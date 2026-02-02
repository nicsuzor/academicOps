#!/usr/bin/env python3
"""
Session-end commit enforcement hook for Claude Code Stop event.

Detects when an agent is ending a session with uncommitted work and enforces
a commit before allowing the session to stop. This prevents loss of work when
agents complete tasks, pass tests, but forget to commit changes.

The hook checks for:
1. Framework Reflection or final summary in recent messages (indicates completion)
2. Passing tests (look for test success patterns in tool output)
3. Uncommitted changes (git status shows staged/unstaged changes)

When all conditions are met:
- If changes are staged: auto-commits with message
- If changes are unstaged: blocks session and tells Claude to commit
- Otherwise: allows session to proceed normally

Output format (for Stop hooks):
- decision: "block" with reason field - Claude sees the reason
- stopReason: User sees this message
- Exit code 0 required for JSON processing (exit 2 ignores JSON!)
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.reflection_detector import has_reflection
from lib.session_state import get_current_task
from lib.session_paths import get_session_short_hash, get_session_status_dir
from lib.insights_generator import find_existing_insights
from lib.transcript_parser import SessionProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Number of recent assistant messages to check for reflection/completion
MAX_MESSAGES_TO_CHECK = 10

# Test success indicators
TEST_SUCCESS_PATTERNS = [
    "all tests passed",
    "all tests passing",
    "tests passed",
    "tests passing",
    "PASSED",
    "passed successfully",
    "OK",
    "100% success",
    "test run successful",
    "passed all",
]

# Framework Reflection indicator
REFLECTION_PATTERNS = ["Framework Reflection", "## Framework Reflection"]


def extract_recent_messages(
    transcript_path: Path, max_messages: int = MAX_MESSAGES_TO_CHECK
) -> list[str]:
    """Extract recent assistant message texts from transcript.

    Args:
        transcript_path: Path to JSONL transcript file
        max_messages: Maximum number of messages to extract

    Returns:
        List of assistant message texts (newest first)
    """
    if not transcript_path.exists():
        return []

    try:
        processor = SessionProcessor()
        _, entries, agent_entries = processor.parse_session_file(
            transcript_path, load_agents=True, load_hooks=False
        )

        messages = []

        # Collect from main entries (reverse order - newest first)
        for entry in reversed(entries):
            if entry.type != "assistant":
                continue

            text = _extract_text_from_entry(entry)
            if text:
                messages.append(text)
                if len(messages) >= max_messages:
                    break

        # Also check agent entries if we haven't found enough
        if len(messages) < max_messages and agent_entries:
            for agent_id, agent_entry_list in agent_entries.items():
                for entry in reversed(agent_entry_list):
                    if entry.type != "assistant":
                        continue
                    text = _extract_text_from_entry(entry)
                    if text:
                        messages.append(text)
                        if len(messages) >= max_messages:
                            break
                if len(messages) >= max_messages:
                    break

        return messages

    except Exception as e:
        logger.warning(f"Failed to extract messages from transcript: {e}")
        return []


def _extract_text_from_entry(entry: Any) -> str:
    """Extract text content from an Entry object."""
    text = ""
    if entry.message:
        content = entry.message.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
    elif entry.content:
        text = str(entry.content.get("content", ""))
    return text


def has_framework_reflection(messages: list[str]) -> bool:
    """Check if messages contain Framework Reflection section.

    Args:
        messages: List of message texts

    Returns:
        True if Framework Reflection detected
    """
    for message in messages:
        if has_reflection(message):
            return True
    return False


def has_test_success(messages: list[str]) -> bool:
    """Check if messages contain test success indicators.

    Args:
        messages: List of message texts

    Returns:
        True if test success detected
    """
    for message in messages:
        for pattern in TEST_SUCCESS_PATTERNS:
            if pattern.lower() in message.lower():
                logger.debug(f"Test success pattern detected: {pattern}")
                return True
    return False


def get_git_status(cwd: str | None = None) -> dict[str, Any]:
    """Get git status information.

    Args:
        cwd: Working directory for git command

    Returns:
        Dictionary with:
        - has_changes: bool - any uncommitted changes
        - staged_changes: bool - changes in staging area
        - unstaged_changes: bool - changes not staged
        - untracked_files: bool - untracked files exist
        - status_output: str - raw git status output
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.warning(f"git status failed: {result.stderr}")
            return {
                "has_changes": False,
                "staged_changes": False,
                "unstaged_changes": False,
                "untracked_files": False,
                "status_output": "",
            }

        output = result.stdout
        if not output:
            return {
                "has_changes": False,
                "staged_changes": False,
                "unstaged_changes": False,
                "untracked_files": False,
                "status_output": "",
            }

        has_staged = any(
            line.startswith(("A ", "M ", "D ", "R ", "C "))
            for line in output.split("\n")
        )
        has_unstaged = any(line.startswith((" M", " D")) for line in output.split("\n"))
        has_untracked = any(line.startswith("??") for line in output.split("\n"))

        return {
            "has_changes": bool(output.strip()),
            "staged_changes": has_staged,
            "unstaged_changes": has_unstaged,
            "untracked_files": has_untracked,
            "status_output": output,
        }

    except Exception as e:
        logger.warning(f"Failed to get git status: {e}")
        return {
            "has_changes": False,
            "staged_changes": False,
            "unstaged_changes": False,
            "untracked_files": False,
            "status_output": "",
        }


