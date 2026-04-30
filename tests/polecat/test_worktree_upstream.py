#!/usr/bin/env python3
"""Regression tests for aops-578fdde1 — polecat worktree upstream tracking safety.

The upstream fix (unsetting tracking after worktree creation) lives in
setup_crew_worktree() and _do_setup_worktree() in polecat/manager.py.

These tests call the actual framework functions and FAIL if the
``--unset-upstream`` calls are removed from manager.py.

How the regression condition is reproduced
------------------------------------------
By default, ``git worktree add -b branch main`` does not set upstream tracking
because ``branch.autoSetupMerge`` only propagates tracking from remote-tracking
branches, not from local ones.  The original bug required a git config where
``branch.autoSetupMerge = always`` — which propagates tracking even from local
branches whose own upstream is set (main → origin/main → new branch inherits
origin/main).

The fixtures therefore set ``branch.autoSetupMerge = always`` in the cloned
repo.  With that config in place:

- Without the fix: ``git worktree add -b branch main`` leaves the branch
  tracking ``origin/main``.
- With the fix: ``--unset-upstream`` immediately removes that tracking.

The test ``test_without_fix_upstream_would_be_set`` exists to verify that our
setup actually replicates the dangerous condition, so that future readers can
confirm the other tests are not vacuous.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports require the path insertions above.
from manager import PolecatManager  # noqa: E402

from tests.polecat.conftest import write_polecat_test_config  # noqa: E402


@dataclass
class Task:
    """Minimal Task stub — lib.task_model has been deleted, polecat migrates to MCP."""

    id: str
    title: str = ""
    project: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


def _get_upstream(repo: Path, branch: str) -> str | None:
    """Return the upstream tracking branch for *branch*, or None if unset."""
    result = _git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{upstream}}"],
        cwd=repo,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bare_origin(tmp_path: Path) -> Path:
    """Create a minimal bare repo that acts as 'origin'."""
    origin = tmp_path / "origin.git"
    _git(["init", "--bare", "-b", "main", str(origin)], cwd=tmp_path)

    # Seed with a commit so main exists; use a sub-dir as a throwaway workspace.
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main", str(seed)], cwd=tmp_path)
    # Set repo-local identity so the commit works in CI without global git config.
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
    """Clone origin so main tracks origin/main (simulates the real repo).

    Sets ``branch.autoSetupMerge = always`` to replicate the dangerous git
    config that caused the original bug.  With this config, ``git worktree add
    -b branch main`` makes the new branch track ``origin/main`` — exactly the
    condition that the ``--unset-upstream`` fix addresses.
    """
    clone = tmp_path / "local"
    _git(["clone", str(bare_origin), str(clone)], cwd=tmp_path)
    # Identity needed for later commits in worktrees.
    _git(["config", "user.email", "test@test.example"], cwd=clone)
    _git(["config", "user.name", "Test User"], cwd=clone)
    # Replicate the dangerous config (autoSetupMerge=always propagates upstream
    # even from local branches, so new branches inherit origin/main tracking).
    _git(["config", "branch.autoSetupMerge", "always"], cwd=clone)
    return clone


@pytest.fixture()
def aca_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal ACA_DATA directory and set the env var.

    PolecatManager.__init__ instantiates TaskStorage(), which requires
    ACA_DATA to be set to an existing path.
    """
    data_dir = tmp_path / "aca_data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path: Path, local_clone: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal polecat home dir + sessions registry pointing at local_clone."""
    home = tmp_path / "polecat_home"
    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home,
        project_paths={"test": local_clone},
        crew_names=["test-worker"],
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    return home


@pytest.fixture()
def manager(polecat_home: Path, aca_data: Path) -> PolecatManager:
    """PolecatManager instance wired to temp repos and a temp data dir."""
    return PolecatManager(home_dir=polecat_home)


# ---------------------------------------------------------------------------
# Tests: setup_crew_worktree()
# ---------------------------------------------------------------------------


