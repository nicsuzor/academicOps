"""Regression tests for polecat/cli.py workspace isolation (aops_f74aafce,
aops_aef75b26).

polecat used to bind-mount the shared canonical checkout (e.g.
/home/nic/src/academicOps) READ-WRITE straight into every worker container
as /workspace, with no per-task isolation. Concurrent containers each ran
their own `git checkout <task-branch>` inside that ONE shared tree, racing
every other container and every live interactive session reading the same
directory (confirmed via `git reflog` showing interleaved checkout/reset
across 3+ branches in quick succession — see aops_f74aafce for the full
containment evidence).

The first fix (`resolve_isolated_workspace` / `cleanup_isolated_workspace`
in cli.py) used a `git worktree add` per session. That closed the race but
introduced a new failure (aops_aef75b26, reproduced live against this fix's
own acceptance test): a linked worktree's `.git` is a *file* pointing at an
absolute host path inside the parent repo's `.git/worktrees/<name>` — not
mounted into the container, so every git command inside the container
failed with `fatal: not a git repository`. The fix now uses `git clone
--local` instead: every dispatch that doesn't pass an explicit --repo-dir
gets its own fully self-contained clone (independent `.git` directory, no
dependency on any path outside the mounted workspace), never the canonical
checkout path itself.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_POLECAT_DIR = str(_REPO_ROOT / "aops-jr" / "polecat")
if _POLECAT_DIR not in sys.path:
    sys.path.insert(0, _POLECAT_DIR)

from cli import cleanup_isolated_workspace, resolve_isolated_workspace  # noqa: E402


def _run(*args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, f"{args} failed: {result.stderr}"
    return result.stdout


@pytest.fixture
def fake_canonical_repo(tmp_path):
    """A throwaway git repo standing in for the shared canonical checkout."""
    repo = tmp_path / "canonical-checkout"
    repo.mkdir()
    _run("git", "init", cwd=repo)
    _run("git", "config", "user.email", "test@example.com", cwd=repo)
    _run("git", "config", "user.name", "Test", cwd=repo)
    (repo / "README.md").write_text("hello\n")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "initial", cwd=repo)
    return repo


def test_isolated_workspace_is_never_the_canonical_path(fake_canonical_repo, tmp_path):
    """The core invariant: the returned mount source must never equal the
    canonical checkout directory (or its repo root)."""
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-abc123", polecat_home
    )

    assert isolated_path != fake_canonical_repo.resolve()
    assert cleanup_info is not None
    assert cleanup_info["repo_root"] == fake_canonical_repo.resolve()

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_is_a_real_independent_clone(fake_canonical_repo, tmp_path):
    """The isolated path must be a working, independent git clone carrying
    the canonical repo's history — not just an arbitrary empty directory."""
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-xyz789", polecat_home
    )

    assert (isolated_path / "README.md").read_text() == "hello\n"
    assert (isolated_path / ".git").exists()

    # Branch-switching inside the isolated clone must never touch the
    # canonical checkout's HEAD — this is the exact race that caused the bug.
    canonical_head_before = _run(
        "git", "rev-parse", "HEAD", cwd=fake_canonical_repo
    ).strip()
    _run("git", "checkout", "-b", "task/some-worker-branch", cwd=isolated_path)
    canonical_head_after = _run(
        "git", "rev-parse", "HEAD", cwd=fake_canonical_repo
    ).strip()
    canonical_branch_after = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()

    assert canonical_head_before == canonical_head_after
    assert canonical_branch_after != "task/some-worker-branch"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_clone_is_fully_self_contained_without_parent_repo(fake_canonical_repo, tmp_path):
    """Regression test for aops_aef75b26: a linked `git worktree`'s `.git`
    is a FILE pointing at an absolute path inside the parent repo's `.git`
    directory (`<repo_root>/.git/worktrees/<name>`) — invisible to a
    container that only mounts the isolated workspace, so every git command
    inside the container failed with `fatal: not a git repository`. A real
    clone's `.git` is a self-contained directory that must keep working
    even when the parent repo (and thus any `.git/worktrees/<name>` admin
    path) is completely unreachable — exactly the container-mount
    constraint that broke the worktree-based approach.
    """
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-standalone", polecat_home
    )

    # The regression signature itself: .git must be a real directory, not
    # a worktree-style file pointing back at the parent.
    assert (isolated_path / ".git").is_dir()

    # Simulate the container constraint directly: the parent repo (and any
    # `.git/worktrees/<session>` admin path inside it) becomes completely
    # unreachable. Isolated git operations must still work.
    shutil.rmtree(fake_canonical_repo)

    status = _run("git", "status", cwd=isolated_path)
    assert "nothing to commit" in status or "working tree clean" in status
    _run("git", "checkout", "-b", "worker-branch-after-parent-gone", cwd=isolated_path)
    (isolated_path / "new-file.txt").write_text("committed after parent removed\n")
    _run("git", "add", "new-file.txt", cwd=isolated_path)
    _run("git", "commit", "-m", "isolated commit with no parent repo reachable", cwd=isolated_path)
    log_out = _run("git", "log", "--oneline", "-1", cwd=isolated_path)
    assert log_out.strip() != ""

    # cleanup_isolated_workspace must also not depend on the parent repo.
    cleanup_isolated_workspace(cleanup_info)
    assert not isolated_path.exists()


