"""Unit tests for polecat run record (run.json) persistence and schema compliance.

Covers acceptance criteria M1/M2 for task aops_9b03ee22:
- Persistence of run.json on success, non-zero exit, and delivery guard failure.
- Complete schema validation.
- Capture of container_id, commit_start/commit_end, image_digest, exit_code,
  delivery_guard, seeded_prompt, transcript, worker_model, and degraded ledger.

What the `transcript` key must record is asserted in
`test_transcript_persistence.py`; here it is only part of the schema.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from lib.polecat import cli

REQUIRED_SCHEMA_KEYS = {
    "schema_version",
    "session_id",
    "container_id",
    "container_name",
    "agent",
    "task_id",
    "seeded_prompt",
    "image_ref",
    "image_digest",
    "workspace_dir",
    "session_dir",
    "commit_start",
    "commit_end",
    "exit_code",
    "status",
    "delivery_guard",
    "transcript",
    "started_at",
    "ended_at",
    "duration_seconds",
    "worker_model",
    "degraded",
    "plugin_provenance",
}


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
    monkeypatch.setattr(
        cli,
        "_get_image_digest",
        lambda image: "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")


def _init_git_repo(repo_dir):
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    (repo_dir / "initial.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True, capture_output=True
    )


def test_write_run_record_schema_and_keys(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    t_file = session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl"
    t_file.write_text('{"type": "user", "message": "hello"}\n')
    start_time = datetime.now(UTC)
    end_time = datetime.now(UTC)

    out_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-12345",
        container_id="c1234567890a",
        container_name="polecat-session-12345",
        agent="claude",
        task_id="aops_9b03ee22",
        seeded_prompt="/pull aops_9b03ee22",
        image_ref="test-image:latest",
        image_digest="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        workspace_dir=tmp_path / "workspace",
        commit_start="abc1234",
        commit_end="def5678",
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=start_time,
        ended_at=end_time,
        worker_model=None,
        degraded=[],
    )

    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert set(data.keys()) == REQUIRED_SCHEMA_KEYS
    assert data["schema_version"] == 1
    assert data["session_id"] == "session-12345"
    assert data["container_id"] == "c1234567890a"
    assert data["status"] == "success"
    assert data["worker_model"] is None
    assert data["transcript"]["found"] is True
    assert data["transcript"]["transcript_path"] == str(t_file)
    assert data["transcript"]["transcript_bytes"] == t_file.stat().st_size
    assert data["transcript"]["event_count"] == 1
    assert any(d.get("what") == "worker_model" for d in data["degraded"])


def test_run_command_creates_run_json_on_clean_run(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("fake-container-id-12345\n")
            session_dir = cidfile_path.parent
            (session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl").write_text(
                '{"type": "user", "message": "hello"}\n'
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    runner = CliRunner()
    res = runner.invoke(
        cli.main, ["run", "claude", "-d", str(repo), "-s", "session-test1", "-t", "aops_9b03ee22"]
    )
    assert res.exit_code == 0, res.output

    session_logs = tmp_path / "sessions"
    run_jsons = list(session_logs.glob("**/run.json"))
    assert len(run_jsons) == 1

    data = json.loads(run_jsons[0].read_text())
    assert set(data.keys()) == REQUIRED_SCHEMA_KEYS
    assert data["session_id"] == "session-test1"
    assert data["container_id"] == "fake-container-id-12345"
    assert data["container_name"] == "polecat-session-test1"
    assert data["agent"] == "claude"
    assert data["task_id"] == "aops_9b03ee22"
    assert data["seeded_prompt"] == "/pull aops_9b03ee22"
    assert data["exit_code"] == 0
    assert data["status"] == "success"
    assert data["delivery_guard"] == {"ok": True, "error": None}


def test_run_command_creates_run_json_on_nonzero_exit(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("fake-container-id-nonzero\n")
            return subprocess.CompletedProcess(cmd, 3)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-fail3"])
    assert res.exit_code == 3

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1

    data = json.loads(run_jsons[0].read_text())
    assert set(data.keys()) == REQUIRED_SCHEMA_KEYS
    assert data["exit_code"] == 3
    assert data["status"] == "failed"
    assert data["container_id"] == "fake-container-id-nonzero"
    assert data["delivery_guard"]["ok"] is False


def test_run_command_creates_run_json_on_delivery_guard_failure(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            cidfile_idx = cmd.index("--cidfile") + 1
            cidfile_path = Path(cmd[cidfile_idx])
            cidfile_path.write_text("fake-container-id-dirty\n")
            # Simulate agent leaving an uncommitted file in repo
            (repo / "uncommitted.txt").write_text("dirty\n")
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-dirty"])
    assert res.exit_code != 0
    assert "delivery guard failed" in res.output.lower()

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1

    data = json.loads(run_jsons[0].read_text())
    assert set(data.keys()) == REQUIRED_SCHEMA_KEYS
    assert data["exit_code"] == 0
    assert data["status"] == "delivery_guard_failed"
    assert data["delivery_guard"]["ok"] is False
    assert "uncommitted" in data["delivery_guard"]["error"]


def test_commit_start_and_commit_end_differ_when_committed(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli, "_verify_workspace_delivery", lambda workspace_dir, initial_head=None: (True, None)
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            # Simulate a commit during run
            (repo / "new_file.txt").write_text("new content\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "agent commit"], cwd=repo, check=True, capture_output=True
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-commit"])
    assert res.exit_code == 0

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(run_jsons) == 1

    data = json.loads(run_jsons[0].read_text())
    assert data["commit_start"] is not None
    assert data["commit_end"] is not None
    assert data["commit_start"] != data["commit_end"]


def test_worker_model_env_var_populated(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setenv("POLECAT_WORKER_MODEL", "claude-3-5-sonnet")
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["run", "claude", "-d", str(repo), "-s", "session-model"])
    assert res.exit_code == 0

    run_jsons = list((tmp_path / "sessions").glob("**/run.json"))
    data = json.loads(run_jsons[0].read_text())
    assert data["worker_model"] == "claude-3-5-sonnet"
    assert not any(d.get("what") == "worker_model" for d in data["degraded"])


def test_write_run_record_degraded_status_when_transcript_missing(tmp_path):
    session_dir = tmp_path / "session_missing"
    session_dir.mkdir(parents=True)
    out_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-missing-1",
        container_id="c12345",
        container_name="polecat-session-missing-1",
        agent="claude",
        task_id=None,
        seeded_prompt=None,
        image_ref="test-image:latest",
        image_digest="sha256:12345",
        workspace_dir=tmp_path / "workspace",
        commit_start=None,
        commit_end=None,
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    data = json.loads(out_file.read_text())
    assert data["status"] == "degraded"
    assert data["transcript"]["found"] is False
    assert data["transcript"]["transcript_path"] is None
    assert data["transcript"]["transcript_bytes"] is None
    assert data["transcript"]["event_count"] == 0
    assert any(d.get("what") == "transcript_missing" for d in data["degraded"])


def test_write_run_record_degraded_status_when_transcript_zero_bytes(tmp_path):
    session_dir = tmp_path / "session_zero"
    session_dir.mkdir(parents=True)
    t_file = session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl"
    t_file.write_text("")
    out_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-zero-1",
        container_id="c12345",
        container_name="polecat-session-zero-1",
        agent="agy",
        task_id=None,
        seeded_prompt=None,
        image_ref="test-image:latest",
        image_digest="sha256:12345",
        workspace_dir=tmp_path / "workspace",
        commit_start=None,
        commit_end=None,
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    data = json.loads(out_file.read_text())
    assert data["status"] == "degraded"
    assert data["transcript"]["found"] is False
    assert data["transcript"]["transcript_path"] is None
    assert data["transcript"]["transcript_bytes"] is None
    assert data["transcript"]["event_count"] == 0
    assert any(d.get("what") == "transcript_missing" for d in data["degraded"])


def test_write_run_record_non_agent_no_degradation(tmp_path):
    session_dir = tmp_path / "session_shell"
    session_dir.mkdir(parents=True)
    out_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-shell-1",
        container_id="c12345",
        container_name="polecat-session-shell-1",
        agent="shell",
        task_id=None,
        seeded_prompt=None,
        image_ref="test-image:latest",
        image_digest="sha256:12345",
        workspace_dir=tmp_path / "workspace",
        commit_start=None,
        commit_end=None,
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    data = json.loads(out_file.read_text())
    assert data["status"] == "success"
    assert not any(d.get("what") in ("transcript", "transcript_missing") for d in data["degraded"])


def test_transcript_metadata_structure(tmp_path):
    session_dir = tmp_path / "session_meta"
    session_dir.mkdir(parents=True)
    t_file = session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl"
    t_file.write_text('{"line": 1}\n{"line": 2}\n{"line": 3}\n')
    out_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-meta-1",
        container_id="c12345",
        container_name="polecat-session-meta-1",
        agent="claude",
        task_id=None,
        seeded_prompt=None,
        image_ref="test-image:latest",
        image_digest="sha256:12345",
        workspace_dir=tmp_path / "workspace",
        commit_start=None,
        commit_end=None,
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    data = json.loads(out_file.read_text())
    t = data["transcript"]
    assert t["found"] is True
    assert t["path"] == str(t_file)
    assert t["bytes"] == t_file.stat().st_size
    assert t["count"] == 1
    assert t["transcript_path"] == str(t_file)
    assert t["transcript_bytes"] == t_file.stat().st_size
    assert t["event_count"] == 3