class TestCrewWorktreeNoUpstream:
    """setup_crew_worktree() must not leave the crew branch tracking origin/main.

    These tests call the actual manager function and fail if the
    ``--unset-upstream`` call is removed from setup_crew_worktree() in
    manager.py, because ``branch.autoSetupMerge=always`` (set in the
    local_clone fixture) causes the new branch to inherit origin/main tracking.
    """

    def test_new_branch_tracks_self_not_main(self, local_clone: Path, manager: PolecatManager):
        """Crew branch created via setup_crew_worktree() must track itself, not main."""
        worktree_path = manager.setup_crew_worktree("test-worker", "test")

        upstream = _get_upstream(worktree_path, "crew/test-worker")
        # Should track origin/crew/test-worker, definitely NOT origin/main
        assert upstream == "origin/crew/test-worker", (
            f"crew branch 'crew/test-worker' should track itself, but is tracking: {upstream!r}. "
            f"It must NOT track origin/main."
        )

    def test_without_fix_upstream_would_be_set(self, tmp_path: Path, local_clone: Path):
        """Proves the test setup replicates the dangerous condition.

        With ``branch.autoSetupMerge=always``, a plain ``git worktree add -b
        branch main`` (without the subsequent ``--unset-upstream``) leaves the
        branch tracking ``origin/main``.  This test asserts that condition, so
        we know the other tests above are not vacuously passing due to git
        already being safe.
        """
        branch_name = "crew/unfixed-worker"
        worktree_path = tmp_path / "unfixed"
        # Create worktree WITHOUT calling --unset-upstream (simulates unfixed code).
        _git(
            ["worktree", "add", "-b", branch_name, str(worktree_path), "main"],
            cwd=local_clone,
        )
        upstream = _get_upstream(local_clone, branch_name)
        assert upstream in ("main", "origin/main"), (
            f"Expected branch.autoSetupMerge=always to set an upstream tracking branch "
            f"but got: {upstream!r}. "
            f"The test setup (branch.autoSetupMerge=always in local_clone) may not be "
            f"working — check the bare_origin / local_clone fixtures."
        )


