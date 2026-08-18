"""Regression tests for polecat/cli.py workspace isolation.

polecat used to bind-mount the shared canonical checkout (e.g.
/home/nic/src/academicOps) READ-WRITE straight into every worker container
as /workspace, with no per-task isolation. Concurrent containers each ran
their own `git checkout <task-branch>` inside that ONE shared tree, racing
every other container and every live interactive session reading the same
directory (confirmed via `git reflog` showing interleaved checkout/reset
across 3+ branches in quick succession). The first fix (`resolve_isolated_workspace` /
`cleanup_isolated_workspace` in cli.py) gave every dispatch that doesn't pass
an explicit --repo-dir its own throwaway `git worktree`, never the canonical
checkout path itself.

That first fix used `git worktree add`, which creates a *linked* worktree
whose `.git` is a plain-text file pointing at an admin dir living inside the
canonical repo's own `.git/worktrees/<name>` — a host-only path never
mounted into the container, so every git operation inside the container
failed with `fatal: not a git repository: <host-path>`. The
mechanism was changed to a fully standalone `git clone --local` instead: the
isolated workspace now has its own complete `.git` directory, not a pointer
file, so git is fully self-contained inside the container. One consequence
worth noting in these tests: since the clone is standalone, cleanup no
longer needs (or performs) any `git worktree remove` / `branch -D` against
the canonical repo — the worker's branch only ever exists inside the
isolated clone, never leaks into the canonical repo's branch list at all.
"""

import subprocess
from pathlib import Path

import pytest

from lib.polecat.cli import cleanup_isolated_workspace, resolve_isolated_workspace

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
    assert cleanup_info["path"].resolve() == isolated_path

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_is_a_real_independent_worktree(fake_canonical_repo, tmp_path):
    """The isolated path must be a working, independent git clone sharing
    the canonical repo's history — not just an arbitrary empty directory."""
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-xyz789", polecat_home
    )

    assert (isolated_path / "README.md").read_text() == "hello\n"
    assert (isolated_path / ".git").exists()
    # `.git` must be a real directory (self-contained), never a
    # linked-worktree pointer *file* referencing a host-only admin path
    # that a container could never resolve.
    assert (isolated_path / ".git").is_dir()

    # Branch-switching inside the isolated worktree must never touch the
    # canonical checkout's HEAD — this is the exact race that caused the bug.
    canonical_head_before = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    _run("git", "checkout", "-b", "task/some-worker-branch", cwd=isolated_path)
    canonical_head_after = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    canonical_branch_after = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()

    assert canonical_head_before == canonical_head_after
    assert canonical_branch_after != "task/some-worker-branch"

    cleanup_isolated_workspace(cleanup_info)


def test_concurrent_sessions_get_independent_worktrees(fake_canonical_repo, tmp_path):
    """Two concurrent dispatches (the actual failure mode reported: 6+
    containers sharing one checkout) must never collide on the same path or
    branch."""
    polecat_home = tmp_path / "polecat-home"
    path_a, cleanup_a = resolve_isolated_workspace(fake_canonical_repo, "session-a", polecat_home)
    path_b, cleanup_b = resolve_isolated_workspace(fake_canonical_repo, "session-b", polecat_home)

    assert path_a != path_b
    initial_branch_a = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_a).strip()
    initial_branch_b = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_b).strip()
    assert initial_branch_a != initial_branch_b

    _run("git", "checkout", "-b", "worker-a-branch", cwd=path_a)
    _run("git", "checkout", "-b", "worker-b-branch", cwd=path_b)

    branch_a = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_a).strip()
    branch_b = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path_b).strip()
    assert branch_a == "worker-a-branch"
    assert branch_b == "worker-b-branch"

    cleanup_isolated_workspace(cleanup_a)
    cleanup_isolated_workspace(cleanup_b)


def test_cleanup_removes_worktree_and_branch(fake_canonical_repo, tmp_path):
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-cleanup", polecat_home
    )
    assert isolated_path.exists()

    # The worker branch must exist inside the isolated clone before
    # cleanup...
    branch_name = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=isolated_path).strip()
    isolated_branches = _run("git", "branch", "--list", branch_name, cwd=isolated_path)
    assert branch_name in isolated_branches

    cleanup_isolated_workspace(cleanup_info)

    assert not isolated_path.exists()
    # ...and must never have leaked into the canonical repo's own branch
    # list at any point — the standalone-clone mechanism means there is
    # nothing in the canonical repo for cleanup to remove.
    branches = _run("git", "branch", "--list", branch_name, cwd=fake_canonical_repo)
    assert branch_name not in branches


