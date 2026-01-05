#!/usr/bin/env python3
"""
PostToolUse hook: Auto-commit data/ changes after state-modifying operations.

This hook detects when operations modify the personal knowledge base or task
database and automatically commits/pushes changes to prevent data loss and
enable cross-device sync.

Enforces: A#28 (Current State Machine - $ACA_DATA always up-to-date)

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

        # Verify not in partial rebase state
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
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
        Set of repo types modified: "data", "aops", or both
    """
    modified = set()

    # Task script patterns (Bash commands) -> data repo
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

    # Write/Edit operations - check path to determine repo
    if tool_name in ["Write", "Edit"]:
        file_path = tool_input.get("file_path", "")
        if "data/" in file_path or file_path.startswith("data/"):
            modified.add("data")
        if "academicOps/" in file_path or "/academicOps" in file_path:
            modified.add("aops")
        # Also check AOPS env var path
        import os

        aops_path = os.environ.get("AOPS", "")
        if aops_path and file_path.startswith(aops_path):
            modified.add("aops")

    return modified


def has_repo_changes(repo_path: Path, subdir: str | None = None) -> bool:
    """Check if there are uncommitted changes in repo (optionally in subdir).

    Args:
        repo_path: Path to repository root
        subdir: Optional subdirectory to check (e.g., "data/")

    Returns:
        True if uncommitted changes exist, False otherwise
    """
    try:
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
        return bool(result.stdout.strip())
    except Exception:
        return False


def get_aops_root() -> Path | None:
    """Get the AOPS repository root path.

    Returns:
        Path to AOPS root, or None if not available
    """
    import os

    aops_path = os.environ.get("AOPS")
    if aops_path:
        return Path(aops_path)
    return None


def commit_and_push_repo(
    repo_path: Path, subdir: str | None = None, commit_prefix: str = "update"
) -> tuple[bool, str]:
    """Commit and push changes in a repo (optionally scoped to subdir).

    Syncs with remote before committing to prevent conflicts.

    Args:
        repo_path: Path to repository root
        subdir: Optional subdirectory to add (e.g., "data/"). If None, adds all.
        commit_prefix: Prefix for commit message (e.g., "update(data)" or "update(framework)")

    Returns:
        Tuple of (success: bool, message: str)
    """
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

    # Check which repos were modified
    modified_repos = get_modified_repos(tool_name, tool_input)
    if not modified_repos:
        # Not a state operation, continue normally
        print(json.dumps({}))
        sys.exit(0)

    messages = []

    # Handle data/ repo (writing repo)
    if "data" in modified_repos:
        try:
            from lib.paths import get_data_root

            data_root = get_data_root()

            # Find git root containing data directory
            data_repo = data_root
            while data_repo != data_repo.parent:
                if (data_repo / ".git").exists():
                    break
                data_repo = data_repo.parent

            if has_repo_changes(data_repo, "data/"):
                success, message = commit_and_push_repo(
                    data_repo, "data/", "update(data)"
                )
                if success:
                    messages.append("data: committed")
                else:
                    messages.append(f"data: {message}")
        except Exception as e:
            messages.append(f"data: error - {e}")

    # Handle AOPS repo (framework repo)
    if "aops" in modified_repos:
        aops_root = get_aops_root()
        if aops_root and aops_root.exists():
            if has_repo_changes(aops_root):
                success, message = commit_and_push_repo(
                    aops_root, None, "update(framework)"
                )
                if success:
                    messages.append("framework: committed")
                else:
                    messages.append(f"framework: {message}")

    # Build output message
    if not messages:
        print(json.dumps({}))
        sys.exit(0)

    combined = "; ".join(messages)
    success = all("committed" in m for m in messages)

    if success:
        # Notify user of automatic commit
        if "push failed" in combined.lower():
            output = {"systemMessage": f"✓ Changes committed locally. ⚠ {combined}"}
        else:
            output = {"systemMessage": f"✓ Auto-committed: {combined}"}
    else:
        # Log error but continue (don't block workflow)
        output = {"systemMessage": f"⚠ Auto-commit issue: {combined}"}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
