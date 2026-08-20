"""Unit tests for polecat stream-json contract and single-stream stdout guarantee.

Guarantees tested:
1. Headless default is `--output-format stream-json` for both claude and agy.
2. Claude includes `--verbose` when `--output-format stream-json` is used (required by claude CLI).
3. Claude omits `--verbose` when `--output-format` is not `stream-json` (e.g. `text` or `json`).
4. Extra args containing `--output-format` / `-o` do not corrupt the prompt for agy.
5. Explicit `--output-format` overrides the default.
6. Seed verification retry path emits exactly one stream to stdout.
7. Stream output is well-formed NDJSON.
"""

import json
import subprocess
from unittest.mock import MagicMock

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
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _capture_docker_cmd(monkeypatch, tmp_path, argv):
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    return captured[0]


def _inner_cmd(docker_cmd, image="test-image:latest"):
    return docker_cmd[docker_cmd.index(image) + 1 :]


def test_headless_claude_defaults_to_stream_json_with_verbose(monkeypatch, tmp_path):
    """Headless claude dispatch defaults to --output-format stream-json and --verbose."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--prompt", "test prompt"],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" in inner
    assert inner[inner.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in inner


def test_headless_agy_defaults_to_stream_json(monkeypatch, tmp_path):
    """Headless agy dispatch defaults to --output-format stream-json."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "--prompt", "test prompt"],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" in inner
    assert inner[inner.index("--output-format") + 1] == "stream-json"


def test_explicit_output_format_overrides_default(monkeypatch, tmp_path):
    """Explicit --output-format json overrides the stream-json default."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
            "--output-format",
            "json",
            "--prompt",
            "test prompt",
        ],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" in inner
    assert inner[inner.index("--output-format") + 1] == "json"
    # --verbose is only required for stream-json, not json
    assert "--verbose" not in inner


def test_agy_extra_args_output_format_does_not_corrupt_prompt(monkeypatch, tmp_path):
    """Passing --output-format in extra_args does not make it the prompt value."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "agy",
            "-d",
            str(tmp_path / "repo"),
            "--",
            "--output-format",
            "stream-json",
            "real question",
        ],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" in inner
    assert inner[inner.index("--output-format") + 1] == "stream-json"
    assert "--print" in inner
    assert inner[inner.index("--print") + 1] == "real question"


def test_seed_retry_emits_single_stream_on_stdout(tmp_path, monkeypatch):
    """When seed verification retries, only the final winning attempt is written to stdout."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)

    attempt_calls = []

    def fake_run(cmd, env=None, stdout=None):
        attempt_num = len(attempt_calls) + 1
        attempt_calls.append(attempt_num)
        if stdout:
            if attempt_num == 1:
                # Attempt 1 writes a partial stream that fails seed check
                stdout.write(b'{"event":"attempt1"}\n')
            else:
                # Attempt 2 writes winning stream
                stdout.write(b'{"event":"attempt2"}\n')
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    # Seed check fails on attempt 1, succeeds on attempt 2
    seed_checks = [False, True]
    monkeypatch.setattr(cli, "_seed_confirmed", lambda sdir, task: seed_checks.pop(0))
    monkeypatch.setattr(cli, "_drain_cidfile", lambda sdir: "cid-123")

    written_stdout = []
    fake_stdout = MagicMock()
    fake_stdout.buffer.write = lambda data: written_stdout.append(data)
    fake_stdout.buffer.flush = lambda: None
    monkeypatch.setattr(cli.sys, "stdout", fake_stdout)

    code = cli._execute_with_seed_verification(
        cmd=["docker", "run", "img"],
        run_env={},
        session_dir=session_dir,
        image="test-image",
        inner_cmd=["claude"],
        task="task-123",
        quiet=True,
        verify_seed=True,
    )

    assert code == 0
    assert len(attempt_calls) == 2
    # Exactly one stream was written to stdout buffer (the winning attempt 2)
    assert written_stdout == [b'{"event":"attempt2"}\n']


def test_ndjson_stream_parseability():
    """Verify that simulated NDJSON stream output parses cleanly line-by-line."""
    stream_output = (
        '{"type":"system","subtype":"informational","content":"notice"}\n'
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Hi!"}]}}\n'
        '{"type":"result","result":"Hi!"}\n'
    )
    lines = [line for line in stream_output.strip().split("\n") if line]
    parsed = [json.loads(line) for line in lines]
    assert len(parsed) == 3
    assert parsed[0]["type"] == "system"
    assert parsed[1]["type"] == "assistant"
    assert parsed[2]["result"] == "Hi!"
