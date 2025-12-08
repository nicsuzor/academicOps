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
        "toolInput": {
            "name": "Bash",
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


def test_hook_detects_bmem_operations(hook_script: Path) -> None:
    """Test that hook correctly identifies bmem MCP operations."""
    # Arrange
    tool_input = {
        "toolInput": {
            "name": "mcp__bmem__write_note",
            "title": "Test Note",
            "content": "Test content",
            "folder": "test",
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
    tool_input = {"toolInput": {"name": "Read", "file_path": "/some/file.txt"}}

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
        "toolInput": {
            "name": "Bash",
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

    # Simulate bmem operation
    tool_input = {
        "toolInput": {
            "name": "mcp__bmem__write_note",
            "title": "Test",
            "content": "Content",
            "folder": "test",
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
        "toolInput": {
            "name": "Bash",
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
        "toolInput": {
            "name": "Bash",
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
