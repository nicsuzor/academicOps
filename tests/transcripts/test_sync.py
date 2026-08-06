"""Unit tests for transcripts.domain.sync.git_sync_sessions.

Regression coverage:

- a stray nested-git directory (worker scratch leaking into the sessions repo
  under logs/) must not abort the whole sync -- everything else should still get
  staged, committed, and pushed;
- a remote that has moved on since this host last synced must be merged before
  the push, not left to be rejected non-fast-forward (which silently dropped
  every transcript from every subsequent cron cycle).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from transcripts.domain.sync import git_sync_sessions

_TEST_IDENTITY = [
    "-c",
    "user.name=test",
    "-c",
    "user.email=test@example.com",
]


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _out(args: list[str], cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _init_repo_with_remote(
    tmp_path: Path, *, set_identity: bool = True, set_upstream: bool = True
) -> tuple[Path, Path]:
    """Create a bare 'remote' repo and a clone of it to act as the sessions dir.

    set_identity=False leaves the repo with no user.name/user.email, matching a
    cron environment -- the seed commit then supplies its identity per-command.
    set_upstream=False leaves no branch tracking config, so a sync that relies
    on implicit upstream resolution rather than an explicit refspec will fail.
    """
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _run(["git", "init", "--bare", "-q", "-b", "main"], cwd=remote)

    sessions_dir = tmp_path / "sessions_repo"
    sessions_dir.mkdir()
    _run(["git", "init", "-q", "-b", "main"], cwd=sessions_dir)
    if set_identity:
        _run(["git", "config", "user.email", "test@example.com"], cwd=sessions_dir)
        _run(["git", "config", "user.name", "test"], cwd=sessions_dir)
    (sessions_dir / "README.md").write_text("seed\n")
    _run(["git", "add", "."], cwd=sessions_dir)
    _run([*(["git", *_TEST_IDENTITY]), "commit", "-q", "-m", "seed"], cwd=sessions_dir)
    _run(["git", "remote", "add", "origin", str(remote)], cwd=sessions_dir)
    push = ["git", "push", "-q"]
    if set_upstream:
        push.append("-u")
    _run([*push, "origin", "main"], cwd=sessions_dir)
    return sessions_dir, remote


def _land_commit_on_remote(
    tmp_path: Path, remote: Path, *, filename: str, content: str, slug: str
) -> str:
    """Land a commit on the bare remote's main from a second clone."""
    clone = tmp_path / f"clone_{slug}"
    _run(["git", "clone", "-q", str(remote), str(clone)], cwd=tmp_path)
    (clone / filename).write_text(content)
    _run(["git", "add", "."], cwd=clone)
    _run([*(["git", *_TEST_IDENTITY]), "commit", "-q", "-m", f"other host: {slug}"], cwd=clone)
    _run(["git", "push", "-q", "origin", "main"], cwd=clone)
    return _out(["git", "rev-parse", "HEAD"], cwd=clone)


def _remote_main_tree(remote: Path) -> list[str]:
    return _out(["git", "ls-tree", "-r", "--name-only", "main"], cwd=remote).splitlines()


