#!/usr/bin/env python3
"""
PostToolUse hook: Auto-commit data/ changes after state-modifying operations.

This hook detects when operations modify the personal knowledge base or task
database and automatically commits/pushes changes to prevent data loss and
enable cross-device sync.

Enforces: current-state-machine (Current State Machine - $ACA_DATA always up-to-date)

Triggers:
- After Bash tool executes task scripts (task_add.py, task_archive.py, etc.)
- After memory MCP tools modify knowledge base (store_memory, update_memory_metadata, etc.)
- After any Write/Edit operations to data/ directory

Scope: All files under data/ (tasks, projects, sessions, knowledge, etc.)

Exit codes:
    0: Success (continues execution)
    Non-zero: Hook error (logged, does not block)
"""

import subprocess
from pathlib import Path
from typing import Any


def can_sync(repo_path: Path) -> tuple[bool, str]:
    """Check if repo is in a syncable state.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (can_sync: bool, reason: str)
        If can_sync is False, reason explains why.
    """
    try:
        # Check not detached HEAD
        result = subprocess.run(
            ["git", "symbolic-ref", "-q", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return False, "detached HEAD"

        # Check has tracking branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return False, "no tracking branch"

        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timeout checking repo state"
    except Exception as e:
        return False, f"error: {e}"


def fetch_and_check_divergence(repo_path: Path) -> tuple[bool, int, str]:
    """Fetch from origin and check if local is behind remote.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (is_behind: bool, commits_behind: int, error: str)
        If error is non-empty, fetch failed and sync should be skipped.
    """
    try:
        # Fetch with separate 5s timeout
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return False, 0, f"fetch failed: {result.stderr.strip()}"

        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        branch = result.stdout.strip()

        # Check how many commits behind
        result = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            # Remote branch might not exist
            return False, 0, f"no remote branch origin/{branch}"

        commits_behind = int(result.stdout.strip())
        return commits_behind > 0, commits_behind, ""

    except subprocess.TimeoutExpired:
        return False, 0, "fetch timeout"
    except Exception as e:
        return False, 0, f"error: {e}"


def pull_rebase_if_behind(repo_path: Path) -> tuple[bool, str]:
    """Pull with rebase if behind remote.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (success: bool, message: str)
        If success is False, message contains conflict details.
    """
    try:
        # Get current branch for explicit pull
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        branch = result.stdout.strip()

        # Pull with rebase
        result = subprocess.run(
            ["git", "pull", "--rebase", "origin", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            # Check for conflict
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                # Abort rebase to restore clean state
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    cwd=repo_path,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                return False, "rebase conflict - aborted. Run `git status` to inspect."

            return False, f"rebase failed: {result.stderr.strip()}"

        # Check for rebase in progress markers
        rebase_dir = repo_path / ".git" / "rebase-merge"
        rebase_apply = repo_path / ".git" / "rebase-apply"
        if rebase_dir.exists() or rebase_apply.exists():
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=repo_path,
                capture_output=True,
                timeout=5,
                check=False,
            )
            return False, "partial rebase detected - aborted"

        return True, "synced successfully"

    except subprocess.TimeoutExpired:
        return False, "rebase timeout"
    except Exception as e:
        return False, f"error: {e}"


def get_modified_repos(tool_name: str, tool_input: dict[str, Any]) -> set[str]:
    """Check which repos were modified by this tool call.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Parameters passed to the tool

    Returns:
        Set of repo types modified: "data" (checks for "aops" are disabled)
    """
    modified = set()

    # Task script patterns (Bash commands) -> data repo
    if tool_name == "Bash":
        if "command" not in tool_input:
            raise ValueError(
                "Bash tool_input requires 'command' parameter (P#8: fail-fast)"
            )
        command = tool_input["command"]
        task_script_patterns = [
            "task_add.py",
            "task_archive.py",
            "task_process.py",
            "task_create.py",
            "task_modify.py",
        ]
        if any(pattern in command for pattern in task_script_patterns):
            modified.add("data")

    # memory MCP tools (knowledge base operations) -> data repo
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
        modified.add("data")

    # tasks-v2 MCP tools (task management) -> data repo
    tasks_write_tools = [
        "mcp__tasks__create_task",
        "mcp__tasks__update_task",
        "mcp__tasks__complete_task",
        "mcp__tasks__delete_task",
        "mcp__tasks__decompose_task",
        "mcp__tasks__complete_tasks",
        "mcp__tasks__reorder_children",
        "mcp__tasks__rebuild_index",
    ]
    if tool_name in tasks_write_tools:
        modified.add("data")

    # Write/Edit operations - check path to determine repo
    if tool_name in ["Write", "Edit"]:
        if "file_path" not in tool_input:
            raise ValueError(
                "Write/Edit tool_input requires 'file_path' parameter (P#8: fail-fast)"
            )
        file_path = tool_input["file_path"]
        if "data/" in file_path or file_path.startswith("data/"):
            modified.add("data")

        # AOPS tracking disabled: only sync knowledge base changes
        # if "academicOps/" in file_path or "/academicOps" in file_path:
        #     modified.add("aops")

    return modified


def has_repo_changes(repo_path: Path, subdir: str | None = None) -> bool:
    """Check if there are uncommitted changes in repo (optionally in subdir).

    Args:
        repo_path: Path to repository root
        subdir: Optional subdirectory to check (e.g., "data/")

    Returns:
        True if uncommitted changes exist, False otherwise

    Raises:
        RuntimeError: If git status check fails (P#8: fail-fast)
    """
    cmd = ["git", "status", "--porcelain"]
    if subdir:
        cmd.append(subdir)
    result = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git status failed in {repo_path}: {result.stderr.strip()} (P#8: fail-fast)"
        )
    return bool(result.stdout.strip())


def get_current_branch(repo_path: Path) -> str | None:
    """Get the current branch name.

    Returns:
        Branch name, or None if detached HEAD

    Raises:
        RuntimeError: If git command fails (P#8: fail-fast)
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git rev-parse failed in {repo_path}: {result.stderr.strip()} (P#8: fail-fast)"
        )
    branch = result.stdout.strip()
    return None if branch == "HEAD" else branch  # HEAD means detached


def is_protected_branch(branch: str | None) -> bool:
    """Check if branch is protected from auto-commits.

    Protected branches: main, master
    """
    if branch is None:
        return True  # Detached HEAD - don't auto-commit
    return branch.lower() in ("main", "master")


def commit_and_push_repo(
    repo_path: Path, subdir: str | None = None, commit_prefix: str = "update"
) -> tuple[bool, str]:
    """Commit and push changes in a repo (optionally scoped to subdir).

    Syncs with remote before committing to prevent conflicts.
    Will NOT auto-commit to main/master branches.

    Args:
        repo_path: Path to repository root
        subdir: Optional subdirectory to add (e.g., "data/"). If None, adds all.
        commit_prefix: Prefix for commit message (e.g., "update(data)" or "update(framework)")

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Branch protection: never auto-commit to main/master
    current_branch = get_current_branch(repo_path)
    if is_protected_branch(current_branch):
        return (
            False,
            f"Skipping auto-commit: protected branch '{current_branch or 'detached HEAD'}'",
        )

    sync_warning = ""

    # Step 1: Check if sync is possible
    syncable, reason = can_sync(repo_path)
    if not syncable:
        # Skip sync but continue with commit
        sync_warning = f"(sync skipped: {reason}) "
    else:
        # Step 2: Fetch and check divergence
        is_behind, count, fetch_err = fetch_and_check_divergence(repo_path)
        if fetch_err:
            # Network issue - skip sync, continue with local commit
            sync_warning = f"(sync skipped: {fetch_err}) "
        elif is_behind:
            # Step 3: Rebase to incorporate remote changes
            sync_ok, sync_msg = pull_rebase_if_behind(repo_path)
            if not sync_ok:
                # CONFLICT - abort, don't commit, alert agent
                return False, f"SYNC CONFLICT: {sync_msg}"
            # Sync succeeded
            sync_warning = f"(synced {count} commits) "

    try:
        # Step 4: Add changes (scoped to subdir if provided)
        add_target = subdir if subdir else "."
        subprocess.run(
            ["git", "add", add_target],
            cwd=repo_path,
            capture_output=True,
            check=True,
            timeout=5,
        )

        # Commit with descriptive message
        scope = subdir.rstrip("/") if subdir else "all"
        commit_msg = (
            f"{commit_prefix}: auto-commit after state operation\n\n"
            f"Changes in {scope} committed automatically via PostToolUse hook.\n"
            "Ensures cross-device sync and prevents data loss.\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
            "Co-Authored-By: Claude <noreply@anthropic.com>"
        )

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            capture_output=True,
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
                f"{sync_warning}Changes committed but push failed: {push_result.stderr.strip()}",
            )

        return True, f"{sync_warning}State changes committed and pushed successfully"

    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed: {e}"
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except Exception as e:
        return False, f"Unexpected error: {e}"
