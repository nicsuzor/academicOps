#!/usr/bin/env python3
"""
PostToolUse hook: Auto-commit data/ changes after state-modifying operations.

This hook detects when operations modify the personal knowledge base or task
database and automatically commits/pushes changes to prevent data loss and
enable cross-device sync.

Triggers:
- After Bash tool executes task scripts (task_add.py, task_archive.py, etc.)
- After memory MCP tools modify knowledge base (store_memory, update_memory_metadata, etc.)
- After any Write/Edit operations to data/ directory

Scope: All files under data/ (tasks, projects, sessions, knowledge, etc.)

Exit codes:
    0: Success (continues execution)
    Non-zero: Hook error (logged, does not block)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def is_state_modifying_operation(
    tool_name: str, tool_input: dict[str, Any]
) -> bool:
    """Check if the tool call modifies data/ state.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Parameters passed to the tool

    Returns:
        True if operation modifies data/ state, False otherwise
    """

    # Task script patterns (Bash commands)
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        task_script_patterns = [
            "task_add.py",
            "task_archive.py",
            "task_process.py",
            "task_create.py",
            "task_modify.py",
        ]
        if any(pattern in command for pattern in task_script_patterns):
            return True

    # memory MCP tools (knowledge base operations)
    memory_write_tools = [
        "mcp__memory__store_memory",
        "mcp__memory__update_memory_metadata",
        "mcp__memory__delete_memory",
        "mcp__memory__delete_by_tag",
        "mcp__memory__delete_by_tags",
        "mcp__memory__delete_by_all_tags",
        "mcp__memory__delete_by_timeframe",
        "mcp__memory__delete_before_date",
        "mcp__memory__ingest_document",
        "mcp__memory__ingest_directory",
        "mcp__memory__rate_memory",
    ]
    if tool_name in memory_write_tools:
        return True

    # Write/Edit operations targeting data/
    if tool_name in ["Write", "Edit"]:
        file_path = tool_input.get("file_path", "")
        if "data/" in file_path or file_path.startswith("data/"):
            return True

    return False


def has_data_changes(repo_path: Path) -> bool:
    """Check if there are uncommitted changes in data/.

    Args:
        repo_path: Path to repository root

    Returns:
        True if uncommitted changes exist in data/, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "data/"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def commit_and_push_data(repo_path: Path) -> tuple[bool, str]:
    """Commit and push data/ changes.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Add all data/ changes
        subprocess.run(
            ["git", "add", "data/"],
            cwd=repo_path,
            check=True,
            timeout=5,
        )

        # Commit with descriptive message
        commit_msg = (
            "update(data): auto-commit after state operation\n\n"
            "State changes in data/ committed automatically via PostToolUse hook.\n"
            "Ensures cross-device sync and prevents data loss.\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
            "Co-Authored-By: Claude <noreply@anthropic.com>"
        )

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            check=True,
            timeout=10,
        )

        # Push to remote
        push_result = subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,  # Don't fail if push fails (no remote, network issue)
        )

        if push_result.returncode != 0:
            # Commit succeeded but push failed
            return (
                True,
                f"Changes committed but push failed: {push_result.stderr.strip()}",
            )

        return True, "State changes committed and pushed successfully"

    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed: {e}"
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main() -> None:
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except Exception:
        # Can't parse input, just continue
        print(json.dumps({}))
        sys.exit(0)

    # Extract tool name and input
    tool_name = input_data.get("toolName", "")
    tool_input = input_data.get("toolInput", {})

    # Check if this was a state-modifying operation
    if not is_state_modifying_operation(tool_name, tool_input):
        # Not a state operation, continue normally
        print(json.dumps({}))
        sys.exit(0)

    # Get repository path - need to find the git repo containing $ACA_DATA
    try:
        from lib.paths import get_data_root
        data_root = get_data_root()

        # Find git root containing data directory
        repo_path = data_root
        while repo_path != repo_path.parent:
            if (repo_path / ".git").exists():
                break
            repo_path = repo_path.parent

        # Verify we found a git repository
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            check=True,
            timeout=2,
        )
    except Exception as e:
        # Fail-fast: report to agent so they know data wasn't committed
        print(f"autocommit_state: {e}. Data changes NOT auto-committed.", file=sys.stderr)
        sys.exit(2)

    # Check for data/ changes
    if not has_data_changes(repo_path):
        # No changes, continue normally
        print(json.dumps({}))
        sys.exit(0)

    # Commit and push changes
    success, message = commit_and_push_data(repo_path)

    if success:
        # Notify user of automatic commit
        if "push failed" in message.lower():
            output = {"systemMessage": f"✓ Data changes committed locally. ⚠ {message}"}
        else:
            output = {"systemMessage": "✓ Data changes auto-committed and pushed"}
    else:
        # Log error but continue (don't block workflow)
        output = {
            "systemMessage": f"⚠ Auto-commit failed: {message}. Please commit manually."
        }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
