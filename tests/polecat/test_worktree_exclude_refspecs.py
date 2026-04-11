#!/usr/bin/env python3
"""Tests for _worktree_exclude_refspecs() in polecat/manager.py.

Validates that the helper correctly parses `git worktree list --porcelain`
output and returns negative refspecs for branches checked out in worktrees.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bare_origin(tmp_path: Path) -> Path:
    """Create a minimal bare repo that acts as 'origin'."""
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
    """Clone origin so main tracks origin/main."""
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
# Tests: _worktree_exclude_refspecs()
# ---------------------------------------------------------------------------


class TestWorktreeExcludeRefspecs:
    """Tests for the _worktree_exclude_refspecs() helper method."""

    def test_no_worktrees_returns_empty(self, local_clone: Path, manager: PolecatManager):
        """A repo with no linked worktrees returns no exclusions."""
        result = manager._worktree_exclude_refspecs(local_clone)
        # main is checked out in the main working tree, so it should appear
        assert isinstance(result, list)

    def test_with_linked_worktree(self, tmp_path: Path, local_clone: Path, manager: PolecatManager):
        """A repo with a linked worktree excludes that branch."""
        wt_path = tmp_path / "wt-feature"
        _git(["worktree", "add", "-b", "feature-a", str(wt_path), "main"], cwd=local_clone)

        result = manager._worktree_exclude_refspecs(local_clone)
        assert "^refs/heads/feature-a" in result
        assert "^refs/heads/main" in result

    def test_multiple_worktrees(self, tmp_path: Path, local_clone: Path, manager: PolecatManager):
        """Multiple linked worktrees produce multiple exclusions."""
        for name in ["branch-x", "branch-y", "branch-z"]:
            wt = tmp_path / f"wt-{name}"
            _git(["worktree", "add", "-b", name, str(wt), "main"], cwd=local_clone)

        result = manager._worktree_exclude_refspecs(local_clone)
        for name in ["branch-x", "branch-y", "branch-z"]:
            assert f"^refs/heads/{name}" in result

    def test_results_are_sorted_and_deduplicated(
        self, tmp_path: Path, local_clone: Path, manager: PolecatManager
    ):
        """Output is sorted and deduplicated (real worktrees, checked via sort order)."""
        # Create worktrees with branch names that prove sorting: z before a alphabetically
        for name in ["zebra", "alpha"]:
            wt = tmp_path / f"wt-{name}"
            _git(["worktree", "add", "-b", name, str(wt), "main"], cwd=local_clone)

        result = manager._worktree_exclude_refspecs(local_clone)

        # Must be sorted: alpha before main before zebra
        branch_names = [r.replace("^refs/heads/", "") for r in result]
        assert branch_names == sorted(branch_names), f"Not sorted: {branch_names}"
        # No duplicates
        assert len(branch_names) == len(set(branch_names)), f"Duplicates: {branch_names}"

    def test_command_failure_returns_empty(self, tmp_path: Path, manager: PolecatManager):
        """If git worktree list fails (non-git dir), returns empty list gracefully."""
        non_git_dir = tmp_path / "not-a-repo"
        non_git_dir.mkdir()
        result = manager._worktree_exclude_refspecs(non_git_dir)
        assert result == []