def _isolate_git_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Strip every ambient git identity, the way cron sees the world.

    Without this the developer's own ~/.gitconfig supplies user.name/user.email
    and a missing commit identity on the merge commit passes locally while
    failing in the environment this code actually runs in.
    """
    home = tmp_path / "fake_home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_git_sync_skips_nested_git_dir_but_commits_everything_else(tmp_path: Path) -> None:
    sessions_dir, remote = _init_repo_with_remote(tmp_path)

    # Legitimate new content, e.g. a batch of transcript files.
    (sessions_dir / "transcripts").mkdir()
    (sessions_dir / "transcripts" / "20260722-01-adhoc-aaaa.md").write_text("hi\n")

    # Simulate the confirmed defect: a polecat/agy worker's own scratch
    # checkout leaking into logs/, complete with a nested no-commit .git dir.
    stray = (
        sessions_dir
        / "logs"
        / "20260721"
        / "p3-transcripts"
        / "workspace"
        / "agy-brain"
        / "c3b09d92"
        / "scratch"
        / "sessions"
    )
    stray.mkdir(parents=True)
    _run(["git", "init", "-q"], cwd=stray)  # bare-ish: no commits checked out
    (stray / "pr_body.md").write_text("scratch\n")

    ok = git_sync_sessions(sessions_dir)

    assert ok is True, "sync should succeed despite the stray nested-git dir"

    # The legitimate transcript file must have been committed and pushed.
    log = subprocess.run(
        ["git", "log", "--name-only", "--format=", "-1"],
        cwd=sessions_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "transcripts/20260722-01-adhoc-aaaa.md" in log

    remote_log = subprocess.run(
        ["git", "log", "main", "--format=%H"],
        cwd=remote,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    local_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=sessions_dir, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert local_head in remote_log.splitlines(), "local HEAD must have been pushed to origin"


def test_git_sync_returns_false_when_nothing_stageable(tmp_path: Path) -> None:
    sessions_dir, _remote = _init_repo_with_remote(tmp_path)

    # Only a stray nested-git dir changed -- nothing real to commit.
    stray = sessions_dir / "logs" / "scratch" / "sessions"
    stray.mkdir(parents=True)
    _run(["git", "init", "-q"], cwd=stray)
    (stray / "f.txt").write_text("x\n")

    ok = git_sync_sessions(sessions_dir)

    assert ok is False


def test_git_sync_no_changes_returns_true(tmp_path: Path) -> None:
    sessions_dir, _remote = _init_repo_with_remote(tmp_path)
    ok = git_sync_sessions(sessions_dir)
    assert ok is True


def test_git_sync_merges_diverged_remote_instead_of_being_rejected(tmp_path: Path) -> None:
    """The defect: another host landed a commit, so our push is non-fast-forward.

    Before the fix this returned False with '! [rejected] ... (fetch first)' and
    the transcripts never left the machine.
    """
    sessions_dir, remote = _init_repo_with_remote(tmp_path, set_upstream=False)
    _land_commit_on_remote(tmp_path, remote, filename="from_other_host.md", content="b\n", slug="b")

    (sessions_dir / "transcripts").mkdir()
    (sessions_dir / "transcripts" / "20260806-01-adhoc-aaaa.md").write_text("hi\n")

    assert git_sync_sessions(sessions_dir) is True

    remote_head = _out(["git", "rev-parse", "main"], cwd=remote)
    local_head = _out(["git", "rev-parse", "HEAD"], cwd=sessions_dir)
    assert remote_head == local_head, "the merged local HEAD must be what origin/main points at"

    tree = _remote_main_tree(remote)
    assert "transcripts/20260806-01-adhoc-aaaa.md" in tree, "our transcript must reach the remote"
    assert "from_other_host.md" in tree, "the other host's commit must be preserved, not clobbered"


def test_git_sync_merge_commit_gets_bot_identity_with_no_git_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The merge commit `git pull` writes needs a committer, and cron has none."""
    _isolate_git_config(monkeypatch, tmp_path)
    sessions_dir, remote = _init_repo_with_remote(tmp_path, set_identity=False, set_upstream=False)
    _land_commit_on_remote(tmp_path, remote, filename="from_other_host.md", content="b\n", slug="b")

    (sessions_dir / "new_transcript.md").write_text("hi\n")

    assert git_sync_sessions(sessions_dir) is True

    head_parents = _out(["git", "rev-list", "--parents", "-n", "1", "HEAD"], cwd=sessions_dir)
    assert len(head_parents.split()) == 3, "HEAD should be a merge commit with two parents"
    committer = _out(["git", "log", "-1", "--format=%cn <%ce>"], cwd=sessions_dir)
    assert committer == "aops-bot <aops-bot@users.noreply.github.com>"


def test_git_sync_conflict_returns_false_without_wedging_the_repo(tmp_path: Path) -> None:
    """A real conflict still fails the cycle -- but must not trap the next one."""
    sessions_dir, remote = _init_repo_with_remote(tmp_path, set_upstream=False)
    _land_commit_on_remote(tmp_path, remote, filename="README.md", content="theirs\n", slug="b")

    (sessions_dir / "README.md").write_text("ours\n")

    assert git_sync_sessions(sessions_dir) is False

    git_dir = Path(_out(["git", "rev-parse", "--absolute-git-dir"], cwd=sessions_dir))
    assert not (git_dir / "MERGE_HEAD").exists(), "repo left mid-merge; next cycle is trapped"
    status = _out(["git", "status", "--porcelain"], cwd=sessions_dir)
    assert "UU" not in status, f"unmerged paths left behind: {status!r}"
    # Our local work was still committed, so nothing is lost pending resolution.
    assert "ours" in _out(["git", "show", "HEAD:README.md"], cwd=sessions_dir)


def test_git_sync_recovers_from_interrupted_merge(tmp_path: Path) -> None:
    """A sync killed mid-merge leaves MERGE_HEAD; the next cycle must self-heal."""
    sessions_dir, remote = _init_repo_with_remote(tmp_path, set_upstream=False)
    remote_head = _land_commit_on_remote(
        tmp_path, remote, filename="from_other_host.md", content="b\n", slug="b"
    )

    git_dir = Path(_out(["git", "rev-parse", "--absolute-git-dir"], cwd=sessions_dir))
    _run(["git", "fetch", "-q", "origin", "main"], cwd=sessions_dir)
    (git_dir / "MERGE_HEAD").write_text(f"{remote_head}\n")

    (sessions_dir / "new_transcript.md").write_text("hi\n")

    assert git_sync_sessions(sessions_dir) is True
    assert not (git_dir / "MERGE_HEAD").exists()

    tree = _remote_main_tree(remote)
    assert "new_transcript.md" in tree
    assert "from_other_host.md" in tree
