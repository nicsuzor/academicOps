#!/usr/bin/env python3
"""Integration tests for autocommit_state.py hook.

Tests verify that changes to data/ are automatically committed and pushed
after operations that modify state files.

These are E2E tests that actually execute git operations in a test repository.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Create a test git repository with data/ structure."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create data/ structure
    (repo_dir / "data").mkdir()
    (repo_dir / "data" / "tasks").mkdir()
    (repo_dir / "data" / "projects").mkdir()
    (repo_dir / "data" / "sessions").mkdir()

    # Create initial README to have something to commit
    (repo_dir / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    return repo_dir


@pytest.fixture
def hook_script() -> Path:
    """Return path to the autocommit hook script."""
    return Path(__file__).parent.parent.parent / "hooks" / "autocommit_state.py"


def test_hook_detects_task_script_execution(hook_script: Path) -> None:
    """Test that hook correctly identifies task script operations."""
    # Arrange
    tool_input = {
        "toolName": "Bash",
        "toolInput": {
            "command": "python skills/tasks/scripts/task_add.py --title 'Test task'",
        }
    }

    # Act
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        check=True,
    )

    # Assert - hook should process this (output something or exit 0)
    assert result.returncode == 0


def test_hook_detects_memory_operations(hook_script: Path) -> None:
    """Test that hook correctly identifies memory server MCP operations."""
    # Arrange
    tool_input = {
        "toolName": "mcp__memory__store_memory",
        "toolInput": {
            "content": "Test content",
            "metadata": {
                "tags": "test",
            },
        }
    }

    # Act
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        check=True,
    )

    # Assert
    assert result.returncode == 0


def test_hook_ignores_non_state_operations(hook_script: Path) -> None:
    """Test that hook ignores operations that don't modify data/."""
    # Arrange
    tool_input = {"toolName": "Read", "toolInput": {"file_path": "/some/file.txt"}}

    # Act
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        check=True,
    )

    # Assert - should pass through with empty output
    assert result.returncode == 0
    output = json.loads(result.stdout) if result.stdout.strip() else {}
    assert "systemMessage" not in output or output.get("systemMessage") == ""


def test_hook_commits_and_pushes_task_changes(
    test_repo: Path, hook_script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E test: Hook commits and pushes changes to data/tasks/."""
    # Arrange
    monkeypatch.chdir(test_repo)

    # Create a task file to simulate task script operation
    task_file = test_repo / "data" / "tasks" / "inbox" / "test-task.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Test Task\n\nTest content\n")

    # Simulate tool input that would trigger the hook
    tool_input = {
        "toolName": "Bash",
        "toolInput": {
            "command": "python skills/tasks/scripts/task_add.py --title 'Test'",
        }
    }

    # Act
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(test_repo)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        cwd=test_repo,
        env=env,
        check=True,
    )

    # Assert
    assert result.returncode == 0

    # Verify commit was created
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=test_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (
        "update(data)" in log_result.stdout.lower()
        or "auto-commit" in log_result.stdout.lower()
    )

    # Verify task file is committed
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=test_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (
        "data/tasks/" not in status_result.stdout
    )  # Should be committed, not in working tree


def test_hook_commits_any_data_directory_changes(
    test_repo: Path, hook_script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E test: Hook commits changes to any data/ subdirectory."""
    # Arrange
    monkeypatch.chdir(test_repo)

    # Create files in different data/ subdirectories
    (test_repo / "data" / "projects" / "test-project.md").write_text("# Project\n")
    (test_repo / "data" / "sessions" / "test-session.jsonl").write_text(
        '{"test": true}\n'
    )

    # Simulate memory server operation
    tool_input = {
        "toolName": "mcp__memory__store_memory",
        "toolInput": {
            "content": "Content",
            "metadata": {
                "tags": "test",
            },
        }
    }

    # Act
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(test_repo)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        cwd=test_repo,
        env=env,
        check=True,
    )

    # Assert
    assert result.returncode == 0

    # Verify all data/ changes are committed
    status_result = subprocess.run(
        ["git", "status", "--porcelain", "data/"],
        cwd=test_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert status_result.stdout.strip() == ""  # All changes committed


def test_hook_handles_no_changes_gracefully(
    test_repo: Path, hook_script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that hook handles case where no changes exist in data/."""
    # Arrange
    monkeypatch.chdir(test_repo)

    # No changes to data/
    tool_input = {
        "toolName": "Bash",
        "toolInput": {
            "command": "python skills/tasks/scripts/task_view.py",
        }
    }

    # Act
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(test_repo)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        cwd=test_repo,
        env=env,
        check=True,
    )

    # Assert - should not fail, just pass through
    assert result.returncode == 0
    output = json.loads(result.stdout) if result.stdout.strip() else {}
    # Should not show commit message since there were no changes
    if "systemMessage" in output:
        assert "auto-commit" not in output["systemMessage"].lower()


def test_hook_handles_git_failures_gracefully(
    test_repo: Path, hook_script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that hook handles git failures without blocking workflow."""
    # Arrange
    monkeypatch.chdir(test_repo)

    # Create change but make git push fail (no remote)
    task_file = test_repo / "data" / "tasks" / "test.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Test\n")

    tool_input = {
        "toolName": "Bash",
        "toolInput": {
            "command": "python skills/tasks/scripts/task_add.py --title 'Test'",
        }
    }

    # Act
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(test_repo)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        cwd=test_repo,
        env=env,
        check=False,
    )

    # Assert - hook should not fail even if push fails
    assert result.returncode == 0

    # Should show warning about push failure
    try:
        output = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        # If JSON parsing fails, check raw stdout
        output = {"systemMessage": result.stdout}

    if "systemMessage" in output:
        # Either succeeded with commit or warned about push failure
        assert (
            "auto-commit" in output["systemMessage"].lower()
            or "push failed" in output["systemMessage"].lower()
            or "warning" in output["systemMessage"].lower()
        )


