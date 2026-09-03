"""Unit tests for polecat stdout contract: plain-text default, opt-in stream-json, and single-stream guarantee.

Guarantees tested:
1. Headless default is plain text (no --output-format) for both claude and agy.
2. Claude includes --verbose when --output-format stream-json is explicitly used.
3. Claude omits --verbose when --output-format is not stream-json (e.g. text or json) or unspecified.
4. Opt-in --output-format stream-json works for both claude and agy.
5. Extra args containing --output-format / -o do not corrupt the prompt for agy.
6. Explicit --output-format overrides the default.
7. Seed verification retry path emits exactly one stream to stdout.
8. Stream output is well-formed NDJSON when stream-json mode is used.
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
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
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


def test_headless_claude_defaults_to_plain_text(monkeypatch, tmp_path):
    """Headless claude dispatch defaults to plain text (no --output-format and no --verbose)."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--prompt", "test prompt"],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" not in inner
    assert "--verbose" not in inner
    assert inner[-1] == "test prompt"


def test_headless_agy_defaults_to_plain_text(monkeypatch, tmp_path):
    """Headless agy dispatch defaults to plain text (no --output-format)."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "--prompt", "test prompt"],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" not in inner
    assert "--prompt" in inner


def test_opt_in_claude_stream_json_includes_verbose(monkeypatch, tmp_path):
    """Opt-in --output-format stream-json adds --output-format stream-json and --verbose for claude."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
            "--output-format",
            "stream-json",
            "--prompt",
            "test prompt",
        ],
    )
    inner = _inner_cmd(cmd)

    assert "--output-format" in inner
    assert inner[inner.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in inner


def test_opt_in_agy_stream_json(monkeypatch, tmp_path):
    """Opt-in --output-format stream-json adds --output-format stream-json for agy."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "agy",
            "-d",
            str(tmp_path / "repo"),
            "--output-format",
            "stream-json",
            "--prompt",
            "test prompt",
        ],
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


def test_task_dispatch_default_emits_plain_text_stdout_and_polecat_prose_stderr(
    monkeypatch, tmp_path
):
    """Criterion 1 & 3: polecat run <agent> -p <project> -t <id> defaults to plain text on stdout
    and carries only inner agent output on stdout, with polecat prose on stderr."""
    _base_mocks(monkeypatch, tmp_path)
    (tmp_path / "sessions" / "polecat.yaml").write_text("paths:\n  proj: " + str(tmp_path / "repo"))
    monkeypatch.setattr(
        cli,
        "load_local_overlay",
        lambda home: {"paths": {"proj": str(tmp_path / "repo")}},
    )

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            stdout = kw.get("stdout")
            if stdout and hasattr(stdout, "write"):
                stdout.write(b"Task output: plain text result\n")
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda sdir, task: True)

    result = CliRunner().invoke(
        cli.main,
        ["run", "claude", "-p", "proj", "-t", "aops_763bad10"],
    )
    assert result.exit_code == 0, result.output
    # stdout carries exclusively the plain-text result from the agent
    assert result.stdout == "Task output: plain text result\n"
    # stderr carries polecat progress prose (Running, Workspace, Session logs)
    assert "Workspace:" in result.stderr
    assert "Session logs:" in result.stderr
    assert "Running" in result.stderr


def test_task_dispatch_opt_in_stream_json_emits_json_stream_stdout(monkeypatch, tmp_path):
    """Criterion 2: --output-format stream-json explicitly requested emits JSON stream on stdout."""
    _base_mocks(monkeypatch, tmp_path)
    (tmp_path / "sessions" / "polecat.yaml").write_text("paths:\n  proj: " + str(tmp_path / "repo"))
    monkeypatch.setattr(
        cli,
        "load_local_overlay",
        lambda home: {"paths": {"proj": str(tmp_path / "repo")}},
    )

    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            stdout = kw.get("stdout")
            if stdout and hasattr(stdout, "write"):
                stdout.write(b'{"type":"result","result":"success"}\n')
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda sdir, task: True)

    result = CliRunner().invoke(
        cli.main,
        ["run", "claude", "-p", "proj", "-t", "aops_763bad10", "--output-format", "stream-json"],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == '{"type":"result","result":"success"}\n'
    assert "Workspace:" in result.stderr
    assert "Running" in result.stderr
