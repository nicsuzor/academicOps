"""A run must leave evidence of the conversation it ran, and say so in run.json.

`tests/polecat/test_transcript_persistence_e2e.py` used to guarantee this and
was deleted with the old repository layout (commit 4620f529b). What it asserted
— that a real transcript, not a stub, lands on the host, and that the run record
points at it — is restored here against the current layout:

    $AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/<project-or-"workspace">/

The old "summary stub" with its `real_transcript_path` field no longer exists;
`run.json`'s `transcript` block is its replacement, and it is written for every
run rather than only for seeded ones.

The deterministic tests below run everywhere. The live-container test at the end
is `e2e`-marked and skips unless the real image and credentials are present —
it is what proves the host-side path is still the one the container writes to.
"""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.polecat import cli

# A claude transcript, as claude itself names and shapes it: a session-uuid
# `.jsonl` of one JSON object per line.
_CLAUDE_UUID = "6912ac2b-781f-4515-94d5-d883e2b94a54"


def _write_claude_transcript(session_dir: Path, task_id: str | None = None, uuid_name=_CLAUDE_UUID):
    session_dir.mkdir(parents=True, exist_ok=True)
    prompt = f"/pull {task_id}" if task_id else "hello"
    lines = [
        json.dumps({"type": "mode", "mode": "normal", "sessionId": uuid_name}),
        json.dumps(
            {
                "type": "user",
                "cwd": "/workspace",
                "entrypoint": "sdk-cli",
                "sessionId": uuid_name,
                "message": {"role": "user", "content": prompt},
            }
        ),
    ]
    path = session_dir / f"{uuid_name}.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return path


def _write_agy_transcript(session_dir: Path, task_id: str, session_uuid="04c2580a-bdb1-4a57"):
    logs = session_dir / "agy-brain" / session_uuid / ".system_generated" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / "transcript.jsonl"
    path.write_text(
        json.dumps(
            {"type": "USER_INPUT", "content": f"<USER_REQUEST>\n/pull {task_id}\n</USER_REQUEST>"}
        )
        + "\n"
    )
    return path


# ---------------------------------------------------------------------------
# _transcript_paths — the evidence locations, per CLI
# ---------------------------------------------------------------------------


def test_claude_transcript_is_found_at_the_session_dir_root(tmp_path):
    """`session_dir` is bind-mounted at `CLAUDE_SESSION_PATH`, claude's own
    project-state directory for `cwd=/workspace`, so its `<uuid>.jsonl` lands
    directly there — verified against live session dirs under
    `$AOPS_SESSIONS/logs/`."""
    written = _write_claude_transcript(tmp_path / "session")

    assert cli._transcript_paths(tmp_path / "session") == [written]


def test_agy_transcript_is_found_under_the_brain_mount(tmp_path):
    written = _write_agy_transcript(tmp_path / "session", "task_abc123")

    assert cli._transcript_paths(tmp_path / "session") == [written]


