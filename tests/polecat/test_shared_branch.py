#!/usr/bin/env python3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

from tests.polecat.conftest import write_polecat_test_config  # noqa: E402


@dataclass
class DummyTask:
    id: str
    title: str = "Dummy"
    project: str | None = "test"
    branch: str | None = None


@pytest.fixture()
def mock_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PolecatManager:
    # Set up polecat home and config
    polecat_home = tmp_path / "polecat_home"
    polecat_home.mkdir(exist_ok=True)
    monkeypatch.setenv("POLECAT_HOME", str(polecat_home))

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir(exist_ok=True)

    write_polecat_test_config(tmp_path, home_dir=polecat_home, project_paths={"test": repo_path})

    return PolecatManager(home_dir=polecat_home)


def test_resolve_branch_name_priorities(
    mock_manager: PolecatManager, monkeypatch: pytest.MonkeyPatch
):
    task = DummyTask(id="task-123")

    # Priority 4: Default fallback
    assert mock_manager.resolve_branch_name(task) == "polecat/task-123"

    # Priority 3: Config file setting (polecat.yaml)
    mock_manager.config["branch"] = "config-epic-branch"
    assert mock_manager.resolve_branch_name(task) == "config-epic-branch"

    # Priority 2: Task frontmatter/field
    task.branch = "task-specific-branch"
    assert mock_manager.resolve_branch_name(task) == "task-specific-branch"

    # Priority 1: Env override
    monkeypatch.setenv("AOPS_POLECAT_BRANCH", "env-override-branch")
    assert mock_manager.resolve_branch_name(task) == "env-override-branch"

    monkeypatch.setenv("POLECAT_BRANCH", "another-env-branch")
    monkeypatch.delenv("AOPS_POLECAT_BRANCH")
    assert mock_manager.resolve_branch_name(task) == "another-env-branch"


def test_is_shared_branch(mock_manager: PolecatManager):
    # If task_id matches the branch suffix, it is not shared
    assert not mock_manager.is_shared_branch("polecat/task-123", "task-123")
    assert mock_manager.is_shared_branch("polecat/epic-abc", "task-123")

    # Crew branches are never shared
    assert not mock_manager.is_shared_branch("crew/nic")
    assert not mock_manager.is_shared_branch("crew/nic", "task-123")

    # Fallback checks without task_id (defaults to True unless it matches standard pattern)
    assert not mock_manager.is_shared_branch("polecat/aops-613690b5")
    assert mock_manager.is_shared_branch("polecat/epic-7b41c5bf")
    assert mock_manager.is_shared_branch("my-custom-branch")


def test_nuke_worktree_preserves_shared_branch(
    mock_manager: PolecatManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Setup dummy project repo and mirror
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.example"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    (repo_path / "README.md").write_text("Hello")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True)

    # Mock storage to return our task
    task = DummyTask(id="task-123", branch="polecat/shared-epic-branch")

    class MockStorage:
        def get_task(self, tid):
            return task if tid == "task-123" else None

    mock_manager.storage = MockStorage()

    # Set up worktree
    worktree_path = mock_manager.setup_worktree(task)
    assert worktree_path.exists()

    # Now verify the branch exists in the project repo
    result = subprocess.run(
        ["git", "branch", "--list", "polecat/shared-epic-branch"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "polecat/shared-epic-branch" in result.stdout

    # Nuke the worktree - should NOT delete the shared branch
    mock_manager.nuke_worktree("task-123", force=True)

    # Verify worktree directory is gone
    assert not worktree_path.exists()

    # Verify branch still exists in the repo because it's shared!
    result = subprocess.run(
        ["git", "branch", "--list", "polecat/shared-epic-branch"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "polecat/shared-epic-branch" in result.stdout