def test_hook_extracts_tool_name_from_correct_location(
    test_repo: Path, hook_script: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E test: Hook correctly extracts toolName from top-level input structure.

    This test demonstrates the bug where the hook looks for 'name' inside 'toolInput'
    instead of 'toolName' at the top level of the PostToolUse hook input.

    The correct PostToolUse input structure from Claude Code is:
    {
        "toolName": "mcp__memory__store_memory",  # Top level
        "toolInput": {                             # Parameters
            "content": "...",
            "metadata": {...}
        }
    }

    But the hook incorrectly looks for: toolInput.get("name")
    Instead of: input_data.get("toolName")
    """
    # Arrange
    monkeypatch.chdir(test_repo)

    # Create a file in data/knowledge/ to simulate memory server output
    knowledge_dir = test_repo / "data" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    test_note = knowledge_dir / "test-note.md"
    test_note.write_text("# Test Note\n\nTest content from memory server store_memory.\n")

    # Use CORRECT PostToolUse input structure - toolName at top level
    hook_input = {
        "toolName": "mcp__memory__store_memory",  # This is the correct location
        "toolInput": {
            "content": "Test content from memory server store_memory.",
            "metadata": {
                "tags": "knowledge",
            },
        },
    }

    # Act
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(test_repo)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        cwd=test_repo,
        env=env,
        check=True,
    )

    # Assert
    assert result.returncode == 0

    # Verify hook detected this as a state-modifying operation and committed changes
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=test_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    # Should have created a commit for the knowledge base update
    assert (
        "update(data)" in log_result.stdout.lower()
        or "auto-commit" in log_result.stdout.lower()
    ), (
        f"Expected auto-commit for memory server operation, but got: {log_result.stdout}\n"
        f"Hook output: {result.stdout}\n"
        f"Hook stderr: {result.stderr}"
    )

    # Verify the knowledge file is committed (not in working tree)
    status_result = subprocess.run(
        ["git", "status", "--porcelain", "data/knowledge/"],
        cwd=test_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (
        "test-note.md" not in status_result.stdout
    ), f"File should be committed but is still in working tree: {status_result.stdout}"


# ============================================================================
# Sync-before-commit tests
# ============================================================================


@pytest.fixture
def test_repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a test git repository with a bare remote for testing sync."""
    # Create bare remote
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_dir, check=True, capture_output=True)

    # Create local repo
    repo_dir = tmp_path / "local_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Add remote
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_dir)],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create data/ structure and initial commit
    (repo_dir / "data").mkdir()
    (repo_dir / "data" / "tasks").mkdir()
    (repo_dir / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Push to remote and set upstream
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    return repo_dir, remote_dir


def test_can_sync_detects_detached_head(test_repo: Path) -> None:
    """Test that can_sync returns False for detached HEAD."""
    from hooks.autocommit_state import can_sync

    # Detach HEAD
    subprocess.run(
        ["git", "checkout", "--detach"],
        cwd=test_repo,
        check=True,
        capture_output=True,
    )

    can, reason = can_sync(test_repo)
    assert can is False
    assert "detached" in reason.lower()


def test_can_sync_detects_no_tracking_branch(test_repo: Path) -> None:
    """Test that can_sync returns False when no tracking branch is set."""
    from hooks.autocommit_state import can_sync

    # No remote, so no tracking branch
    can, reason = can_sync(test_repo)
    assert can is False
    assert "tracking" in reason.lower()


def test_can_sync_returns_true_when_syncable(
    test_repo_with_remote: tuple[Path, Path]
) -> None:
    """Test that can_sync returns True for a properly configured repo."""
    from hooks.autocommit_state import can_sync

    repo_dir, _ = test_repo_with_remote
    can, reason = can_sync(repo_dir)
    assert can is True
    assert reason == ""


def test_fetch_and_check_divergence_detects_behind(
    test_repo_with_remote: tuple[Path, Path], tmp_path: Path
) -> None:
    """Test that fetch_and_check_divergence detects when local is behind."""
    from hooks.autocommit_state import fetch_and_check_divergence

    repo_dir, remote_dir = test_repo_with_remote

    # Clone another copy and push a commit
    other_repo = tmp_path / "other_repo"
    subprocess.run(
        ["git", "clone", str(remote_dir), str(other_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "other@example.com"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other User"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    (other_repo / "other.txt").write_text("Other change\n")
    subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Other commit"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )

    # Now local should be 1 commit behind
    is_behind, count, error = fetch_and_check_divergence(repo_dir)
    assert is_behind is True
    assert count == 1
    assert error == ""


def test_fetch_and_check_divergence_not_behind(
    test_repo_with_remote: tuple[Path, Path]
) -> None:
    """Test that fetch_and_check_divergence returns not behind when up to date."""
    from hooks.autocommit_state import fetch_and_check_divergence

    repo_dir, _ = test_repo_with_remote
    is_behind, count, error = fetch_and_check_divergence(repo_dir)
    assert is_behind is False
    assert count == 0
    assert error == ""


def test_pull_rebase_if_behind_syncs_changes(
    test_repo_with_remote: tuple[Path, Path], tmp_path: Path
) -> None:
    """Test that pull_rebase_if_behind successfully syncs remote changes."""
    from hooks.autocommit_state import pull_rebase_if_behind

    repo_dir, remote_dir = test_repo_with_remote

    # Clone another copy and push a commit
    other_repo = tmp_path / "other_repo"
    subprocess.run(
        ["git", "clone", str(remote_dir), str(other_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "other@example.com"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other User"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    (other_repo / "other.txt").write_text("Other change\n")
    subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Other commit"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )

    # Fetch to update remote refs
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Now pull rebase
    success, msg = pull_rebase_if_behind(repo_dir)
    assert success is True
    assert "synced" in msg.lower()

    # Verify the file is now present
    assert (repo_dir / "other.txt").exists()


def test_pull_rebase_detects_conflict(
    test_repo_with_remote: tuple[Path, Path], tmp_path: Path
) -> None:
    """Test that pull_rebase_if_behind detects and aborts on conflict."""
    from hooks.autocommit_state import pull_rebase_if_behind

    repo_dir, remote_dir = test_repo_with_remote

    # Clone another copy, modify README, and push
    other_repo = tmp_path / "other_repo"
    subprocess.run(
        ["git", "clone", str(remote_dir), str(other_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "other@example.com"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other User"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    (other_repo / "README.md").write_text("# Other change\n")
    subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Other commit"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )

    # Make conflicting local change
    (repo_dir / "README.md").write_text("# Conflicting change\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Local commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Fetch to update remote refs
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Now pull rebase - should detect conflict and abort
    success, msg = pull_rebase_if_behind(repo_dir)
    assert success is False
    assert "conflict" in msg.lower() or "failed" in msg.lower()

    # Verify rebase was aborted (not in rebase state)
    rebase_dir = repo_dir / ".git" / "rebase-merge"
    rebase_apply = repo_dir / ".git" / "rebase-apply"
    assert not rebase_dir.exists()
    assert not rebase_apply.exists()


def test_autocommit_syncs_before_commit(
    test_repo_with_remote: tuple[Path, Path],
    tmp_path: Path,
    hook_script: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2E test: autocommit hook syncs with remote before committing."""
    repo_dir, remote_dir = test_repo_with_remote
    monkeypatch.chdir(repo_dir)

    # Clone another copy and push a commit
    other_repo = tmp_path / "other_repo"
    subprocess.run(
        ["git", "clone", str(remote_dir), str(other_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "other@example.com"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other User"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    (other_repo / "other.txt").write_text("Other change\n")
    subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Other commit"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=other_repo,
        check=True,
        capture_output=True,
    )

    # Create local data change
    task_file = repo_dir / "data" / "tasks" / "test-task.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Test Task\n")

    # Run hook
    tool_input = {
        "toolName": "Bash",
        "toolInput": {
            "command": "python skills/tasks/scripts/task_add.py --title 'Test'",
        }
    }
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["AOPS"]
    env["AOPS"] = os.environ["AOPS"]
    env["ACA_DATA"] = str(repo_dir)
    result = subprocess.run(
        ["python", str(hook_script)],
        input=json.dumps(tool_input),
        text=True,
        capture_output=True,
        cwd=repo_dir,
        env=env,
        check=True,
    )

    assert result.returncode == 0

    # Verify synced commits message
    output = json.loads(result.stdout) if result.stdout.strip() else {}
    if "systemMessage" in output:
        assert "synced" in output["systemMessage"].lower() or "committed" in output["systemMessage"].lower()

    # Verify remote commit was pulled (other.txt exists)
    assert (repo_dir / "other.txt").exists(), "Remote changes should have been synced"

    # Verify local change was committed
    status_result = subprocess.run(
        ["git", "status", "--porcelain", "data/"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    assert status_result.stdout.strip() == "", "Local changes should be committed"
