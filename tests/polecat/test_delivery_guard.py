"""Regression tests for polecat's delivery guard.

Ensures a polecat run that ends with uncommitted changes or unpushed local
commits exits non-zero rather than reporting a success it cannot evidence.
The guard reports; it does not reach into a knowledge base to reopen the task.
"""

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from lib.polecat import cli
from lib.polecat.cli import _get_git_head, _verify_workspace_delivery, main

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _write_transcript(docker_argv, task_id):
    """Persist a claude transcript into the session dir `docker_argv` mounts,
    exactly as a container that received the seed would."""
    mount = next(
        value
        for flag, value in zip(docker_argv, docker_argv[1:], strict=False)
        if flag == "-v" and value.endswith(f":{cli.CLAUDE_SESSION_PATH}")
    )
    session_dir = Path(mount[: -len(cli.CLAUDE_SESSION_PATH) - 1])
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "5e2f9c11-0000-4000-8000-000000000001.jsonl").write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": f"/pull {task_id}"}})
        + "\n"
    )


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True
    )
    (path / "file.txt").write_text("initial\n")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=path, check=True, capture_output=True
    )


def test_verify_workspace_delivery_clean_repo(tmp_path):
    repo = tmp_path / "clean_repo"
    _init_repo(repo)
    head = _get_git_head(repo)

    ok, err = _verify_workspace_delivery(repo, initial_head=head)
    assert ok is True
    assert err is None


def test_verify_workspace_delivery_uncommitted_changes(tmp_path):
    repo = tmp_path / "dirty_repo"
    _init_repo(repo)
    head = _get_git_head(repo)

    (repo / "file.txt").write_text("modified content\n")

    ok, err = _verify_workspace_delivery(repo, initial_head=head)
    assert ok is False
    assert "uncommitted changes" in err.lower()


def test_verify_workspace_delivery_unpushed_commits(tmp_path):
    repo = tmp_path / "unpushed_repo"
    _init_repo(repo)
    initial_head = _get_git_head(repo)

    # Create local commit
    (repo / "file2.txt").write_text("new file\n")
    subprocess.run(["git", "add", "file2.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "second commit"], cwd=repo, check=True, capture_output=True
    )

    ok, err = _verify_workspace_delivery(repo, initial_head=initial_head)
    assert ok is False
    assert "local commits created" in err.lower() or "no pushed branch" in err.lower()


def test_verify_workspace_delivery_non_git_dir(tmp_path):
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()

    ok, err = _verify_workspace_delivery(plain_dir)
    assert ok is True
    assert err is None


def test_run_fails_loudly_on_uncommitted_changes(tmp_path, monkeypatch):
    """A container that exits 0 leaving work uncommitted is not a success.

    The guard's whole job is to refuse that verdict, and to name the task so
    whoever dispatched it knows which one to reopen.
    """
    _repo = tmp_path / "repo"
    _init_repo(_repo)

    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setattr("lib.polecat.cli._image_available_locally", lambda image: True)
    monkeypatch.setattr(
        "lib.polecat.cli.load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}
        },
    )
    monkeypatch.setattr("lib.polecat.cli.load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        "lib.polecat.cli.setup_staging",
        lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None,
    )

    real_run = subprocess.run

    def fake_subprocess_run(cmd, *a, **kw):
        if cmd[0] == "docker" and cmd[1] == "run":
            # The container did see the seeded task — it just left the work
            # uncommitted. Seed verification runs first and would otherwise be
            # the failure this test catches, which is a different guard.
            _write_transcript(cmd, "task-dirty")
            (_repo / "dirty.txt").write_text("dirty\n")
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr("lib.polecat.cli.subprocess.run", fake_subprocess_run)

    runner = CliRunner()
    result = runner.invoke(main, ["run", "claude", "-d", str(_repo), "-t", "task-dirty"])

    assert result.exit_code != 0
    assert "delivery guard failed" in result.output.lower()
    assert "task-dirty" in result.output
    assert "uncommitted changes" in result.output
