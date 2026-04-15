#!/usr/bin/env python3
"""Regression tests: polecat must fail fast when task.project is missing/invalid.

Bug: polecat silently clones the wrong repo when a task's ``project`` field is
missing, invalid, or the task has been deleted. Several call sites in
``polecat/manager.py`` silently coerce a missing/unknown project into
``"aops"`` (or fall back to ``REPO_ROOT``), which meant tasks targeting any
other project could end up operating against the academicOps checkout.

User preference (CORE.md): fail fast. Silent defaults are wrong.

These tests lock in the new contract:
- ``get_repo_path`` raises ``ValueError`` when ``task.project`` is falsy.
- ``get_repo_path`` raises ``ValueError`` when ``task.project`` is unknown
  (not configured in ``polecat.yaml`` and no bare mirror on disk).
- ``get_repo_path`` still returns the configured path for known projects.
- ``_do_setup_worktree`` / ``setup_worktree`` refuse to operate without a
  project — no clone attempt happens.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402


@dataclass
class Task:
    """Minimal Task stub matching the shape used across polecat tests."""

    id: str
    title: str = ""
    project: str | None = None


# ---------------------------------------------------------------------------
# Fixtures (mirrored from test_worktree_upstream.py)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture()
def bare_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    _git(["init", "--bare", "-b", "main", str(origin)], cwd=tmp_path)

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main", str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)
    (seed / "README.md").write_text("seed\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "init"], cwd=seed)
    _git(["remote", "add", "origin", str(origin)], cwd=seed)
    _git(["push", "-u", "origin", "main"], cwd=seed)
    return origin


@pytest.fixture()
def local_clone(tmp_path: Path, bare_origin: Path) -> Path:
    clone = tmp_path / "local"
    _git(["clone", str(bare_origin), str(clone)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=clone)
    _git(["config", "user.name", "Test User"], cwd=clone)
    return clone


@pytest.fixture()
def aca_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "aca_data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path: Path, local_clone: Path) -> Path:
    home = tmp_path / "polecat_home"
    home.mkdir()
    config = {
        "projects": {
            "test": {
                "path": str(local_clone),
                "default_branch": "main",
            }
        },
        "crew_names": ["test-worker"],
    }
    (home / "polecat.yaml").write_text(yaml.dump(config))
    return home


@pytest.fixture()
def manager(polecat_home: Path, aca_data: Path) -> PolecatManager:
    return PolecatManager(home_dir=polecat_home)


# ---------------------------------------------------------------------------
# get_repo_path validation
# ---------------------------------------------------------------------------


class TestGetRepoPathValidation:
    def test_missing_project_raises(self, manager: PolecatManager):
        """task.project=None must raise ValueError mentioning 'project'."""
        task = Task(id="x", project=None)
        with pytest.raises(ValueError, match="project"):
            manager.get_repo_path(task)

    def test_empty_project_raises(self, manager: PolecatManager):
        """task.project='' must raise ValueError mentioning 'project'."""
        task = Task(id="x", project="")
        with pytest.raises(ValueError, match="project"):
            manager.get_repo_path(task)

    def test_unknown_project_raises(self, manager: PolecatManager):
        """Unknown project (no config entry, no mirror) must raise ValueError
        mentioning the unknown project name."""
        task = Task(id="x", project="nonexistent")
        with pytest.raises(ValueError, match="nonexistent"):
            manager.get_repo_path(task)

    def test_known_project_returns_path(self, manager: PolecatManager, local_clone: Path):
        """A known project must still return the configured path without raising."""
        task = Task(id="x", project="test")
        result = manager.get_repo_path(task)
        assert result == local_clone


# ---------------------------------------------------------------------------
# setup_worktree validation
# ---------------------------------------------------------------------------


class TestSetupWorktreeValidation:
    def test_setup_worktree_missing_project_raises(self, manager: PolecatManager):
        """_do_setup_worktree must refuse a task with no project before any
        clone operation happens (fail fast)."""
        task = Task(id="aops-novalidproject", project=None)
        with pytest.raises(ValueError, match="project"):
            manager._do_setup_worktree(task)
