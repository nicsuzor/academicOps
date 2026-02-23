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

import os
import subprocess
from pathlib import Path
from typing import Any


def is_aca_data_repo(repo_path: Path) -> bool:
    """Check if repo_path is the ACA_DATA repository (~/brain).

    ACA_DATA uses main branch as its only branch, so it needs an
    exemption from branch protection for auto-commits.
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return False
    try:
        return repo_path.resolve() == Path(aca_data).resolve()
    except (OSError, ValueError):
        return False


def generate_commit_message(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Generate a descriptive commit message from tool context.

    Maps tool operations to human-readable commit messages following
    the same conventions as brain-sync.sh.
    """
    if not isinstance(tool_input, dict):
        return "sync: auto-commit"

    # Task operations (suffix matching for client-agnostic tool names)
    if tool_name.endswith("__create_task"):
        title = tool_input.get("task_title", "")
        if title:
            return f"task: create '{title[:60]}'"
        return "task: create"

    if tool_name.endswith("__update_task"):
        task_id = tool_input.get("id", "")
        title = tool_input.get("task_title")
        if title:
            return f"task: update '{title[:60]}'"
        if task_id:
            return f"task: update {task_id}"
        return "task: update"

    if tool_name.endswith("__complete_task") or tool_name.endswith("__complete_tasks"):
        task_id = tool_input.get("id", "")
        ids = tool_input.get("ids", [])
        if task_id:
            return f"task: complete {task_id}"
        if ids:
            return f"task: complete {len(ids)} tasks"
        return "task: complete"

    if tool_name.endswith("__delete_task"):
        task_id = tool_input.get("id", "")
        return f"task: delete {task_id}" if task_id else "task: delete"

    if tool_name.endswith("__decompose_task"):
        task_id = tool_input.get("id", "")
        return f"task: decompose {task_id}" if task_id else "task: decompose"

    if tool_name.endswith("__reorder_children"):
        return "task: reorder"

    if tool_name.endswith("__rebuild_index"):
        return "task: rebuild index"

    # PKB memory/knowledge operations
    if tool_name.endswith("__create_memory"):
        title = tool_input.get("title", "")
        if title:
            return f"memory: store '{title[:60]}'"
        content = tool_input.get("body", tool_input.get("content", ""))
        if content:
            preview = content[:50].replace("\n", " ")
            return f"memory: store '{preview}'"
        return "memory: store"

    if tool_name.endswith("__delete"):
        doc_id = tool_input.get("id", "")
        return f"pkb: delete {doc_id}" if doc_id else "pkb: delete"

    if tool_name.endswith("__append"):
        doc_id = tool_input.get("id", "")
        return f"pkb: append to {doc_id}" if doc_id else "pkb: append"

    if tool_name.endswith("__create") and not tool_name.endswith("__create_task"):
        title = tool_input.get("title", "")
        doc_type = tool_input.get("type", "")
        if title:
            return f"pkb: create {doc_type} '{title[:60]}'"
        return f"pkb: create {doc_type}" if doc_type else "pkb: create"

    # Write/Edit to data paths - categorize by file path
    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        return _categorize_data_path(file_path)

    return "sync: auto-commit"


def _categorize_data_path(file_path: str) -> str:
    """Categorize a file path into a commit message (mirrors brain-sync.sh logic)."""
    if not file_path or not file_path.strip():
        return "sync: auto-commit"
    file_path = file_path.strip()

    # Resolve to relative path within ACA_DATA if possible
    aca_data = os.environ.get("ACA_DATA", "")
    if aca_data:
        try:
            rel = str(Path(file_path).resolve().relative_to(Path(aca_data).resolve()))
            file_path = rel
        except ValueError:
            pass

    parts = file_path.split("/")
    if not parts:
        return "sync: auto-commit"

    first_dir = parts[0]
    basename = Path(file_path).stem

    if first_dir == "knowledge":
        if len(parts) >= 3:
            return f"knowledge: {parts[1]}/{basename}"
        return f"knowledge: {basename}"
    elif first_dir == "aops" and len(parts) >= 3 and parts[1] == "tasks":
        return f"task: {basename}"
    elif first_dir == "daily":
        return f"daily: {basename}"
    elif first_dir == "projects" and len(parts) >= 2:
        return f"project: {parts[1]}"
    elif first_dir == "context":
        return f"context: {basename}"
    elif first_dir == "goals":
        return f"goal: {basename}"
    elif first_dir == "academic":
        return f"academic: {basename}"

    return f"{first_dir}: {basename}" if basename else first_dir


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
            raise ValueError("Bash tool_input requires 'command' parameter (P#8: fail-fast)")
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

    # PKB write operations (knowledge base) -> data repo
    # Use suffix matching to be client-agnostic (handles mcp__pkb__,
    # mcp__plugin_aops-core_pkb__, etc.)
    pkb_write_suffixes = (
        "__create_memory",
        "__create",
        "__append",
        "__delete",
    )
    if any(tool_name.endswith(s) for s in pkb_write_suffixes):
        modified.add("data")

    # Task MCP tools (task management) -> data repo
    # Use suffix matching to be client-agnostic (handles mcp__tasks__,
    # mcp__pkb__, etc.)
    tasks_write_suffixes = (
        "__create_task",
        "__update_task",
        "__complete_task",
        "__delete_task",
        "__decompose_task",
        "__complete_tasks",
        "__reorder_children",
        "__rebuild_index",
    )
    if any(tool_name.endswith(s) for s in tasks_write_suffixes):
        modified.add("data")

    # Write/Edit operations - check path to determine repo
    if tool_name in ["Write", "Edit"]:
        if "file_path" not in tool_input:
            raise ValueError(
                "Write/Edit tool_input requires 'file_path' parameter (P#8: fail-fast)"
            )
        file_path = tool_input["file_path"]
        # Check if path is under ACA_DATA
        aca_data = os.environ.get("ACA_DATA", "")
        if aca_data:
            try:
                Path(file_path).resolve().relative_to(Path(aca_data).resolve())
                modified.add("data")
            except ValueError:
                pass
        # Legacy fallback: relative "data/" paths
        if "data/" in file_path or file_path.startswith("data/"):
            modified.add("data")

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
    repo_path: Path,
    subdir: str | None = None,
    commit_prefix: str = "update",
    commit_message: str | None = None,
) -> tuple[bool, str]:
    """Commit and push changes in a repo (optionally scoped to subdir).

    Syncs with remote before committing to prevent conflicts.
    Will NOT auto-commit to main/master branches, UNLESS the repo
    is $ACA_DATA (which only uses main).

    Args:
        repo_path: Path to repository root
        subdir: Optional subdirectory to add (e.g., "data/"). If None, adds all.
        commit_prefix: Prefix for commit message (e.g., "update(data)" or "update(framework)")
        commit_message: Full commit message. If provided, overrides auto-generated message.

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Branch protection: never auto-commit to main/master
    # Exception: ACA_DATA repo uses main as its only branch
    current_branch = get_current_branch(repo_path)
    if is_protected_branch(current_branch) and not is_aca_data_repo(repo_path):
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
        if commit_message:
            commit_msg = commit_message
        else:
            scope = subdir.rstrip("/") if subdir else "all"
            commit_msg = f"{commit_prefix}: auto-commit ({scope})"

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
