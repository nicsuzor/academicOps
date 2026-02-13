#!/usr/bin/env python3
"""
Session-end commit enforcement hook for Claude Code Stop event.

This is a thin wrapper that re-exports from lib/commit_check.py for backwards
compatibility. The core implementation has moved to lib/ to fix circular
dependency issues where lib/gates/ was importing from hooks/.

The hook checks for:
1. Framework Reflection or final summary in recent messages (indicates completion)
2. Passing tests (look for test success patterns in tool output)
3. Uncommitted changes (git status shows staged/unstaged changes)

Output format (for Stop hooks):
- decision: "block" with reason field - Claude sees the reason
- stopReason: User sees this message
- Exit code 0 required for JSON processing (exit 2 ignores JSON!)
"""

import logging
import subprocess
from pathlib import Path

# Re-export core functions from lib/commit_check.py
from lib.commit_check import (
    MAX_MESSAGES_TO_CHECK,
    QA_INVOCATION_PATTERNS,
    TEST_SUCCESS_PATTERNS,
    attempt_auto_commit,
    check_uncommitted_work,
    extract_recent_messages,
    get_current_branch,
    get_git_push_status,
    get_git_status,
    has_framework_reflection,
    has_qa_invocation,
    has_test_success,
    is_protected_branch,
)
from lib.insights_generator import find_existing_insights
from lib.session_paths import get_session_short_hash, get_session_status_dir

from hooks.internal_models import SessionCleanupResult

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Framework Reflection indicator (kept for reference)
REFLECTION_PATTERNS = ["Framework Reflection", "## Framework Reflection"]


def generate_session_transcript(transcript_path: str) -> bool:
    """Generate transcript and insights from session JSONL file.

    Invokes transcript_push.py to parse the session and generate:
    - Markdown transcripts (full and abridged)
    - Insights JSON file (from Framework Reflection if present)
    - Auto-commit and push to writing repository

    Args:
        transcript_path: Path to session.jsonl file

    Returns:
        True if transcript generation succeeded
    """
    import sys

    try:
        # Get path to transcript_push.py script
        script_dir = Path(__file__).parent.parent / "scripts"
        transcript_script = script_dir / "transcript_push.py"

        if not transcript_script.exists():
            logger.warning(f"Transcript script not found: {transcript_script}")
            # Fallback to transcript.py if push wrapper missing
            transcript_script = script_dir / "transcript.py"

        if not transcript_script.exists():
            logger.warning(f"Fallback transcript script not found: {transcript_script}")
            return False

        # Run transcript script with the session file
        result = subprocess.run(
            [sys.executable, str(transcript_script), transcript_path],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for transcript generation
            cwd=str(script_dir.parent),  # Run from aops-core root
        )

        if result.returncode == 0:
            logger.info(f"Transcript generated successfully for {transcript_path}")
            return True
        elif result.returncode == 2:
            # Exit 2 = skipped (not enough content) - still OK
            logger.info(f"Transcript skipped (insufficient content): {transcript_path}")
            return True
        else:
            logger.warning(f"Transcript generation failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Transcript generation timed out")
        return False
    except Exception as e:
        logger.warning(f"Transcript generation error: {type(e).__name__}: {e}")
        return False


def verify_insights_exist(session_id: str, date: str | None = None) -> bool:
    """Verify that insights JSON was generated for this session.

    Args:
        session_id: Claude Code session ID (full ID, will be hashed)
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        True if insights JSON file exists
    """
    try:
        # Get 8-char hash from session ID
        short_hash = get_session_short_hash(session_id)

        # Use today's date if not provided
        if date is None:
            from datetime import datetime

            date = datetime.now().astimezone().strftime("%Y-%m-%d")

        # Check if insights file exists
        existing = find_existing_insights(date, short_hash)
        if existing:
            logger.info(f"Insights found: {existing}")
            return True

        logger.debug(f"No insights found for session {short_hash} on {date}")
        return False

    except Exception as e:
        logger.warning(f"Error checking insights: {type(e).__name__}: {e}")
        return False


def delete_session_state_file(session_id: str) -> bool:
    """Delete the session state JSON file after successful cleanup.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if deletion succeeded or file didn't exist
    """
    try:
        status_dir = get_session_status_dir(session_id)
        short_hash = get_session_short_hash(session_id)

        # Find matching state file(s) - may have different date prefixes
        # Pattern: YYYYMMDD-HH-hash.json or legacy YYYYMMDD-hash.json
        matches = list(status_dir.glob(f"*-{short_hash}.json"))

        if not matches:
            logger.debug(f"No session state file found for {short_hash}")
            return True

        for state_file in matches:
            try:
                state_file.unlink()
                logger.info(f"Deleted session state file: {state_file}")
            except OSError as e:
                logger.warning(f"Failed to delete state file {state_file}: {e}")
                return False

        return True

    except Exception as e:
        logger.warning(f"Error deleting session state: {type(e).__name__}: {e}")
        return False


def perform_session_cleanup(session_id: str, transcript_path: str | None) -> SessionCleanupResult:
    """Perform end-of-session cleanup: transcript generation and state file deletion.

    Order of operations (fail-fast):
    1. Generate transcript (includes insights extraction)
    2. Verify insights JSON exists
    3. Delete session state file

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session.jsonl file

    Returns:
        SessionCleanupResult with cleanup status
    """
    if not transcript_path:
        return SessionCleanupResult(
            success=True,
            message="No transcript path provided - skipping cleanup",
        )

    # Step 1: Generate transcript
    transcript_generated = generate_session_transcript(transcript_path)
    if not transcript_generated:
        return SessionCleanupResult(message="Transcript generation failed")

    # Step 2: Verify insights exist (may not exist for very short sessions)
    insights_verified = verify_insights_exist(session_id)

    # skip deleting
    return SessionCleanupResult(
        success=True,
        transcript_generated=True,
        insights_verified=insights_verified,
        state_deleted=False,
        message="Session cleanup completed",
    )


# Expose all public symbols
__all__ = [
    # Core functions (re-exported from lib/commit_check.py)
    "check_uncommitted_work",
    "extract_recent_messages",
    "has_framework_reflection",
    "has_test_success",
    "has_qa_invocation",
    "get_git_status",
    "get_git_push_status",
    "get_current_branch",
    "is_protected_branch",
    "attempt_auto_commit",
    # Local functions
    "generate_session_transcript",
    "verify_insights_exist",
    "delete_session_state_file",
    "perform_session_cleanup",
    # Constants (re-exported)
    "MAX_MESSAGES_TO_CHECK",
    "TEST_SUCCESS_PATTERNS",
    "QA_INVOCATION_PATTERNS",
    "REFLECTION_PATTERNS",
]