def test_isolated_workspace_gitdir_is_self_contained(fake_canonical_repo, tmp_path):
    """The container only ever gets the isolated path mounted, never the
    canonical checkout or its .git admin dir. Prove that `git`'s own gitdir
    resolution from inside the isolated clone never points outside the
    isolated tree — the exact defect this fix addresses: the
    prior linked-worktree mechanism resolved `.git` to a host-only path
    under the CANONICAL repo's `.git/worktrees/<name>`, which a container
    with only the isolated path mounted could never reach."""
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-selfcontained", polecat_home
    )

    git_dir = _run(
        "git", "-C", str(isolated_path), "rev-parse", "--absolute-git-dir", cwd=isolated_path
    ).strip()
    resolved_git_dir = Path(git_dir).resolve()

    # The resolved gitdir must live inside the isolated clone itself, not
    # inside the canonical repo (fake_canonical_repo) or any other host-only
    # location a container mount wouldn't include.
    assert resolved_git_dir.is_relative_to(isolated_path.resolve())
    assert not resolved_git_dir.is_relative_to(fake_canonical_repo.resolve())

    # Basic git operations (status/log) must work standalone — the best
    # available proxy, without docker, for "this is git-functional inside a
    # container that only has this directory mounted".
    status = _run("git", "-C", str(isolated_path), "status", "--porcelain", cwd=isolated_path)
    assert status == ""
    log = _run("git", "-C", str(isolated_path), "log", "--oneline", cwd=isolated_path)
    assert "initial" in log

    cleanup_isolated_workspace(cleanup_info)


def test_non_git_directory_is_not_isolated_but_flagged(tmp_path):
    """A non-git workspace can't be isolated via worktree — must fall back
    to mounting it directly rather than crashing, with cleanup_info=None."""
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()
    polecat_home = tmp_path / "polecat-home"

    isolated_path, cleanup_info = resolve_isolated_workspace(
        plain_dir, "session-plain", polecat_home
    )

    assert isolated_path == plain_dir.resolve()
    assert cleanup_info is None

    # Must be a no-op, not an error.
    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_respects_base_option(fake_canonical_repo, tmp_path):
    """The isolated workspace must create its private branch from the commit specified by base."""
    initial_branch = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()
    # Create a feature branch with a second commit
    _run("git", "checkout", "-b", "feature-branch", cwd=fake_canonical_repo)
    (fake_canonical_repo / "feature.txt").write_text("feature content\n")
    _run("git", "add", "feature.txt", cwd=fake_canonical_repo)
    _run("git", "commit", "-m", "feature commit", cwd=fake_canonical_repo)
    feature_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    _run("git", "checkout", initial_branch, cwd=fake_canonical_repo)

    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-base-opt", polecat_home, base="feature-branch"
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    assert isolated_sha == feature_sha
    assert (isolated_path / "feature.txt").read_text() == "feature content\n"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_defaults_to_config_branch(fake_canonical_repo, tmp_path):
    """When base is None, isolated workspace must default to the branch specified in polecat.yaml config."""
    initial_branch = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()
    _run("git", "checkout", "-b", "dev", cwd=fake_canonical_repo)
    (fake_canonical_repo / "dev.txt").write_text("dev content\n")
    _run("git", "add", "dev.txt", cwd=fake_canonical_repo)
    _run("git", "commit", "-m", "dev commit", cwd=fake_canonical_repo)
    dev_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    _run("git", "checkout", initial_branch, cwd=fake_canonical_repo)

    polecat_home = tmp_path / "polecat-home"
    config = {"branch": "dev"}
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-base-cfg", polecat_home, base=None, config=config
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    assert isolated_sha == dev_sha
    assert (isolated_path / "dev.txt").read_text() == "dev content\n"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_defaults_to_head_when_unconfigured(fake_canonical_repo, tmp_path):
    """When base and config['branch'] are unset, isolated workspace defaults to HEAD."""
    head_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-base-head", polecat_home, base=None, config={}
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    assert isolated_sha == head_sha
    branch_name = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=isolated_path).strip()
    assert branch_name == "polecat/session-base-head"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_respects_custom_branch_option(fake_canonical_repo, tmp_path):
    """When branch is passed explicitly, the isolated clone checks out that custom branch name."""
    initial_branch = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()
    _run("git", "checkout", "-b", "feat/custom-override", cwd=fake_canonical_repo)
    _run("git", "checkout", initial_branch, cwd=fake_canonical_repo)

    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-custom-branch", polecat_home, branch="feat/custom-override"
    )

    branch_name = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=isolated_path).strip()
    assert branch_name == "feat/custom-override"

    cleanup_isolated_workspace(cleanup_info)


