#!/usr/bin/env python3
"""
PostToolUse hook: Auto-commit task database changes after task script execution.

This hook detects when task management scripts modify the task database and
automatically commits/pushes changes to prevent data loss.

Triggers:
- After Bash tool executes task scripts (task_add.py, task_process.py, etc.)
- Only commits if changes detected in $ACADEMICOPS_PERSONAL/data/tasks/

Exit codes:
    0: Success (continues execution)
    Non-zero: Hook error (logged, does not block)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def is_task_script_execution(tool_input: dict[str, Any]) -> bool:
    """Check if the tool call was a task management script."""
    if tool_input.get("name") != "Bash":
        return False

    command = tool_input.get("command", "")

    # Detect task script patterns
    task_script_patterns = [
        "task_add.py",
        "task_process.py",
        "task_view.py",
        "task_index.py",
    ]

    return any(pattern in command for pattern in task_script_patterns)


def has_task_changes(personal_repo: Path) -> bool:
    """Check if there are uncommitted changes in data/tasks/."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "data/tasks/"],
            cwd=personal_repo,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def commit_and_push_tasks(personal_repo: Path) -> tuple[bool, str]:
    """Commit and push task changes."""
    try:
        # Add task changes
        subprocess.run(
            ["git", "add", "data/tasks/"],
            cwd=personal_repo,
            check=True,
            timeout=5,
        )

        # Commit with descriptive message
        commit_msg = (
            "update(tasks): auto-commit after task operation\n\n"
            "Task database changes committed automatically via PostToolUse hook.\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
            "Co-Authored-By: Claude <noreply@anthropic.com>"
        )

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=personal_repo,
            check=True,
            timeout=10,
        )

        # Push to remote
        subprocess.run(
            ["git", "push"],
            cwd=personal_repo,
            check=True,
            timeout=30,
        )

        return True, "Task changes committed and pushed successfully"

    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed: {e}"
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main():
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except Exception:
        # Can't parse input, just continue
        print(json.dumps({}))
        sys.exit(0)

    # Extract tool input
    tool_input = input_data.get("toolInput", {})

    # Check if this was a task script execution
    if not is_task_script_execution(tool_input):
        # Not a task script, continue normally
        print(json.dumps({}))
        sys.exit(0)

    # Get personal repository path
    personal_repo_path = os.environ.get("ACADEMICOPS_PERSONAL")
    if not personal_repo_path:
        # Can't determine repo, continue without committing
        print(json.dumps({}))
        sys.exit(0)

    personal_repo = Path(personal_repo_path)
    if not personal_repo.exists():
        print(json.dumps({}))
        sys.exit(0)

    # Check for task changes
    if not has_task_changes(personal_repo):
        # No changes, continue normally
        print(json.dumps({}))
        sys.exit(0)

    # Commit and push changes
    success, message = commit_and_push_tasks(personal_repo)

    if success:
        # Notify user of automatic commit
        output = {
            "systemMessage": "✓ Task changes auto-committed and pushed to repository"
        }
    else:
        # Log error but continue (don't block workflow)
        output = {
            "systemMessage": f"⚠ Auto-commit failed: {message}. Please commit manually."
        }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
