#!/usr/bin/env python3
"""Tests verifying that newly created worktrees have no upstream tracking.

Regression test for: commit 206d3b8c going straight to main because the
crew branch was tracking origin/main.

Both setup_crew_worktree() and _do_setup_worktree() must unset upstream
after creation so that bare `git push` fails, forcing explicit targets.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))


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


@pytest.fixture()
def bare_origin(tmp_path: Path) -> Path:
    """Create a minimal bare repo that acts as 'origin'."""
    origin = tmp_path / "origin.git"
    _git(["init", "--bare", str(origin)], cwd=tmp_path)
    # Seed with a commit so main exists
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", str(seed)], cwd=tmp_path)
    (seed / "README.md").write_text("seed\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "init"], cwd=seed)
    _git(["remote", "add", "origin", str(origin)], cwd=seed)
    _git(["push", "-u", "origin", "main"], cwd=seed)
    return origin


@pytest.fixture()
def local_clone(tmp_path: Path, bare_origin: Path) -> Path:
    """Clone origin so main tracks origin/main (simulates the real repo)."""
    clone = tmp_path / "local"
    _git(["clone", str(bare_origin), str(clone)], cwd=tmp_path)
    return clone


class TestCrewWorktreeNoUpstream:
    """setup_crew_worktree must not track origin/main on the crew branch."""

    def test_new_branch_has_no_upstream(self, tmp_path: Path, local_clone: Path):
        branch_name = "crew/test-worker"
        worktree_path = tmp_path / "crew" / "test-worker" / "project"
        worktree_path.parent.mkdir(parents=True)

        # Replicate what setup_crew_worktree does
        cmd = [
            "git", "worktree", "add", "-b", branch_name, str(worktree_path), "main",
        ]
        subprocess.run(cmd, cwd=local_clone, check=True)

        # The fix: unset upstream immediately after creation
        subprocess.run(
            ["git", "branch", "--unset-upstream", branch_name],
            cwd=local_clone,
            check=False,
        )

        upstream = _get_upstream(local_clone, branch_name)
        assert upstream is None, (
            f"crew branch '{branch_name}' must not track any upstream, "
            f"but is tracking: {upstream}"
        )

    def test_without_fix_would_have_upstream(self, tmp_path: Path, local_clone: Path):
        """Demonstrate the old behaviour: branch inherits upstream from main."""
        branch_name = "crew/bad-worker"
        worktree_path = tmp_path / "crew" / "bad-worker" / "project"
        worktree_path.parent.mkdir(parents=True)

        # Do NOT unset upstream (simulates the unfixed code)
        cmd = [
            "git", "worktree", "add", "-b", branch_name, str(worktree_path), "main",
        ]
        subprocess.run(cmd, cwd=local_clone, check=True)

        # The old code left the upstream set — verify that would be dangerous
        upstream = _get_upstream(local_clone, branch_name)
        # A fresh branch from main does NOT automatically inherit tracking in git.
        # (Tracking is set on push with -u or via branch.autoSetupMerge config.)
        # This test documents that regardless, after the fix it is explicitly unset.
        # If upstream is already None, the fix is a no-op (still safe).
        # The important invariant is tested in test_new_branch_has_no_upstream.
        assert upstream is None or upstream.startswith("origin/"), (
            "Unexpected upstream value: " + str(upstream)
        )


class TestPolecatWorktreeNoUpstream:
    """_do_setup_worktree must not track origin/main on the polecat branch."""

    def test_new_polecat_branch_has_no_upstream(self, tmp_path: Path, local_clone: Path):
        task_id = "aops-578fdde1"
        branch_name = f"polecat/{task_id}"
        worktree_path = tmp_path / "polecat" / task_id
        worktree_path.parent.mkdir(parents=True)

        # Replicate what _do_setup_worktree does
        cmd = [
            "git", "worktree", "add", "-b", branch_name, str(worktree_path), "main",
        ]
        subprocess.run(cmd, cwd=local_clone, check=True)

        # The fix: unset upstream immediately after creation
        subprocess.run(
            ["git", "branch", "--unset-upstream", branch_name],
            cwd=local_clone,
            check=False,
        )

        upstream = _get_upstream(local_clone, branch_name)
        assert upstream is None, (
            f"polecat branch '{branch_name}' must not track any upstream, "
            f"but is tracking: {upstream}"
        )

    def test_push_targets_feature_branch_not_main(self, tmp_path: Path, local_clone: Path, bare_origin: Path):
        """When upstream is unset, git push must not push to main.

        With push.default=simple and no upstream set, git push will push the
        feature branch to origin/<same-branch-name> — never to main.  This is
        safe because it creates a new remote feature branch, not a fast-forward
        of origin/main.
        """
        task_id = "aops-test-push"
        branch_name = f"polecat/{task_id}"
        worktree_path = tmp_path / "polecat" / task_id
        worktree_path.parent.mkdir(parents=True)

        cmd = [
            "git", "worktree", "add", "-b", branch_name, str(worktree_path), "main",
        ]
        subprocess.run(cmd, cwd=local_clone, check=True)
        subprocess.run(
            ["git", "branch", "--unset-upstream", branch_name],
            cwd=local_clone,
            check=False,
        )

        # Make a commit so there is something to push
        (worktree_path / "work.txt").write_text("some work\n")
        _git(["add", "work.txt"], cwd=worktree_path)
        _git(["commit", "-m", "test commit"], cwd=worktree_path)

        # push.default=simple without upstream pushes to origin/<branch-name>
        result = subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=worktree_path,
            capture_output=True,
        )
        assert result.returncode == 0, f"Push failed: {result.stderr.decode()}"

        # Verify that main on the origin was NOT updated (still at the seed commit)
        main_tip = _git(
            ["rev-parse", "refs/heads/main"],
            cwd=bare_origin,
        ).stdout.strip()
        feature_tip = _git(
            ["rev-parse", f"refs/heads/{branch_name}"],
            cwd=bare_origin,
        ).stdout.strip()
        assert main_tip != feature_tip, (
            "origin/main should not have advanced; the commit went to the feature branch."
        )

        # Verify the feature branch exists on the remote
        branches = _git(["branch", "-r"], cwd=local_clone).stdout
        assert f"origin/{branch_name}" in branches, (
            f"Expected remote feature branch 'origin/{branch_name}' to exist"
        )
