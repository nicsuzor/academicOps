"""Shared utilities for hook implementations.

Provides DRY infrastructure for:
- Temp file management (unified temp directory, write, cleanup)
- Session ID extraction
- Subagent detection
- Hook output formatting

All gates should use these utilities instead of duplicating code.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from pathlib import Path
from typing import Any, TypedDict

from lib.session_paths import get_claude_project_folder

# Default temp directory for hooks (under home for persistence across reboots)
# Default temp directory for hooks (under home for persistence across reboots)
# DEFAULT_HOOK_TMP removed - now using ~/.claude/projects/... or ~/.gemini/...

# Cleanup age: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60


class HookOutput(TypedDict, total=False):
    """Standard hook output format."""

    hookSpecificOutput: dict[str, Any]


def get_hook_temp_dir(category: str, input_data: dict[str, Any] | None = None) -> Path:
    """Get temporary directory for hook files.

    Unified temp directory resolution:
    1. TMPDIR env var (highest priority - host CLI provided)
    2. AOPS_GEMINI_TEMP_ROOT env var (Gemini router provided)
    3. GEMINI_CLI mode: ~/.gemini/tmp/{project_hash}/{category}/
       - Discovered via input_data["transcript_path"] (preferred)
       - Discovered via CWD hash (fallback)

    Using ~/.gemini/tmp/ to keep all Gemini artifacts in one place.

    Args:
        category: Subdirectory name for this hook type (e.g., "hydrator", "compliance", "session")
        input_data: Hook input data (optional). Used to extract transcript_path for precise location.

    Returns:
        Path to temp directory (created if doesn't exist)

    Raises:
        RuntimeError: If GEMINI_CLI is set but temp dir resolves to nothing or doesn't exist
    """
    # 1. Check for standard temp dir env var
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        path = Path(tmpdir) / category
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2. Check for Gemini router provided temp root
    gemini_root = os.environ.get("AOPS_GEMINI_TEMP_ROOT")
    if gemini_root:
        path = Path(gemini_root) / category
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 3. Check transcript_path for Gemini CLI detection (before cwd check)
    # This handles cases where hook runs with different cwd than Gemini CLI
    if input_data:
        transcript_path = input_data.get("transcript_path")
        if transcript_path and ".gemini" in str(transcript_path):
            # Path is usually ~/.gemini/tmp/<hash>/chats/session.json
            # We want ~/.gemini/tmp/<hash>/<category>/
            # So we go up 2 levels from the file: chats/ -> hash/
            t_path = Path(transcript_path)
            if t_path.suffix in (".jsonl", ".json"):
                project_hash_dir = t_path.parent.parent
            else:
                project_hash_dir = t_path.parent

            if project_hash_dir.exists():
                path = project_hash_dir / category
                path.mkdir(parents=True, exist_ok=True)
                return path

    # 4. Gemini-specific discovery logic (GEMINI_CLI env or .gemini in cwd)
    if os.environ.get("GEMINI_CLI") or (Path.cwd() / ".gemini").exists():
        # Strategy A: Use transcript path (already checked above, but keep for completeness)
        if input_data:
            transcript_path = input_data.get("transcript_path")
            if transcript_path:
                t_path = Path(transcript_path)
                if t_path.suffix in (".jsonl", ".json"):
                    project_hash_dir = t_path.parent.parent
                else:
                    project_hash_dir = t_path.parent

                if project_hash_dir.exists() and ".gemini" in str(project_hash_dir):
                    path = project_hash_dir / category
                    path.mkdir(parents=True, exist_ok=True)
                    return path

        # Strategy B: Use CWD hash (standard Gemini behavior)
        project_root = str(Path.cwd())
        abs_root = str(Path(project_root).resolve())
        project_hash = hashlib.sha256(abs_root.encode()).hexdigest()
        gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash

        if gemini_tmp.exists():
            path = gemini_tmp / category
            path.mkdir(parents=True, exist_ok=True)
            return path

        # FAIL-CLOSED: Gemini temp dir doesn't exist
        # We generally do NOT want to use a fallback here if we strictly want isolation.
        raise RuntimeError(
            f"GEMINI_CLI is set but temp root not found. "
            f"Tried transcript path and CWD hash: {gemini_tmp}. "
            "Ensure you are running inside a Gemini project."
        )

    # 5. Default: ~/.claude/projects/{project}/tmp/{category}/ (Claude behavior)
    project_folder = get_claude_project_folder()
    path = Path.home() / ".claude" / "projects" / project_folder / "tmp" / category
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_old_temp_files(
    temp_dir: Path,
    prefix: str,
    age_seconds: int = CLEANUP_AGE_SECONDS,
) -> int:
    """Delete temp files older than specified age.

    Args:
        temp_dir: Directory to clean
        prefix: File prefix pattern (e.g., "hydrate_", "audit_")
        age_seconds: Max file age in seconds (default: 1 hour)

    Returns:
        Number of files deleted
    """
    if not temp_dir.exists():
        return 0

    deleted = 0
    cutoff = time.time() - age_seconds
    for f in temp_dir.glob(f"{prefix}*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass  # Ignore cleanup errors

    return deleted


def write_temp_file(
    content: str,
    temp_dir: Path,
    prefix: str,
    suffix: str = ".md",
) -> Path:
    """Write content to temp file, return path.

    Args:
        content: Content to write
        temp_dir: Target directory
        prefix: File name prefix (e.g., "hydrate_", "audit_")
        suffix: File extension (default: ".md")

    Returns:
        Path to created temp file

    Raises:
        IOError: If temp file cannot be written (fail-fast)
    """
    temp_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix=prefix,
        suffix=suffix,
        dir=temp_dir,
        delete=False,
    ) as f:
        f.write(content)
        return Path(f.name)


def get_session_id(input_data: dict[str, Any], require: bool = False) -> str:
    """Get session ID from hook input data or environment.

    Args:
        input_data: Hook input data dict
        require: If True, raise ValueError when session_id not found

    Returns:
        Session ID string, or empty string if not found and not required

    Raises:
        ValueError: If require=True and session_id not found
    """
    session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        if require:
            raise ValueError(
                "session_id is required in hook input_data or CLAUDE_SESSION_ID env var. "
                "If you're seeing this error, the hook invocation is missing required context."
            )
        return ""
    return session_id


def is_subagent_session() -> bool:
    """Check if this is a subagent session.

    Returns:
        True if CLAUDE_AGENT_TYPE is set (indicating subagent context)
    """
    return bool(os.environ.get("CLAUDE_AGENT_TYPE"))


# ============================================================================
# Hook Output Helpers
# ============================================================================


def make_deny_output(
    message: str,
    event_name: str = "PreToolUse",
) -> HookOutput:
    """Build JSON output for deny/block decision.

    Args:
        message: Block message to display
        event_name: Hook event name (default: "PreToolUse")

    Returns:
        Hook output dict with permissionDecision: deny
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "additionalContext": message,
        }
    }


def make_allow_output(
    message: str = "",
    event_name: str = "PreToolUse",
) -> HookOutput:
    """Build JSON output for allow with optional context.

    Args:
        message: Optional context message
        event_name: Hook event name (default: "PreToolUse")

    Returns:
        Hook output dict with permissionDecision: allow
    """
    if not message:
        return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "allow",
            "additionalContext": message,
        }
    }


def make_context_output(
    message: str,
    event_name: str = "PostToolUse",
    wrap_in_reminder: bool = True,
) -> HookOutput:
    """Build JSON output for injecting context (no permission decision).

    Args:
        message: Context message to inject
        event_name: Hook event name (default: "PostToolUse")
        wrap_in_reminder: If True, wrap message in <system-reminder> tags

    Returns:
        Hook output dict with additionalContext
    """
    if wrap_in_reminder:
        message = f"<system-reminder>\n{message}\n</system-reminder>"

    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": message,
        }
    }


def make_empty_output() -> dict:
    """Return empty output dict (allow without context).

    Returns:
        Empty dict {} which signals allow
    """
    return {}
