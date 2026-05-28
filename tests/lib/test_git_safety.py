"""Tests for lib/git_safety.ensure_worktree_push_safety.

Reproduces the push-to-main footgun that hit a Claude Code harness worktree:
a worktree branch whose upstream is ``origin/main``, which under the user's
global ``push.default=upstream`` makes a bare ``git push`` resolve to *main*.
The guard must neutralise this so pushes target the feature branch instead,
while leaving correctly-configured branches (main itself, self-tracking
feature branches) untouched.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib.git_safety import ensure_worktree_push_safety  # noqa: E402


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def _upstream(repo: Path, branch: str = "HEAD") -> str | None:
    r = _git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{upstream}}"],
        cwd=repo,
        check=False,
    )
    return (r.stdout.strip() or None) if r.returncode == 0 else None


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    """Bare repo acting as 'origin', seeded with a main branch."""
    o = tmp_path / "origin.git"
    _git(["init", "--bare", "-b", "main", str(o)], cwd=tmp_path)
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main", str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "t@e.x"], cwd=seed)
    _git(["config", "user.name", "T"], cwd=seed)
    (seed / "README.md").write_text("seed\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "init"], cwd=seed)
    _git(["remote", "add", "origin", str(o)], cwd=seed)
    _git(["push", "-u", "origin", "main"], cwd=seed)
    return o


@pytest.fixture()
def clone(tmp_path: Path, origin: Path) -> Path:
    """Clone of origin with the user's dangerous global preference replicated.

    ``push.default=upstream`` is exactly what turns a main-tracking upstream
    into an accidental push to main; ``extensions.worktreeConfig`` lets the
    guard write worktree-scoped config.
    """
    c = tmp_path / "clone"
    _git(["clone", str(origin), str(c)], cwd=tmp_path)
    _git(["config", "user.email", "t@e.x"], cwd=c)
    _git(["config", "user.name", "T"], cwd=c)
    _git(["config", "push.default", "upstream"], cwd=c)
    _git(["config", "extensions.worktreeConfig", "true"], cwd=c)
    return c


def _worktree_tracking_main(clone: Path, tmp_path: Path, branch: str) -> Path:
    """Create a worktree whose branch dangerously tracks origin/main."""
    wt = tmp_path / branch.replace("/", "_")
    _git(["worktree", "add", "-b", branch, str(wt), "main"], cwd=clone)
    _git(["branch", "--set-upstream-to=origin/main", branch], cwd=wt)
    assert _upstream(wt) == "origin/main", "precondition: branch must track origin/main"
    return wt


class TestEnsureWorktreePushSafety:
    def test_neutralises_main_tracking(self, clone: Path, tmp_path: Path):
        wt = _worktree_tracking_main(clone, tmp_path, "claude/feature-x")

        msg = ensure_worktree_push_safety(wt)

        assert msg is not None
        assert "push.default=current" in msg
        assert "claude/feature-x" in msg
        # Upstream tracking removed.
        assert _upstream(wt) is None
        # push.default=current now in effect for this worktree.
        assert _git(["config", "--get", "push.default"], cwd=wt).stdout.strip() == "current"

    def test_bare_push_targets_feature_branch_not_main(
        self, clone: Path, origin: Path, tmp_path: Path
    ):
        wt = _worktree_tracking_main(clone, tmp_path, "claude/feature-y")
        ensure_worktree_push_safety(wt)

        main_before = _git(["rev-parse", "refs/heads/main"], cwd=origin).stdout.strip()
        (wt / "work.txt").write_text("work\n")
        _git(["add", "work.txt"], cwd=wt)
        _git(["commit", "-m", "work"], cwd=wt)

        r = _git(["push"], cwd=wt, check=False)
        assert r.returncode == 0, f"bare push failed: {r.stderr}"

        main_after = _git(["rev-parse", "refs/heads/main"], cwd=origin).stdout.strip()
        assert main_after == main_before, "origin/main must NOT advance"
        feature_tip = _git(["rev-parse", "refs/heads/claude/feature-y"], cwd=origin).stdout.strip()
        assert feature_tip == _git(["rev-parse", "HEAD"], cwd=wt).stdout.strip(), (
            "the commit must land on the feature branch"
        )

    def test_without_guard_bare_push_hits_main(self, clone: Path, origin: Path, tmp_path: Path):
        """Non-vacuous proof: without the guard, the bare push DOES hit main."""
        wt = _worktree_tracking_main(clone, tmp_path, "claude/unfixed")
        # Deliberately do NOT call the guard.
        main_before = _git(["rev-parse", "refs/heads/main"], cwd=origin).stdout.strip()
        (wt / "w.txt").write_text("w\n")
        _git(["add", "w.txt"], cwd=wt)
        _git(["commit", "-m", "w"], cwd=wt)

        r = _git(["push"], cwd=wt, check=False)
        assert r.returncode == 0, f"push failed: {r.stderr}"

        main_after = _git(["rev-parse", "refs/heads/main"], cwd=origin).stdout.strip()
        assert main_after != main_before, (
            "expected the UNFIXED bare push to advance origin/main — if it didn't, "
            "the test no longer reproduces the bug and the other tests are vacuous"
        )

    def test_main_branch_untouched(self, clone: Path):
        # On main, tracking origin/main is correct; the guard must not touch it.
        assert _upstream(clone) == "origin/main"
        assert ensure_worktree_push_safety(clone) is None
        assert _upstream(clone) == "origin/main"

    def test_self_tracking_branch_untouched(self, clone: Path, tmp_path: Path):
        wt = tmp_path / "selftrack"
        _git(["worktree", "add", "-b", "claude/selftrack", str(wt), "main"], cwd=clone)
        _git(["push", "-u", "origin", "claude/selftrack:claude/selftrack"], cwd=wt)
        assert _upstream(wt) == "origin/claude/selftrack"

        assert ensure_worktree_push_safety(wt) is None
        assert _upstream(wt) == "origin/claude/selftrack"

    def test_no_upstream_is_noop(self, clone: Path, tmp_path: Path):
        wt = tmp_path / "noup"
        _git(["worktree", "add", "-b", "claude/noup", str(wt), "main"], cwd=clone)
        _git(["branch", "--unset-upstream", "claude/noup"], cwd=wt, check=False)
        assert _upstream(wt) is None
        assert ensure_worktree_push_safety(wt) is None

    def test_non_repo_is_noop(self, tmp_path: Path):
        plain = tmp_path / "plain"
        plain.mkdir()
        assert ensure_worktree_push_safety(plain) is None