def test_clone_passes_no_checkout(fake_canonical_repo, tmp_path, monkeypatch):
    """Verify that git clone is invoked with --no-checkout for speedup."""
    real_run = subprocess.run
    clone_commands = []

    def tracking_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and len(cmd) > 1 and cmd[0] == "git" and cmd[1] == "clone":
            clone_commands.append(cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", tracking_run)
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo, "session-no-checkout", polecat_home
    )

    assert len(clone_commands) == 1
    assert "--no-checkout" in clone_commands[0]
    assert "--local" in clone_commands[0]

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_branch_sets_base_ref(fake_canonical_repo, tmp_path):
    """When branch is passed and base is not, base_ref resolves to that branch instead of config or HEAD."""
    initial_branch = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()
    _run("git", "checkout", "-b", "feat/my-feature", cwd=fake_canonical_repo)
    (fake_canonical_repo / "feature.txt").write_text("feature content\n")
    _run("git", "add", "feature.txt", cwd=fake_canonical_repo)
    _run("git", "commit", "-m", "feature commit", cwd=fake_canonical_repo)
    feature_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()
    _run("git", "checkout", initial_branch, cwd=fake_canonical_repo)

    polecat_home = tmp_path / "polecat-home"
    # Even if config specifies another branch like main, branch option takes precedence for base ref
    config = {"branch": initial_branch}
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo,
        "session-branch-base",
        polecat_home,
        base=None,
        config=config,
        branch="feat/my-feature",
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    branch_name = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=isolated_path).strip()
    assert isolated_sha == feature_sha
    assert branch_name == "feat/my-feature"
    assert (isolated_path / "feature.txt").read_text() == "feature content\n"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_base_precedes_branch(fake_canonical_repo, tmp_path):
    """When both base and branch are passed, base sets the commit SHA while branch sets the branch name."""
    initial_branch = _run(
        "git", "rev-parse", "--abbrev-ref", "HEAD", cwd=fake_canonical_repo
    ).strip()

    _run("git", "checkout", "-b", "base-branch", cwd=fake_canonical_repo)
    (fake_canonical_repo / "base.txt").write_text("base content\n")
    _run("git", "add", "base.txt", cwd=fake_canonical_repo)
    _run("git", "commit", "-m", "base commit", cwd=fake_canonical_repo)
    base_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()

    _run("git", "checkout", "-b", "target-branch", cwd=fake_canonical_repo)
    (fake_canonical_repo / "target.txt").write_text("target content\n")
    _run("git", "add", "target.txt", cwd=fake_canonical_repo)
    _run("git", "commit", "-m", "target commit", cwd=fake_canonical_repo)
    target_sha = _run("git", "rev-parse", "HEAD", cwd=fake_canonical_repo).strip()

    _run("git", "checkout", initial_branch, cwd=fake_canonical_repo)

    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        fake_canonical_repo,
        "session-base-precedence",
        polecat_home,
        base="base-branch",
        branch="custom-feature-branch",
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    branch_name = _run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=isolated_path).strip()

    assert isolated_sha == base_sha
    assert isolated_sha != target_sha
    assert branch_name == "custom-feature-branch"
    assert (isolated_path / "base.txt").read_text() == "base content\n"
    assert not (isolated_path / "target.txt").exists()

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_resolves_origin_remote_fallback(tmp_path):
    """When a ref is not found locally, resolve_isolated_workspace falls back to origin/<ref>."""
    # Create upstream repository
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _run("git", "init", "--bare", cwd=upstream)

    # Create canonical checkout and push to upstream
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    _run("git", "init", cwd=canonical)
    _run("git", "config", "user.email", "test@example.com", cwd=canonical)
    _run("git", "config", "user.name", "Test", cwd=canonical)
    (canonical / "README.md").write_text("main\n")
    _run("git", "add", "README.md", cwd=canonical)
    _run("git", "commit", "-m", "initial", cwd=canonical)
    _run("git", "remote", "add", "origin", str(upstream), cwd=canonical)
    _run("git", "push", "-u", "origin", "HEAD:main", cwd=canonical)

    # Another dev pushes a remote branch to upstream
    other_dev = tmp_path / "other-dev"
    other_dev.mkdir()
    _run("git", "clone", str(upstream), str(other_dev), cwd=tmp_path)
    _run("git", "config", "user.email", "test@example.com", cwd=other_dev)
    _run("git", "config", "user.name", "Test", cwd=other_dev)
    _run("git", "checkout", "-b", "remote-feature", cwd=other_dev)
    (other_dev / "remote.txt").write_text("remote feature content\n")
    _run("git", "add", "remote.txt", cwd=other_dev)
    _run("git", "commit", "-m", "remote commit", cwd=other_dev)
    remote_sha = _run("git", "rev-parse", "HEAD", cwd=other_dev).strip()
    _run("git", "push", "origin", "remote-feature", cwd=other_dev)

    # Canonical checkout fetches so origin/remote-feature exists, but no local remote-feature branch
    _run("git", "fetch", "origin", cwd=canonical)
    local_branches = _run("git", "branch", "--list", "remote-feature", cwd=canonical).strip()
    assert local_branches == ""

    # Resolving with base="remote-feature" should fall back to origin/remote-feature
    polecat_home = tmp_path / "polecat-home"
    isolated_path, cleanup_info = resolve_isolated_workspace(
        canonical, "session-origin-fallback", polecat_home, base="remote-feature"
    )

    isolated_sha = _run("git", "rev-parse", "HEAD", cwd=isolated_path).strip()
    assert isolated_sha == remote_sha
    assert (isolated_path / "remote.txt").read_text() == "remote feature content\n"

    cleanup_isolated_workspace(cleanup_info)


def test_isolated_workspace_fails_on_unresolvable_ref(fake_canonical_repo, tmp_path):
    """When base ref cannot be resolved locally or on origin, resolve_isolated_workspace fails with SystemExit."""
    polecat_home = tmp_path / "polecat-home"
    with pytest.raises(SystemExit):
        resolve_isolated_workspace(
            fake_canonical_repo,
            "session-bad-ref",
            polecat_home,
            base="nonexistent-branch-xyz",
        )