def get_git_push_status(cwd: str | None = None) -> dict[str, Any]:
    """Get git push status information (commits ahead of remote).

    Args:
        cwd: Working directory for git command

    Returns:
        Dictionary with:
        - branch_ahead: bool - current branch is ahead of remote
        - commits_ahead: int - number of commits ahead
        - current_branch: str - current branch name
        - tracking_branch: str - remote tracking branch (e.g., origin/main)
    """
    try:
        # Get current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.warning(f"Failed to get current branch: {result.stderr}")
            return {
                "branch_ahead": False,
                "commits_ahead": 0,
                "current_branch": "",
                "tracking_branch": "",
            }

        current_branch = result.stdout.strip()

        # Get tracking branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{u}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug(f"No tracking branch configured for {current_branch}")
            return {
                "branch_ahead": False,
                "commits_ahead": 0,
                "current_branch": current_branch,
                "tracking_branch": "",
            }

        tracking_branch = result.stdout.strip()

        # Count commits ahead of remote
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{tracking_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug(f"Failed to count commits ahead: {result.stderr}")
            return {
                "branch_ahead": False,
                "commits_ahead": 0,
                "current_branch": current_branch,
                "tracking_branch": tracking_branch,
            }

        commits_ahead = int(result.stdout.strip())

        return {
            "branch_ahead": commits_ahead > 0,
            "commits_ahead": commits_ahead,
            "current_branch": current_branch,
            "tracking_branch": tracking_branch,
        }

    except ValueError:
        logger.warning("Failed to parse commits ahead count")
        return {
            "branch_ahead": False,
            "commits_ahead": 0,
            "current_branch": "",
            "tracking_branch": "",
        }
    except Exception as e:
        logger.warning(f"Failed to get git push status: {e}")
        return {
            "branch_ahead": False,
            "commits_ahead": 0,
            "current_branch": "",
            "tracking_branch": "",
        }


def get_current_branch() -> str | None:
    """Get the current branch name.

    Returns:
        Branch name, or None if detached HEAD or error
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return None if branch == "HEAD" else branch
        return None
    except Exception:
        return None


def is_protected_branch(branch: str | None) -> bool:
    """Check if branch is protected from auto-commits."""
    if branch is None:
        return True  # Detached HEAD - don't auto-commit
    return branch.lower() in ("main", "master")


def attempt_auto_commit() -> bool:
    """Attempt to auto-commit staged changes.

    Will NOT auto-commit to main/master branches.

    Returns:
        True if commit succeeded
    """
    # Branch protection: never auto-commit to main/master
    current_branch = get_current_branch()
    if is_protected_branch(current_branch):
        logger.info(
            f"Skipping auto-commit: protected branch '{current_branch or 'detached HEAD'}'"
        )
        return False

    try:
        message = "Auto-commit: Session-end enforcement hook detected uncommitted work\n\nCo-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            logger.info("Auto-commit succeeded")
            return True
        elif "nothing to commit" in result.stdout.lower():
            logger.debug("No changes to commit")
            return True
        else:
            logger.warning(f"Commit failed: {result.stderr}")
            return False

    except Exception as e:
        logger.warning(f"Auto-commit failed: {e}")
        return False


def generate_session_transcript(transcript_path: str) -> bool:
    """Generate transcript and insights from session JSONL file.

    Invokes transcript.py to parse the session and generate:
    - Markdown transcripts (full and abridged)
    - Insights JSON file (from Framework Reflection if present)

    Args:
        transcript_path: Path to session.jsonl file

    Returns:
        True if transcript generation succeeded
    """
    try:
        # Get path to transcript.py script
        script_dir = Path(__file__).parent.parent / "scripts"
        transcript_script = script_dir / "transcript.py"

        if not transcript_script.exists():
            logger.warning(f"Transcript script not found: {transcript_script}")
            return False

        # Run transcript.py with the session file
        result = subprocess.run(
            ["python", str(transcript_script), transcript_path],
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


def perform_session_cleanup(
    session_id: str, transcript_path: str | None
) -> dict[str, Any]:
    """Perform end-of-session cleanup: transcript generation and state file deletion.

    Order of operations (fail-fast):
    1. Generate transcript (includes insights extraction)
    2. Verify insights JSON exists
    3. Delete session state file

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session.jsonl file

    Returns:
        Dictionary with:
        - success: bool - all cleanup steps succeeded
        - transcript_generated: bool
        - insights_verified: bool
        - state_deleted: bool
        - message: str - human-readable status
    """
    result = {
        "success": False,
        "transcript_generated": False,
        "insights_verified": False,
        "state_deleted": False,
        "message": "",
    }

    if not transcript_path:
        result["message"] = "No transcript path provided - skipping cleanup"
        result["success"] = True  # Not a failure, just nothing to clean up
        return result

    # Step 1: Generate transcript
    if generate_session_transcript(transcript_path):
        result["transcript_generated"] = True
    else:
        result["message"] = "Transcript generation failed"
        return result

    # Step 2: Verify insights exist (may not exist for very short sessions)
    # We proceed with cleanup even if insights don't exist - the transcript
    # generation already handled that case (exit code 2 for insufficient content)
    result["insights_verified"] = verify_insights_exist(session_id)

    # skip deleting
    result["state_deleted"] = False
    result["success"] = True
    result["message"] = "Session cleanup completed"
    return result

    # Step 3: Delete session state file
    if delete_session_state_file(session_id):
        result["state_deleted"] = True
        result["success"] = True
        result["message"] = "Session cleanup completed"
        if result["insights_verified"]:
            result["message"] = (
                str(result["message"]) + " (transcript + insights generated)"
            )
        else:
            result["message"] = (
                str(result["message"]) + " (transcript generated, no insights)"
            )
    else:
        result["message"] = "Failed to delete session state file"

    return result


def check_uncommitted_work(
    session_id: str, transcript_path: str | None
) -> dict[str, Any]:
    """Check if session has uncommitted work or unpushed commits.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session transcript

    Returns:
        Dictionary with:
        - should_block: bool - whether to block session
        - has_reflection: bool - Framework Reflection found
        - has_test_success: bool - Test success patterns found
        - git_status: dict - git status information
        - push_status: dict - git push status information
        - reminder_needed: bool - if reminder should be shown (even if not blocking)
        - message: str - human-readable message
    """
    result = {
        "should_block": False,
        "has_reflection": False,
        "has_test_success": False,
        "git_status": {},
        "push_status": {},
        "reminder_needed": False,
        "message": "",
    }

    if not transcript_path:
        logger.debug("No transcript path provided")
        return result

    path = Path(transcript_path)
    messages = extract_recent_messages(path)

    if not messages:
        logger.debug("No assistant messages found")
        return result

    # Check for Framework Reflection
    has_reflection = has_framework_reflection(messages)
    result["has_reflection"] = has_reflection

    # Check for test success
    has_tests = has_test_success(messages)
    result["has_test_success"] = has_tests

    # Get git status
    git_status = get_git_status()
    result["git_status"] = git_status

    # Get git push status
    push_status = get_git_push_status()
    result["push_status"] = push_status

    # Build reminder message for any uncommitted work or unpushed commits
    reminder_parts = []

    # Check for uncommitted changes
    if git_status.get("has_changes"):
        if git_status.get("staged_changes"):
            reminder_parts.append("Staged changes detected")
        if git_status.get("unstaged_changes"):
            reminder_parts.append("Unstaged changes detected")
        if git_status.get("untracked_files"):
            reminder_parts.append("Untracked files detected")

    # Check for unpushed commits
    if push_status.get("branch_ahead"):
        reminder_parts.append(
            f"{push_status.get('commits_ahead', 1)} unpushed commit(s) on {push_status.get('current_branch', 'current branch')}"
        )

    # Don't block on git -- just warn.
    # Only trigger blocking if: (has reflection OR has test success) AND has uncommitted changes
    if (has_reflection or has_tests) and git_status.get("has_changes"):
        result["should_block"] = False

        if git_status.get("staged_changes"):
            result["message"] = "Staged changes detected. Attempting auto-commit..."
            # Try to auto-commit
            if attempt_auto_commit():
                result["should_block"] = False
                result["message"] = "Auto-committed. Session can proceed."
                # Update reminder for any unpushed commits
                if push_status.get("branch_ahead"):
                    result["reminder_needed"] = True
                    result["message"] = str(result["message"]) + (
                        f"\nReminder: Push {push_status.get('commits_ahead', 1)} unpushed commit(s) on {push_status.get('current_branch', 'current branch')}"
                    )
            else:
                result["message"] = (
                    "Commit staged changes before ending session, "
                    "or use AskUserQuestion to request permission to end without committing."
                )
        else:
            result["message"] = (
                "Uncommitted changes detected. Commit before ending session, "
                "or use AskUserQuestion to request permission to end without committing."
            )
    elif reminder_parts:
        # Non-blocking reminder for unpushed commits or other git state
        result["reminder_needed"] = True
        result["message"] = (
            "Reminder: "
            + " and ".join(reminder_parts)
            + ". Consider committing and pushing before ending session."
        )

    return result


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode failed: {e}")
    except Exception as e:
        logger.warning(f"Error reading stdin: {type(e).__name__}: {e}")

    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path")
    hook_event = input_data.get("hook_event_name", "")

    # Only process Stop events
    if hook_event != "Stop":
        print(json.dumps({}))
        sys.exit(0)

    output_data: dict[str, Any] = {}

    if session_id:
        # Check 1: Block if there's an active task bound to this session
        try:
            current_task = get_current_task(session_id)
            if current_task:
                output_data = {
                    "verdict": "deny",  # Deny the stop -> Block session end
                    "system_message": (
                        f"Active task bound to session: {current_task}. "
                        "Complete the task or use AskUserQuestion to request permission to end without completing."
                    ),
                }
                logger.info(f"Session end blocked: active task {current_task}")
                print(json.dumps(output_data))
                sys.exit(0)
        except Exception as e:
            logger.warning(f"Task binding check failed: {type(e).__name__}: {e}")

        # Check 2: Block if uncommitted work after passing tests, or remind about unpushed commits
        try:
            check_result = check_uncommitted_work(session_id, transcript_path)

            if check_result["should_block"]:
                # Block the session and require commit
                # Note: Stop hooks can't send messages to agent (hookSpecificOutput
                # not supported for Stop event). Keep reason concise to avoid spam.
                output_data = {
                    "verdict": "deny",  # Deny the stop -> Block session end
                    "system_message": check_result["message"],
                }
                logger.info(f"Session end blocked: {check_result['message'][:80]}...")
                print(json.dumps(output_data))
                sys.exit(
                    0
                )  # Exit 0 so JSON is processed; decision:block does the blocking
            elif check_result["reminder_needed"]:
                # Allow session to proceed, but include reminder message
                output_data = {
                    "verdict": "allow",
                    "system_message": check_result["message"],
                }
                logger.info(f"Reminder shown: {check_result['message'][:80]}...")

        except Exception as e:
            logger.warning(f"Uncommitted work check failed: {type(e).__name__}: {e}")

        # Perform session cleanup (transcript generation + state file deletion)
        # Only run if all blocking checks passed
        try:
            cleanup_result = perform_session_cleanup(session_id, transcript_path)
            if cleanup_result["success"]:
                logger.info(f"Session cleanup: {cleanup_result['message']}")
            else:
                logger.warning(
                    f"Session cleanup incomplete: {cleanup_result['message']}"
                )
        except Exception as e:
            logger.warning(f"Session cleanup failed: {type(e).__name__}: {e}")

    # Allow session to proceed normally - add verification message for user if not already set
    if "system_message" not in output_data:
        output_data["system_message"] = "✅ handover verified"
    if "verdict" not in output_data:
        output_data["verdict"] = "allow"

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