def test_concurrent_sessions_get_independent_clones(fake_canonical_repo, tmp_path):
    """Two concurrent dispatches (the actual failure mode reported: 6+
    containers sharing one checkout) must never collide on the same path or
    branch."""
    polecat_home = tmp_path / "polecat-home"
    path_a, cleanup_a = resolve_isolated_workspace(fake_canonical_repo, "session-a", polecat_home)
    path_b, cleanup_b = resolve_isolated_workspace(fake_canonical_repo, "session-b", polecat_home)

    assert path_a != path_b
    assert cleanup_a["branch"] != cleanup_b["branch"]

    _run("git", "checkout", "-b", "worker-a-branch", cwd=path_a)
    _run("git", "checkout", "-b", "worker-b-branch", cwd=path_b)

    branch_a = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_a).strip()
    branch_b = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_b).strip()
    assert branch_a == "worker-a-branch"
    assert branch_b == "worker-b-branch"

    cleanup_isolated_workspace(cleanup_a)
    cleanup_isolated_workspace(cleanup_b)


def test_cleanup_removes_clone_and_leaves_canonical_repo_untouched(fake_canonical_repo, tmp_path):
    polecat_home = tmp_path / "polecat-home"
    canonical_branch_before = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()

    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-cleanup", polecat_home
    )
    assert isolated_path.exists()

    cleanup_isolated_workspace(cleanup_info)

    assert not isolated_path.exists()
    # A clone's session branch lives only inside the clone's own separate
    # .git — the canonical repo never saw it and its own branch is
    # untouched (unlike the old worktree approach, which created the
    # throwaway branch inside the shared repo itself).
    canonical_branch_after = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()
    assert canonical_branch_after == canonical_branch_before
    branches = _run("git", "branch", "--list", cleanup_info["branch"], cwd=fake_canonical_repo)
    assert cleanup_info["branch"] not in branches


def test_non_git_directory_is_not_isolated_but_flagged(tmp_path):
    """A non-git workspace can't be isolated via clone — must fall back to
    mounting it directly rather than crashing, with cleanup_info=None."""
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()
    polecat_home = tmp_path / "polecat-home"

    isolated_path, cleanup_info = resolve_isolated_workspace(plain_dir, "session-plain", polecat_home)

    assert isolated_path == plain_dir.resolve()
    assert cleanup_info is None

    # Must be a no-op, not an error.
    cleanup_isolated_workspace(cleanup_info)
