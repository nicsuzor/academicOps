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
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports require the path insertions above.
from lib.task_model import Task  # noqa: E402
from manager import PolecatManager  # noqa: E402

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
    data_dir.mkdir()
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path: Path, local_clone: Path) -> Path:
    """Minimal polecat home dir with a config pointing at local_clone."""
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

    def test_new_branch_has_no_upstream(self, local_clone: Path, manager: PolecatManager):
        """Crew branch created via setup_crew_worktree() must not track any upstream."""
        manager.setup_crew_worktree("test-worker", "test")

        upstream = _get_upstream(local_clone, "crew/test-worker")
        assert upstream is None, (
            f"crew branch 'crew/test-worker' must not track any upstream after "
            f"setup_crew_worktree(), but is tracking: {upstream!r}. "
            f"The --unset-upstream fix in setup_crew_worktree() may have been removed."
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
        assert upstream == "origin/main", (
            f"Expected branch.autoSetupMerge=always to set upstream to 'origin/main' "
            f"but got: {upstream!r}. "
            f"The test setup (branch.autoSetupMerge=always in local_clone) may not be "
            f"working — check the bare_origin / local_clone fixtures."
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

    def test_new_polecat_branch_has_no_upstream(self, local_clone: Path, manager: PolecatManager):
        """Polecat branch created via _do_setup_worktree() must not track any upstream."""
        task_id = "aops-578fdde1"
        task = Task(id=task_id, title="regression test task", project="test")

        manager._do_setup_worktree(task)

        upstream = _get_upstream(local_clone, f"polecat/{task_id}")
        assert upstream is None, (
            f"polecat branch 'polecat/{task_id}' must not track any upstream after "
            f"_do_setup_worktree(), but is tracking: {upstream!r}. "
            f"The --unset-upstream fix in _do_setup_worktree() may have been removed."
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
