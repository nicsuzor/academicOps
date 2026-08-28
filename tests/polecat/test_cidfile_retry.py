"""Regression tests for the `--cidfile` collision inside the seed-verification retry.

Background (task aops_3f7c91d2, found while triaging aops_4b996906): the docker
argv is built exactly once by `_build_docker_argv`, which computes
`<session_dir>/container.cid` and clears any stale copy *before* the retry loop
exists. `_execute_with_seed_verification` then re-runs that identical argv up to
twice. Docker writes the cidfile at container creation and refuses to start when
the path is already present:

    docker: container ID file found, make sure the other container isn't
    running or delete /tmp/x.cid.   (exit 125)

So attempt 1 leaving a cidfile behind made attempt 2 abort before the container
was ever created — the retry could never succeed after a first-attempt
container failure, regardless of session name.

The cid is host-side bookkeeping only: it feeds `container_id` in run.json and
nothing else, so it must be drained per attempt without losing the id an
already-reaped (`--rm`) container recorded.
"""

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from lib.polecat import cli


def _base_mocks(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}
        },
    )
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setattr(cli, "_get_image_digest", lambda image: None)
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("AOPS", str(tmp_path / "repo"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")


def _init_git_repo(repo_dir):
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    (repo_dir / "initial.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True, capture_output=True
    )


def _cidfile_of(cmd):
    return Path(cmd[cmd.index("--cidfile") + 1])


# --------------------------------------------------------------------------
# _drain_cidfile
# --------------------------------------------------------------------------


def test_drain_cidfile_returns_id_and_removes_file(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "container.cid").write_text("deadbeefcafe\n")

    assert cli._drain_cidfile(session_dir) == "deadbeefcafe"
    assert not (session_dir / "container.cid").exists()


def test_drain_cidfile_is_a_noop_when_absent(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    assert cli._drain_cidfile(session_dir) is None
    assert not (session_dir / "container.cid").exists()


# --------------------------------------------------------------------------
# retry loop
# --------------------------------------------------------------------------


def test_retry_attempt_does_not_inherit_the_first_attempts_cidfile(tmp_path, monkeypatch):
    """The core regression: attempt 1 fails after docker wrote the cidfile.

    Attempt 2 reuses the identical prebuilt argv, so if the file is still there
    docker aborts at exit 125 before creating anything and the retry is dead on
    arrival. Every attempt must see a clean cidfile path.
    """
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run
    seen_stale = []

    def fake_run(cmd, *a, **kw):
        if cmd[:2] != ["docker", "run"]:
            return real_run(cmd, *a, **kw)
        cidfile = _cidfile_of(cmd)
        seen_stale.append(cidfile.exists())
        if cidfile.exists():
            # Faithful docker behaviour: refuse, create nothing, exit 125.
            return subprocess.CompletedProcess(cmd, 125)
        attempt = len(seen_stale)
        cidfile.write_text(f"container-id-attempt-{attempt}\n")
        # Attempt 1's container fails; attempt 2's succeeds.
        return subprocess.CompletedProcess(cmd, 0 if attempt == 2 else 1)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    runner = CliRunner()
    res = runner.invoke(
        cli.main, ["run", "claude", "-d", str(repo), "-s", "session-cid1", "-t", "aops_3f7c91d2"]
    )

    assert seen_stale == [False, False], (
        "docker must never be invoked against a pre-existing cidfile; "
        f"observed stale-file state per attempt: {seen_stale}"
    )
    assert res.exit_code == 0, res.output

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1
    assert json.loads(run_jsons[0].read_text())["container_id"] == "container-id-attempt-2"


def test_failed_attempts_container_id_survives_the_drain(tmp_path, monkeypatch):
    """Draining must not destroy the evidence it removes.

    Attempt 1 creates a container and fails; attempt 2 aborts before docker
    writes any cid at all. run.json must still name the container that actually
    existed rather than reporting none.
    """
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run
    attempts = {"n": 0}

    def fake_run(cmd, *a, **kw):
        if cmd[:2] != ["docker", "run"]:
            return real_run(cmd, *a, **kw)
        attempts["n"] += 1
        if attempts["n"] == 1:
            _cidfile_of(cmd).write_text("container-id-attempt-1\n")
            return subprocess.CompletedProcess(cmd, 1)
        # Second attempt dies before any container is created — no cid written.
        return subprocess.CompletedProcess(cmd, 125)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    runner = CliRunner()
    res = runner.invoke(
        cli.main, ["run", "claude", "-d", str(repo), "-s", "session-cid2", "-t", "aops_3f7c91d2"]
    )

    assert res.exit_code != 0, res.output
    assert attempts["n"] == 2

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1
    assert json.loads(run_jsons[0].read_text())["container_id"] == "container-id-attempt-1"
