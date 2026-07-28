"""Unit tests for transcripts.domain.sync.git_sync_sessions.

Regression coverage: a stray nested-git directory (worker
scratch leaking into the sessions repo under logs/) must not abort the whole
sync -- everything else should still get staged, committed, and pushed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from transcripts.domain.sync import git_sync_sessions


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a bare 'remote' repo and a clone of it to act as the sessions dir."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _run(["git", "init", "--bare", "-q"], cwd=remote)

    sessions_dir = tmp_path / "sessions_repo"
    sessions_dir.mkdir()
    _run(["git", "init", "-q", "-b", "main"], cwd=sessions_dir)
    _run(["git", "config", "user.email", "test@example.com"], cwd=sessions_dir)
    _run(["git", "config", "user.name", "test"], cwd=sessions_dir)
    (sessions_dir / "README.md").write_text("seed\n")
    _run(["git", "add", "."], cwd=sessions_dir)
    _run(["git", "commit", "-q", "-m", "seed"], cwd=sessions_dir)
    _run(["git", "remote", "add", "origin", str(remote)], cwd=sessions_dir)
    _run(["git", "push", "-q", "-u", "origin", "main"], cwd=sessions_dir)
    return sessions_dir, remote


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
