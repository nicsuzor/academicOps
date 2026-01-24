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

        has_staged = any(line.startswith(("A ", "M ", "D ", "R ", "C ")) for line in output.split("\n"))
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


def attempt_auto_commit() -> bool:
    """Attempt to auto-commit staged changes.

    Returns:
        True if commit succeeded
    """
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


def check_uncommitted_work(session_id: str, transcript_path: str | None) -> dict[str, Any]:
    """Check if session has uncommitted work after passing tests.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session transcript

    Returns:
        Dictionary with:
        - should_block: bool - whether to block session
        - has_reflection: bool - Framework Reflection found
        - has_test_success: bool - Test success patterns found
        - git_status: dict - git status information
        - message: str - human-readable message
    """
    result = {
        "should_block": False,
        "has_reflection": False,
        "has_test_success": False,
        "git_status": {},
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

    # Determine if we should block
    # Block if: has reflection OR has test success, AND has uncommitted changes
    if (has_reflection or has_tests) and git_status.get("has_changes"):
        result["should_block"] = True

        if git_status.get("staged_changes"):
            result["message"] = "Staged changes detected. Attempting auto-commit..."
            # Try to auto-commit
            if attempt_auto_commit():
                result["should_block"] = False
                result["message"] = "Auto-committed. Session can proceed."
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
                    "decision": "block",
                    "reason": (
                        f"Active task bound to session: {current_task}. "
                        "Complete the task or use AskUserQuestion to request permission to end without completing."
                    ),
                }
                logger.info(f"Session end blocked: active task {current_task}")
                print(json.dumps(output_data))
                sys.exit(0)
        except Exception as e:
            logger.warning(f"Task binding check failed: {type(e).__name__}: {e}")

        # Check 2: Block if uncommitted work after passing tests
        try:
            check_result = check_uncommitted_work(session_id, transcript_path)

            if check_result["should_block"]:
                # Block the session and require commit
                # Note: Stop hooks can't send messages to agent (hookSpecificOutput
                # not supported for Stop event). Keep reason concise to avoid spam.
                output_data = {
                    "decision": "block",
                    "reason": check_result["message"],
                }
                logger.info(f"Session end blocked: {check_result['message'][:80]}...")
                print(json.dumps(output_data))
                sys.exit(0)  # Exit 0 so JSON is processed; decision:block does the blocking
            else:
                # Allow session to proceed, but log findings
                if check_result["message"]:
                    output_data = {
                        "systemMessage": check_result["message"],
                    }
                    logger.info(check_result["message"])

        except Exception as e:
            logger.warning(f"Uncommitted work check failed: {type(e).__name__}: {e}")

    # Allow session to proceed normally - add verification message for user
    output_data["systemMessage"] = "✓ handover verified"
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
