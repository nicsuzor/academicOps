#!/usr/bin/env python3
"""Regression test for the A3/A8 unpushed-commits gate on nuke_worktree.

Motivation: task-0e4d20a8. An ephemeral crew container was torn down while
holding two unpushed commits; the work died with the container. The task
was still marked done, with a fabricated pr_url.

This test reproduces the condition — a worktree with local commits that
were never pushed to origin — and asserts that ``nuke_worktree`` refuses
to destroy it unless the caller opts in via ``allow_unpushed=True``.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from manager import PolecatManager  # noqa: E402

from tests.polecat.conftest import write_polecat_test_config  # noqa: E402


def _git(args, cwd, check=True):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture()
def bare_origin(tmp_path):
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
def local_clone(tmp_path, bare_origin):
    clone = tmp_path / "local"
    _git(["clone", str(bare_origin), str(clone)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=clone)
    _git(["config", "user.name", "Test User"], cwd=clone)
    return clone


@pytest.fixture()
def aca_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "aca_data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path, local_clone, monkeypatch):
    home = tmp_path / "polecat_home"
    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home,
        project_paths={"test": local_clone},
        crew_names=["cheryl"],
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    return home


@pytest.fixture()
def manager(polecat_home, aca_data):
    return PolecatManager(home_dir=polecat_home)


def _make_worktree_with_unpushed_commit(
    manager: PolecatManager, task_id: str, local_clone: Path
) -> Path:
    """Create a polecat-style worktree, commit to it, but do NOT push.

    Reproduces the cheryl 2026-04-18 state: worker made a commit, then the
    container was torn down before the push happened.
    """
    branch = f"polecat/{task_id}"
    worktree = manager.polecats_dir / task_id
    manager.polecats_dir.mkdir(parents=True, exist_ok=True)
    _git(
        ["worktree", "add", "-b", branch, str(worktree), "main"],
        cwd=local_clone,
    )
    _git(["config", "user.email", "test@test.example"], cwd=worktree)
    _git(["config", "user.name", "Test User"], cwd=worktree)
    (worktree / "work.txt").write_text("critical work that must not be lost\n")
    _git(["add", "work.txt"], cwd=worktree)
    _git(["commit", "-m", "unpushed work"], cwd=worktree)
    return worktree


class TestNukeUnpushedGate:
    def test_refuses_to_destroy_unpushed_commits(self, manager: PolecatManager, local_clone: Path):
        """nuke_worktree without allow_unpushed must refuse when commits exist locally only."""
        task_id = "aops-abc12345"
        worktree = _make_worktree_with_unpushed_commit(manager, task_id, local_clone)

        # force=True should NOT bypass the unpushed-commits gate — force is for
        # unmerged-WIP, allow_unpushed is for never-pushed integrity.
        with pytest.raises(RuntimeError, match="not been pushed|ahead of origin"):
            manager.nuke_worktree(task_id, force=True)

        assert worktree.exists(), "worktree must NOT be destroyed when gate refuses"

    def test_allow_unpushed_overrides_gate(self, manager: PolecatManager, local_clone: Path):
        """Explicit opt-in via allow_unpushed=True is the only way to discard."""
        task_id = "aops-abc12345"
        worktree = _make_worktree_with_unpushed_commit(manager, task_id, local_clone)

        manager.nuke_worktree(task_id, force=True, allow_unpushed=True)

        assert not worktree.exists()

    def test_passes_when_branch_is_pushed(self, manager: PolecatManager, local_clone: Path):
        """If the branch is pushed to origin, the gate does not fire."""
        task_id = "aops-abc12345"
        worktree = _make_worktree_with_unpushed_commit(manager, task_id, local_clone)
        # Push to origin so the gate sees origin/<branch> == HEAD.
        branch = f"polecat/{task_id}"
        _git(["push", "-u", "origin", f"{branch}:{branch}"], cwd=worktree)
        # Make sure the local clone has the updated tracking ref too.
        _git(["fetch", "origin", branch], cwd=local_clone)

        # force=True bypasses the unmerged-commits check; unpushed gate is
        # satisfied because the branch really is pushed.
        manager.nuke_worktree(task_id, force=True)
        assert not worktree.exists()

    def test_passes_when_pushed_to_different_branch(
        self, manager: PolecatManager, local_clone: Path
    ):
        """If the commits are pushed to a DIFFERENT branch on origin, the gate should NOT fire."""
        task_id = "aops-abc12345"
        worktree = _make_worktree_with_unpushed_commit(manager, task_id, local_clone)

        # Push to a DIFFERENT branch on origin
        branch = f"polecat/{task_id}"
        other_branch = "crew/sylvia_7df3"
        _git(["push", "origin", f"{branch}:refs/heads/{other_branch}"], cwd=worktree)

        # Fetch in local_clone so manager can see it (manager operates in local_clone/shared repo usually)
        _git(["fetch", "origin"], cwd=local_clone)

        # This should NOT raise RuntimeError after the fix.
        manager.nuke_worktree(task_id, force=True)
        assert not worktree.exists()
