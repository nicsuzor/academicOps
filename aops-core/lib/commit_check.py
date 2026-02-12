"""Commit check utilities - moved from hooks/session_end_commit_check.py.

This module provides the check_uncommitted_work function for gates to use
without circular imports from hooks/.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from hooks.internal_models import (
    GitPushStatus,
    GitStatus,
    UncommittedWorkCheck,
)

from lib.reflection_detector import has_reflection
from lib.transcript_parser import SessionProcessor

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

# QA invocation patterns
QA_INVOCATION_PATTERNS = [
    'subagent_type="qa"',
    "subagent_type='qa'",
    'subagent_type": "qa"',
    "subagent_type': 'qa'",
    "aops-core:qa",
    "/qa",
    "QA verification",
    "PASS:",
    "FAIL:",
    "REVISE:",
]


def _extract_text_from_entry(entry: Any) -> str:
    """Extract text content from an Entry object."""
    text = ""
    if entry.message:
        content = entry.message.get("content")
        if content is None:
            pass
        elif isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    block_text = block.get("text")
                    if block_text is not None:
                        text += block_text
    elif entry.content:
        inner_content = entry.content.get("content")
        if inner_content is not None:
            text = str(inner_content)
    return text


def extract_recent_messages(
    transcript_path: Path, max_messages: int = MAX_MESSAGES_TO_CHECK
) -> list[str]:
    """Extract recent assistant message texts from transcript."""
    if not transcript_path.exists():
        return []

    try:
        processor = SessionProcessor()
        _, entries, agent_entries = processor.parse_session_file(
            transcript_path, load_agents=True, load_hooks=False
        )

        messages = []

        for entry in reversed(entries):
            if entry.type != "assistant":
                continue
            text = _extract_text_from_entry(entry)
            if text:
                messages.append(text)
                if len(messages) >= max_messages:
                    break

        if len(messages) < max_messages and agent_entries:
            for _agent_id, agent_entry_list in agent_entries.items():
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


def has_framework_reflection(messages: list[str]) -> bool:
    """Check if messages contain Framework Reflection section."""
    for message in messages:
        if has_reflection(message):
            return True
    return False


def has_test_success(messages: list[str]) -> bool:
    """Check if messages contain test success indicators."""
    for message in messages:
        for pattern in TEST_SUCCESS_PATTERNS:
            if pattern.lower() in message.lower():
                return True
    return False


def has_qa_invocation(messages: list[str]) -> bool:
    """Check if QA agent was invoked during the session."""
    for message in messages:
        for pattern in QA_INVOCATION_PATTERNS:
            if pattern.lower() in message.lower():
                return True
    return False


def get_git_status(cwd: str | None = None) -> GitStatus:
    """Get git status information."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return GitStatus()

        output = result.stdout
        if not output:
            return GitStatus()

        has_staged = any(
            line.startswith(("A ", "M ", "D ", "R ", "C ")) for line in output.split("\n")
        )
        has_unstaged = any(line.startswith((" M", " D")) for line in output.split("\n"))
        has_untracked = any(line.startswith("??") for line in output.split("\n"))

        return GitStatus(
            has_changes=bool(output.strip()),
            staged_changes=has_staged,
            unstaged_changes=has_unstaged,
            untracked_files=has_untracked,
            status_output=output,
        )

    except Exception as e:
        logger.warning(f"Failed to get git status: {e}")
        return GitStatus()


def get_git_push_status(cwd: str | None = None) -> GitPushStatus:
    """Get git push status information."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return GitPushStatus()

        current_branch = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{u}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return GitPushStatus(current_branch=current_branch)

        tracking_branch = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-list", "--count", f"{tracking_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return GitPushStatus(
                current_branch=current_branch,
                tracking_branch=tracking_branch,
            )

        commits_ahead = int(result.stdout.strip())

        return GitPushStatus(
            branch_ahead=commits_ahead > 0,
            commits_ahead=commits_ahead,
            current_branch=current_branch,
            tracking_branch=tracking_branch,
        )

    except ValueError:
        return GitPushStatus()
    except Exception as e:
        logger.warning(f"Failed to get git push status: {e}")
        return GitPushStatus()


def get_current_branch() -> str | None:
    """Get the current branch name."""
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
        return True
    return branch.lower() in ("main", "master")


def attempt_auto_commit() -> bool:
    """Attempt to auto-commit staged changes."""
    current_branch = get_current_branch()
    if is_protected_branch(current_branch):
        logger.info(f"Skipping auto-commit: protected branch '{current_branch or 'detached HEAD'}'")
        return False

    try:
        message = (
            "Auto-commit: Session-end enforcement hook detected uncommitted work\n\n"
            "Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
        )
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
            return True
        else:
            logger.warning(f"Commit failed: {result.stderr}")
            return False

    except Exception as e:
        logger.warning(f"Auto-commit failed: {e}")
        return False


def check_uncommitted_work(session_id: str, transcript_path: str | None) -> UncommittedWorkCheck:
    """Check if session has uncommitted work or unpushed commits.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session transcript

    Returns:
        UncommittedWorkCheck with check results
    """
    if not transcript_path:
        return UncommittedWorkCheck()

    path = Path(transcript_path)
    messages = extract_recent_messages(path)

    if not messages:
        return UncommittedWorkCheck()

    reflection_found = has_framework_reflection(messages)
    tests_passed = has_test_success(messages)
    qa_invoked = has_qa_invocation(messages)
    git_status = get_git_status()
    push_status = get_git_push_status()

    reminder_parts = []

    if git_status.has_changes:
        if git_status.staged_changes:
            reminder_parts.append("Staged changes detected")
        if git_status.unstaged_changes:
            reminder_parts.append("Unstaged changes detected")
        if git_status.untracked_files:
            reminder_parts.append("Untracked files detected")

    if push_status.branch_ahead:
        branch_display = push_status.current_branch if push_status.current_branch else "unknown branch"
        reminder_parts.append(f"{push_status.commits_ahead} unpushed commit(s) on {branch_display}")

    has_tracked_changes = git_status.staged_changes or git_status.unstaged_changes
    if has_tracked_changes and not qa_invoked:
        reminder_parts.append(
            "Code modified without QA verification. Consider running /qa before completion."
        )

    should_block = False
    reminder_needed = False
    message = ""

    if (reflection_found or tests_passed or has_tracked_changes) and git_status.has_changes:
        should_block = True

        if git_status.staged_changes:
            message = "Staged changes detected. Attempting auto-commit..."
            if attempt_auto_commit():
                should_block = False
                message = "Auto-committed. Session can proceed."
                if push_status.branch_ahead:
                    reminder_needed = True
                    branch_display = (
                        push_status.current_branch if push_status.current_branch else "unknown branch"
                    )
                    message += f"\nReminder: Push {push_status.commits_ahead} unpushed commit(s) on {branch_display}"
            else:
                message = (
                    "Commit staged changes before ending session, "
                    "or use AskUserQuestion to request permission to end without committing."
                )
        else:
            message = (
                "Uncommitted changes detected. Commit before ending session, "
                "or use AskUserQuestion to request permission to end without committing."
            )
    elif reminder_parts:
        reminder_needed = True
        message = (
            "Reminder: "
            + " and ".join(reminder_parts)
            + ". Consider committing and pushing before ending session."
        )

    return UncommittedWorkCheck(
        should_block=should_block,
        has_reflection=reflection_found,
        has_test_success=tests_passed,
        git_status=git_status,
        push_status=push_status,
        reminder_needed=reminder_needed,
        message=message,
    )
