#!/usr/bin/env python3
"""Regression tests for task-519a1356 — polecat must branch fresh from origin/main
when a re-dispatched task's prior remote branch is stale.

Staleness covers three modes:
  (a) Merge-commit merged — branch tip is an ancestor of origin/main.
  (b) Squash- or rebase-merged — branch tip is NOT an ancestor, but GitHub
      reports a merged PR on that branch. This was the unhandled case that
      caused the 2026-04-15 incident (worktree 305 commits behind main).
  (c) Abandoned — not merged, far behind main, no open PR.

In every case the new worktree must fork from origin/main, not the stale
remote branch.
"""

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
class Task:
    id: str
    title: str = ""
    project: str | None = "test"


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure git has a committer identity in all subprocess calls.

    Rebase replays commits, which requires creating new commits — and git
    refuses to do that without author/committer identity. The CI runner has
    none configured globally, so set it via environment variables instead.
    """
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test.example")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test.example")


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
    (seed / ".gitignore").write_text(".claude/\n.gemini/\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "init"], cwd=seed)
    _git(["remote", "add", "origin", str(origin)], cwd=seed)
    _git(["push", "-u", "origin", "main"], cwd=seed)
    return origin


@pytest.fixture()
def aca_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "aca_data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path: Path, bare_origin: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "polecat_home"
    home.mkdir()
    repos_dir = home / ".repos"
    repos_dir.mkdir()
    # Use a mirror clone of bare_origin as the "mirror"; manager will sync it.
    mirror = repos_dir / "test.git"
    _git(["clone", "--mirror", str(bare_origin), str(mirror)], cwd=tmp_path)

    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home,
        project_paths={"test": mirror},
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    return home


@pytest.fixture()
def manager(polecat_home: Path, aca_data: Path) -> PolecatManager:
    return PolecatManager(home_dir=polecat_home)


def _push_stale_polecat_branch(
    bare_origin: Path, tmp_path: Path, task_id: str, commits: int
) -> str:
    """Push a polecat/<task_id> branch that is diverged from main and looks stale.

    Then advances main by `commits` commits so the polecat branch is behind.
    Returns the SHA of the polecat branch tip.
    """
    seed = tmp_path / f"seed_{task_id}"
    _git(["clone", str(bare_origin), str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)

    # Create the polecat branch from main with a commit that does NOT land on main
    # (simulates squash-merge: the work is logically in main, but the branch tip
    # has a distinct commit hash that is not an ancestor).
    _git(["checkout", "-b", f"polecat/{task_id}"], cwd=seed)
    (seed / f"work_{task_id}.txt").write_text("feature work\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", f"feature work for {task_id}"], cwd=seed)
    _git(["push", "origin", f"polecat/{task_id}"], cwd=seed)
    branch_sha = _git(["rev-parse", "HEAD"], cwd=seed).stdout.strip()

    _git(["checkout", "main"], cwd=seed)
    for i in range(commits):
        _git(["commit", "--allow-empty", "-m", f"main advance {i}"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    return branch_sha


def test_abandoned_branch_far_behind_main_restarts_fresh(
    bare_origin: Path, manager: PolecatManager, tmp_path: Path
):
    """Branch that is >100 commits behind main with no merged/open PR is treated as
    stale and the worktree is forked from origin/main instead of raising or
    resuming from the stale branch."""
    task_id = "task-abandoned"
    branch_name = f"polecat/{task_id}"
    stale_sha = _push_stale_polecat_branch(bare_origin, tmp_path, task_id, commits=105)

    # Patch gh-based PR checks to simulate gh unavailable / no PRs.
    manager._branch_has_merged_pr = lambda *a, **kw: None  # type: ignore[method-assign]
    manager._crew_branch_open_pr = lambda *a, **kw: None  # type: ignore[method-assign]

    task = Task(id=task_id)
    worktree_path = manager._do_setup_worktree(task)

    # Worktree HEAD must match origin/main (forked fresh, not from stale tip).
    head = _git(["rev-parse", "HEAD"], cwd=worktree_path).stdout.strip()
    origin_main = _git(["rev-parse", "origin/main"], cwd=worktree_path).stdout.strip()
    assert head == origin_main, (
        f"Expected worktree HEAD to match origin/main ({origin_main[:8]}), "
        f"got {head[:8]} — worktree was forked from stale branch, not fresh main"
    )
    assert head != stale_sha, "Worktree must not resume from the stale branch tip"

    # Remote branch must have been rewritten to the fresh main tip, not left at stale.
    ls_remote = _git(
        ["ls-remote", "--heads", str(bare_origin), branch_name], cwd=tmp_path, check=False
    )
    if ls_remote.stdout.strip():
        remote_sha = ls_remote.stdout.split()[0]
        assert remote_sha != stale_sha, (
            f"Remote {branch_name} still points at stale tip {stale_sha[:8]}"
        )


def test_squash_merged_branch_detected_via_gh_restarts_fresh(
    bare_origin: Path, manager: PolecatManager, tmp_path: Path
):
    """Squash-merged branch (tip not ancestor of main) is detected via gh's
    merged-PR lookup and the worktree starts fresh from origin/main.

    This is the canonical re-dispatch case from task-519a1356: prior PR was
    squash-merged, branch was left behind, task revived, new run must not
    resume from the stale branch tip.
    """
    task_id = "task-squashed"
    branch_name = f"polecat/{task_id}"
    # Only 3 commits behind so commits_behind > 100 does NOT fire — gh is the
    # only signal that this branch is stale.
    stale_sha = _push_stale_polecat_branch(bare_origin, tmp_path, task_id, commits=3)

    # Simulate gh reporting a merged PR for the branch.
    merged_pr_url = "https://github.com/example/repo/pull/999"
    manager._branch_has_merged_pr = lambda repo_path, name: (  # type: ignore[method-assign]
        merged_pr_url if name == branch_name else None
    )
    manager._crew_branch_open_pr = lambda *a, **kw: None  # type: ignore[method-assign]

    task = Task(id=task_id)
    worktree_path = manager._do_setup_worktree(task)

    head = _git(["rev-parse", "HEAD"], cwd=worktree_path).stdout.strip()
    origin_main = _git(["rev-parse", "origin/main"], cwd=worktree_path).stdout.strip()
    assert head == origin_main, (
        "Worktree must be forked from origin/main when gh reports the branch has a merged PR"
    )
    assert head != stale_sha, "Worktree must not resume from the squash-merged branch tip"


def test_stale_branch_with_open_pr_refuses_destruction(
    bare_origin: Path, manager: PolecatManager, tmp_path: Path
):
    """If a branch is far behind main but has an OPEN PR, we must NOT delete it —
    that would discard in-flight review work. Raise instead.
    """
    task_id = "task-open-pr"
    _push_stale_polecat_branch(bare_origin, tmp_path, task_id, commits=105)

    manager._branch_has_merged_pr = lambda *a, **kw: None  # type: ignore[method-assign]
    manager._crew_branch_open_pr = lambda *a, **kw: "https://github.com/example/repo/pull/1"  # type: ignore[method-assign]

    task = Task(id=task_id)
    with pytest.raises(RuntimeError) as excinfo:
        manager._do_setup_worktree(task)

    assert "open PR" in str(excinfo.value)


def test_in_flight_branch_is_checked_out_not_recreated(
    bare_origin: Path, manager: PolecatManager, tmp_path: Path
):
    """A legitimately in-flight branch (not merged, not far behind) must still
    be resumed — not destroyed. This guards against the fix over-reaching.
    """
    task_id = "task-in-flight"
    branch_name = f"polecat/{task_id}"
    # Push a branch with work, only 2 commits behind main, no merged PR.
    branch_sha = _push_stale_polecat_branch(bare_origin, tmp_path, task_id, commits=2)

    manager._branch_has_merged_pr = lambda *a, **kw: None  # type: ignore[method-assign]
    manager._crew_branch_open_pr = lambda *a, **kw: None  # type: ignore[method-assign]

    task = Task(id=task_id)
    worktree_path = manager._do_setup_worktree(task)

    head = _git(["rev-parse", "HEAD"], cwd=worktree_path).stdout.strip()
    # After auto-rebase onto origin/main, HEAD changes — but the branch's
    # feature commit (work_*.txt) must still be present.
    assert (worktree_path / f"work_{task_id}.txt").exists(), (
        f"In-flight branch work was lost — worktree HEAD {head[:8]} does not "
        f"contain the feature file (branch tip was {branch_sha[:8]})"
    )

    # Remote branch must still exist.
    ls_remote = _git(
        ["ls-remote", "--heads", str(bare_origin), branch_name], cwd=tmp_path, check=False
    )
    assert ls_remote.stdout.strip() != "", "In-flight remote branch must be preserved"