def test_polecats_own_jsonl_files_are_not_mistaken_for_a_transcript(tmp_path):
    """The hook log and the run record share the session dir and the `.jsonl`
    suffix. Counting either as the conversation would make "a transcript was
    persisted" true of every run, including one that recorded nothing."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    (session_dir / "polecat-session-hooks.jsonl").write_text('{"hook":"SessionStart"}\n')
    (session_dir / "run.json").write_text("{}\n")
    (session_dir / "agy-cli.log").write_text("")

    assert cli._transcript_paths(session_dir) == []
    assert cli.transcript_evidence(session_dir) == {
        "found": False,
        "path": None,
        "bytes": None,
        "count": 0,
        "transcript_path": None,
        "transcript_bytes": None,
        "event_count": 0,
    }


def test_transcript_evidence_names_the_substantive_transcript(tmp_path):
    """A resumed session leaves more than one transcript; the record names the
    one carrying the conversation, and counts the rest."""
    session_dir = tmp_path / "session"
    _write_claude_transcript(session_dir, uuid_name="11111111-1111-1111-1111-111111111111")
    big = _write_claude_transcript(session_dir, uuid_name="22222222-2222-2222-2222-222222222222")
    big.write_text(big.read_text() + json.dumps({"type": "assistant"}) * 50 + "\n")

    evidence = cli.transcript_evidence(session_dir)

    assert evidence["found"] is True
    assert evidence["path"] == str(big)
    assert evidence["bytes"] == big.stat().st_size > 0
    assert evidence["count"] == 2
    assert evidence["transcript_path"] == str(big)
    assert evidence["transcript_bytes"] == big.stat().st_size
    assert evidence["event_count"] > 0


# ---------------------------------------------------------------------------
# _seed_confirmed — same verification whichever CLI ran the dispatch
# ---------------------------------------------------------------------------


def test_seed_confirmed_reads_a_claude_transcript(tmp_path):
    """Established from a real dispatch: `$AOPS_SESSIONS/logs/20260804/
    session-6ea08bd0/aops/6912ac2b-….jsonl` carries the seeded prompt verbatim
    (`/pull aops_89fc51db`) as the first user message, with `cwd=/workspace`."""
    _write_claude_transcript(tmp_path / "session", task_id="aops_89fc51db")

    assert cli._seed_confirmed(tmp_path / "session", "aops_89fc51db") is True


def test_seed_confirmed_false_for_claude_when_the_transcript_is_about_another_task(tmp_path):
    _write_claude_transcript(tmp_path / "session", task_id="aops_other")

    assert cli._seed_confirmed(tmp_path / "session", "aops_89fc51db") is False


def test_seed_confirmed_false_for_claude_when_nothing_was_persisted(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    (session_dir / "polecat-session-hooks.jsonl").write_text("")

    assert cli._seed_confirmed(session_dir, "aops_89fc51db") is False


# ---------------------------------------------------------------------------
# run() — seeded claude dispatch is verified, and every run records the outcome
# ---------------------------------------------------------------------------


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
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _mounted_session_dir(cmd, container_path):
    """The host directory `cmd` bind-mounts at `container_path` — so a fake
    container writes where a real one would, with no second copy of the layout
    in the test."""
    for flag, value in zip(cmd, cmd[1:], strict=False):
        if flag == "-v" and value.endswith(f":{container_path}"):
            return Path(value[: -len(container_path) - 1])
    raise AssertionError(f"no bind mount for {container_path} in {cmd}")


def _fake_docker(writer=None):
    """A `subprocess.run` that runs everything except `docker run` for real, and
    lets `writer` persist whatever that container would have persisted."""
    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            if writer is not None:
                writer(_mounted_session_dir(cmd, cli.CLAUDE_SESSION_PATH))
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    return fake_run


def _the_run_record(tmp_path):
    records = list((tmp_path / "sessions").glob("**/run.json"))
    assert len(records) == 1, f"expected exactly one run.json, got {records}"
    return json.loads(records[0].read_text())


def test_seeded_claude_dispatch_fails_when_the_transcript_shows_no_task(tmp_path, monkeypatch):
    """Seed verification used to be gated off for claude entirely, so a claude
    container that dropped the seed and exited 0 reported success."""
    attempts = {"n": 0}

    def writer(session_dir):
        attempts["n"] += 1
        _write_claude_transcript(session_dir, task_id="aops_something_else")

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", _fake_docker(writer))

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-t", "aops_deadbeef"]
    )

    assert result.exit_code != 0
    assert attempts["n"] == 2, "expected exactly one retry before failing fast"
    assert "aops_deadbeef" in result.output


def test_seeded_claude_dispatch_succeeds_when_the_transcript_shows_the_task(tmp_path, monkeypatch):
    attempts = {"n": 0}

    def writer(session_dir):
        attempts["n"] += 1
        _write_claude_transcript(session_dir, task_id="aops_deadbeef")

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", _fake_docker(writer))

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-t", "aops_deadbeef"]
    )

    assert result.exit_code == 0, result.output
    assert attempts["n"] == 1


def test_run_record_names_the_transcript_a_run_persisted(tmp_path, monkeypatch):
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        _fake_docker(lambda session_dir: _write_claude_transcript(session_dir)),
    )

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-s", "session-fat"]
    )
    assert result.exit_code == 0, result.output

    record = _the_run_record(tmp_path)
    assert record["status"] == "success"
    assert record["transcript"]["found"] is True
    assert record["transcript"]["count"] == 1
    transcript = Path(record["transcript"]["path"])
    assert transcript.is_file(), f"run.json names a transcript that does not exist: {transcript}"
    assert record["transcript"]["bytes"] == transcript.stat().st_size > 0
    assert record["transcript"]["transcript_path"] == str(transcript)
    assert record["transcript"]["transcript_bytes"] == transcript.stat().st_size
    assert record["transcript"]["event_count"] == 2
    assert not any(d.get("what") in ("transcript", "transcript_missing") for d in record["degraded"])


def test_a_run_that_persisted_nothing_is_not_indistinguishable_from_one_that_did(
    tmp_path, monkeypatch
):
    """The whole point: zero bytes written, exit 0, `"status": "success"` — the
    record has to carry something that contradicts the claim."""
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", _fake_docker(writer=None))

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-s", "session-empty"]
    )
    assert result.exit_code == 0, result.output

    record = _the_run_record(tmp_path)
    assert record["transcript"] == {
        "found": False,
        "path": None,
        "bytes": None,
        "count": 0,
        "transcript_path": None,
        "transcript_bytes": None,
        "event_count": 0,
    }
    assert record["status"] == "degraded"
    assert any(d.get("what") == "transcript_missing" for d in record["degraded"])


def test_transcript_is_recorded_even_when_the_container_failed(tmp_path, monkeypatch):
    """A crashed run's partial transcript is exactly what an operator needs; the
    record must point at it rather than only report the exit code."""
    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["docker", "run"]:
            _write_claude_transcript(_mounted_session_dir(cmd, cli.CLAUDE_SESSION_PATH))
            return subprocess.CompletedProcess(cmd, 3)
        return real_run(cmd, *a, **kw)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli.main, ["run", "claude", "-d", str(tmp_path / "repo"), "-s", "session-crash"]
    )
    assert result.exit_code == 3

    record = _the_run_record(tmp_path)
    assert record["status"] == "failed"
    assert record["transcript"]["found"] is True


# ---------------------------------------------------------------------------
# Live container — the host-side path, proven against the real image
# ---------------------------------------------------------------------------


_E2E_TIMEOUT = 300
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def live_claude_dispatch(tmp_path):
    """Everything a real `polecat run claude` needs, or an explicit skip.

    A missing precondition must read as a skip, never a silent pass.
    """
    if os.environ.get("POLECAT_E2E") != "1":
        pytest.skip("POLECAT_E2E is not '1' — set it to run a real container")
    if shutil.which("docker") is None:
        pytest.skip("docker is not on PATH")
    if (
        subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        ).returncode
        != 0
    ):
        pytest.skip("the docker daemon is not reachable")
    image = os.environ.get("POLECAT_IMAGE", "aops-crew:latest")
    if (
        subprocess.run(
            ["docker", "image", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).returncode
        != 0
    ):
        pytest.skip(f"image {image!r} is not present locally — run `make docker-build` first")
    token = os.environ.get("AOPS_CC_OAUTH_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not token:
        pytest.skip("no claude credential in the environment — a container could not authenticate")

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("polecat transcript persistence probe\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    config = tmp_path / "polecat.yaml"
    config.write_text("git_identity:\n  name: polecat-e2e\n  email: polecat-e2e@invalid.example\n")

    env = dict(os.environ)
    env.update(
        {
            "AOPS_SESSIONS": str(tmp_path / "sessions"),
            "POLECAT_HOME": str(tmp_path / "polecat-home"),
            "POLECAT_IMAGE": image,
            "AOPS_POLECAT_CONFIG": str(config),
            "CLAUDE_CODE_OAUTH_TOKEN": token,
        }
    )
    return {"env": env, "repo": repo, "sessions": tmp_path / "sessions"}


@pytest.mark.e2e
def test_a_real_claude_container_persists_a_transcript_to_the_host(live_claude_dispatch):
    """The restored end-to-end guarantee: a real container's conversation lands
    on the host, is a real transcript rather than a stub, and `run.json` names
    it. Failing here means the mount, the client's state path, or the record
    have drifted apart — each of which is invisible to every check above."""
    session_id = f"e2e-transcript-{uuid.uuid4().hex[:8]}"
    cmd = [
        "uv",
        "run",
        "polecat",
        "run",
        "claude",
        "-d",
        str(live_claude_dispatch["repo"]),
        "-s",
        session_id,
        "--print",
        "Reply with exactly: OK. Change no files.",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_REPO_ROOT),
            env=live_claude_dispatch["env"],
            capture_output=True,
            text=True,
            timeout=_E2E_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["docker", "rm", "-f", f"polecat-{session_id}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        raise

    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    records = list(live_claude_dispatch["sessions"].glob(f"logs/*/{session_id}/*/run.json"))
    assert len(records) == 1, f"expected one run.json, got {records}"
    record = json.loads(records[0].read_text())

    assert record["transcript"]["found"] is True, (
        f"the container persisted no transcript under {records[0].parent}: "
        f"{[p.name for p in records[0].parent.iterdir()]}"
    )
    transcript = Path(record["transcript"]["path"])
    assert transcript.is_file()
    assert record["transcript"]["transcript_path"] == str(transcript)
    assert record["transcript"]["transcript_bytes"] == transcript.stat().st_size
    # Fat, not a stub — a truncated or placeholder write must fail loudly.
    assert transcript.stat().st_size >= 1_000, f"{transcript} is only {transcript.stat().st_size}B"
    assert record["transcript"]["transcript_bytes"] >= 1_000
    lines = [line for line in transcript.read_text().splitlines() if line.strip()]
    assert lines, f"{transcript} is empty"
    assert record["transcript"]["event_count"] == len(lines)
    assert record["transcript"]["event_count"] > 0
    assert isinstance(json.loads(lines[-1]), dict), (
        f"last line of {transcript} is not a JSON object"
    )
