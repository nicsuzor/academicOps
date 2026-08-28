"""Regression tests for `timeout` in polecat.yaml reaching agy.

Two live-confirmed defects:

1. Unreachable on the canonical path. The timeout was previously read only inside the
   `extra_args` branch of `_build_inner_command`, so a seeded `-t` dispatch —
   which is what `pc` actually launches — silently discarded it and every run
   sat on agy's 5m default.

2. Forwarded verbatim, so a bare integer killed the run at flag parsing. agy
   parses the value with Go's `time.ParseDuration`:

       invalid value "900" for flag -print-timeout: time: missing unit in
       duration "900"
       EXIT=2

   which surfaced as `status: failed`, `exit_code: 2` and a delivery-guard
   error in run.json — before the agent had run at all.

3. Configuration comes strictly from `polecat.yaml` (key: `timeout`),
   with no ambient environment fallback (`POLECAT_TIMEOUT`), and fails fast on invalid durations.

claude has no timeout flag of any kind (`claude --help` lists none), so the
handling is agy-only by design.
"""

import subprocess

import pytest
from click.testing import CliRunner

from lib.polecat import cli


def _base_mocks(monkeypatch, tmp_path, config=None):
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    cfg = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}
    if config:
        cfg.update(config)
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def _capture_inner_cmd(monkeypatch, tmp_path, argv, config=None, image="test-image:latest"):
    """The agent invocation polecat builds inside the `docker run` argv."""
    _base_mocks(monkeypatch, tmp_path, config=config)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert result.exit_code == 0, result.output
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}"
    docker_cmd = captured[0]
    return docker_cmd[docker_cmd.index(image) + 1 :]


def _seeded_inner_cmd(agent_cmd="agy", task="task_abc123", config=None):
    inner, _, _, _ = cli._build_inner_command(
        agent_cmd,
        extra_args=(),
        is_interactive=False,
        explicit_headless=False,
        task=task,
        config=config,
    )
    return inner


def _flag_value(inner, flag):
    return inner[inner.index(flag) + 1] if flag in inner else None


# --------------------------------------------------------------------------
# Defect 1: the seeded `-t` dispatch must honour the timeout
# --------------------------------------------------------------------------


def test_seeded_task_dispatch_carries_the_print_timeout():
    """`-t` with no explicit prompt is the production path; it must honour configured timeout."""
    inner = _seeded_inner_cmd(config={"timeout": "30m"})

    assert _flag_value(inner, "--print-timeout") == "30m"


def test_seeded_dispatch_puts_the_timeout_immediately_before_print():
    """A value-taking flag consumes the next token whatever it is, so nothing
    may sit between `--print` and the prompt it seeds."""
    inner = _seeded_inner_cmd(task="task_abc123", config={"timeout": "30m"})

    assert inner[-4:] == ["--print-timeout", "30m", "--print", "/pull task_abc123"]


def test_seeded_dispatch_has_no_timeout_flag_when_unset():
    """Absent the timeout in config the invocation has no --print-timeout flag."""
    inner = _seeded_inner_cmd(config={})

    assert "--print-timeout" not in inner
    assert inner[-2:] == ["--print", "/pull task_abc123"]


def test_seeded_dispatch_end_to_end_through_the_cli(tmp_path, monkeypatch):
    """The same fix as it reaches the real `docker run` argv."""
    inner = _capture_inner_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
        config={"timeout": "45m"},
    )

    assert inner[-4:] == ["--print-timeout", "45m", "--print", "/pull task_abc123"]


def test_claude_seeded_dispatch_gets_no_timeout_flag():
    """claude has no `--print-timeout`; passing one would be an unknown-option
    failure inside the container."""
    inner = _seeded_inner_cmd(agent_cmd="claude", config={"timeout": "30m"})

    assert "--print-timeout" not in inner


def test_explicit_prompt_dispatch_carries_the_print_timeout():
    """agy's `--prompt` is an alias for `--print`, so that branch is headless
    too and must honour the timeout the same way."""
    inner, _, _, _ = cli._build_inner_command(
        "agy",
        extra_args=(),
        is_interactive=False,
        explicit_headless=False,
        task=None,
        prompt="hello",
        config={"timeout": "30m"},
    )

    assert inner[-4:] == ["--print-timeout", "30m", "--prompt", "hello"]


# --------------------------------------------------------------------------
# Normalisation and validation of Go duration
# --------------------------------------------------------------------------


def test_bare_integer_is_normalised_to_seconds():
    """`900` alone is normalised to seconds (900s) for Go duration parsing."""
    assert cli._print_timeout_args({"timeout": "900"}) == ["--print-timeout", "900s"]
    assert cli._print_timeout_args({"timeout": 900}) == ["--print-timeout", "900s"]


@pytest.mark.parametrize("value", ["30m", "1h", "1h30m", "900s", "500ms", "2.5h"])
def test_values_that_already_carry_a_unit_pass_through_unchanged(value):
    assert cli._print_timeout_args({"timeout": value}) == ["--print-timeout", value]


def test_surrounding_whitespace_is_stripped():
    assert cli._print_timeout_args({"timeout": "  30m  "}) == ["--print-timeout", "30m"]


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_value_is_the_same_as_unset(value):
    assert cli._print_timeout_args({"timeout": value}) == []


def test_unset_value_adds_no_flag():
    assert cli._print_timeout_args({}) == []


@pytest.mark.parametrize("value", ["30 minutes", "half an hour", "30x", "m30", "-"])
def test_garbage_fails_fast(value):
    """An unparseable value fails loudly rather than being silently ignored."""
    with pytest.raises(SystemExit):
        cli._print_timeout_args({"timeout": value})


def test_ambient_env_var_is_ignored(monkeypatch):
    """Host POLECAT_TIMEOUT is ignored: config is strictly from polecat.yaml."""
    monkeypatch.setenv("POLECAT_TIMEOUT", "30m")
    assert cli._print_timeout_args({}) == []