class TestCrewBranchFlush:
    """Regression: reusing a crew name must not resume from stale state.

    The original bug: nuke_crew only deleted the local branch, leaving
    origin/crew/<name> intact. The next setup_crew_worktree would then
    check out the stale remote branch. And even on the fresh-branch path,
    the clone's default branch came from the (possibly stale) bare mirror,
    never from origin.
    """

    def test_nuke_flushes_remote_branch(
        self, local_clone: Path, bare_origin: Path, manager: PolecatManager
    ):
        """nuke_crew must delete the remote crew branch on origin."""
        worktree = manager.setup_crew_worktree("test-worker", "test")
        # Verify remote branch exists (setup pushed it)
        ls = _git(
            ["ls-remote", "--heads", str(bare_origin), "crew/test-worker"],
            cwd=local_clone,
        )
        assert ls.stdout.strip(), "precondition: remote branch should exist after setup"

        manager.nuke_crew("test-worker", force=True)

        ls = _git(
            ["ls-remote", "--heads", str(bare_origin), "crew/test-worker"],
            cwd=local_clone,
        )
        assert not ls.stdout.strip(), (
            "nuke_crew must delete origin/crew/test-worker; it is still present"
        )
        assert not worktree.exists()

    def test_nuke_preserves_remote_when_pr_open(
        self,
        local_clone: Path,
        bare_origin: Path,
        manager: PolecatManager,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """nuke_crew(force=True) must preserve the remote branch when an open PR exists.

        force=True means "bypass the unmerged-WIP safety check", not "destroy PRs".
        The local worktree and local branch should still be cleaned up.
        """
        worktree = manager.setup_crew_worktree("test-worker", "test")
        ls = _git(
            ["ls-remote", "--heads", str(bare_origin), "crew/test-worker"],
            cwd=local_clone,
        )
        assert ls.stdout.strip(), "precondition: remote branch should exist after setup"

        # Force the classifier to report an open PR without needing real GitHub.
        monkeypatch.setattr(
            PolecatManager,
            "_crew_branch_open_pr",
            lambda self, repo_path, branch_name: "https://example.com/pr/1",
        )

        manager.nuke_crew("test-worker", force=True)

        ls = _git(
            ["ls-remote", "--heads", str(bare_origin), "crew/test-worker"],
            cwd=local_clone,
        )
        assert ls.stdout.strip(), (
            "nuke_crew(force=True) must preserve origin/crew/test-worker when an open PR "
            "exists; the branch was deleted"
        )
        assert not worktree.exists(), "local worktree cleanup should still happen"

    def test_new_crew_starts_from_fresh_origin_main(
        self, local_clone: Path, bare_origin: Path, tmp_path: Path, manager: PolecatManager
    ):
        """After nuke + recreate, the crew branch must base on the latest origin/main,
        even if the bare mirror's copy of main is stale.
        """
        manager.setup_crew_worktree("test-worker", "test")
        manager.nuke_crew("test-worker", force=True)

        # Advance origin/main from a side clone (simulates someone else pushing).
        side = tmp_path / "side"
        _git(["clone", str(bare_origin), str(side)], cwd=tmp_path)
        _git(["config", "user.email", "side@test.example"], cwd=side)
        _git(["config", "user.name", "Side"], cwd=side)
        (side / "new.txt").write_text("newer main\n")
        _git(["add", "new.txt"], cwd=side)
        _git(["commit", "-m", "advance main"], cwd=side)
        _git(["push", "origin", "main"], cwd=side)
        new_main_tip = _git(["rev-parse", "HEAD"], cwd=side).stdout.strip()

        # Recreate crew — must pick up the new origin/main tip.
        worktree = manager.setup_crew_worktree("test-worker", "test")
        crew_tip = _git(["rev-parse", "HEAD"], cwd=worktree).stdout.strip()
        assert crew_tip == new_main_tip, (
            f"New crew branch should base on fresh origin/main ({new_main_tip[:7]}), "
            f"but is at {crew_tip[:7]} — mirror staleness not fixed"
        )


# ---------------------------------------------------------------------------
# Tests: _do_setup_worktree()
# ---------------------------------------------------------------------------


class TestPolecatWorktreeNoUpstream:
    """_do_setup_worktree() must not leave the polecat branch tracking origin/main.

    These tests call the actual manager function and fail if the
    ``--unset-upstream`` call is removed from _do_setup_worktree() in
    manager.py.
    """

    def test_new_polecat_branch_tracks_self_not_main(
        self, local_clone: Path, manager: PolecatManager
    ):
        """Polecat branch created via _do_setup_worktree() must track itself, not main."""
        task_id = "aops-578fdde1"
        task = Task(id=task_id, title="regression test task", project="test")

        worktree_path = manager._do_setup_worktree(task)

        upstream = _get_upstream(worktree_path, f"polecat/{task_id}")
        expected = f"origin/polecat/{task_id}"
        assert upstream == expected, (
            f"polecat branch 'polecat/{task_id}' should track {expected}, but is tracking: {upstream!r}. "
            f"It must NOT track origin/main."
        )

    def test_push_targets_feature_branch_not_main(
        self,
        local_clone: Path,
        bare_origin: Path,
        manager: PolecatManager,
    ):
        """After _do_setup_worktree(), pushing must target the feature branch, not main.

        git push with an explicit remote/branch (the safe pattern enforced by the
        unset upstream) must create the feature branch on origin without advancing
        origin/main.
        """
        task_id = "aops-test-push"
        task = Task(id=task_id, title="push safety test", project="test")
        branch_name = f"polecat/{task_id}"

        worktree_path = manager._do_setup_worktree(task)

        # Make a commit so there is something to push.
        (worktree_path / "work.txt").write_text("some work\n")
        _git(["add", "work.txt"], cwd=worktree_path)
        _git(["commit", "-m", "test commit"], cwd=worktree_path)

        # Explicit push to the feature branch — the safe, expected pattern.
        result = _git(["push", "origin", branch_name], cwd=worktree_path, check=False)
        assert result.returncode == 0, f"Push failed: {result.stderr}"

        # Verify origin/main was NOT advanced.
        main_tip = _git(["rev-parse", "refs/heads/main"], cwd=bare_origin).stdout.strip()
        feature_tip = _git(
            ["rev-parse", f"refs/heads/{branch_name}"], cwd=bare_origin
        ).stdout.strip()
        assert main_tip != feature_tip, (
            "origin/main must not have advanced; the new commit must go to the feature branch only."
        )
