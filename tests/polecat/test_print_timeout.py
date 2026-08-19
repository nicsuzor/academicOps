"""Regression tests for `POLECAT_PRINT_TIMEOUT` reaching agy, and surviving.

Two live-confirmed defects:

1. Unreachable on the canonical path. The env var was read only inside the
   `extra_args` branch of `_build_inner_command`, so a seeded `-t` dispatch —
   which is what `pc` actually launches — silently discarded it and every run
   sat on agy's 5m default no matter what the operator exported.

2. Forwarded verbatim, so a bare integer killed the run at flag parsing. agy
   parses the value with Go's `time.ParseDuration`:

       invalid value "900" for flag -print-timeout: time: missing unit in
       duration "900"
       EXIT=2

   which surfaced as `status: failed`, `exit_code: 2` and a delivery-guard
   error in run.json — before the agent had run at all.

claude has no timeout flag of any kind (`claude --help` lists none), so the
handling is agy-only by design.
"""

import subprocess

import pytest
from click.testing import CliRunner

from lib.polecat import cli


@pytest.fixture(autouse=True)
def _no_inherited_timeout(monkeypatch):
    """The host shell may export POLECAT_PRINT_TIMEOUT; every test here sets
    its own value or asserts on its absence."""
    monkeypatch.delenv("POLECAT_PRINT_TIMEOUT", raising=False)


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


def _capture_inner_cmd(monkeypatch, tmp_path, argv, image="test-image:latest"):
    """The agent invocation polecat builds inside the `docker run` argv."""
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
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}"
    docker_cmd = captured[0]
    return docker_cmd[docker_cmd.index(image) + 1 :]


def _seeded_inner_cmd(agent_cmd="agy", task="task_abc123"):
    inner, _, _, _ = cli._build_inner_command(
        agent_cmd,
        extra_args=(),
        is_interactive=False,
        explicit_headless=False,
        task=task,
    )
    return inner


def _flag_value(inner, flag):
    return inner[inner.index(flag) + 1] if flag in inner else None


# --------------------------------------------------------------------------
# Defect 1: the seeded `-t` dispatch must honour the timeout
# --------------------------------------------------------------------------


def test_seeded_task_dispatch_carries_the_print_timeout(monkeypatch):
    """`-t` with no explicit prompt is the production path; it used to drop the
    operator's timeout on the floor."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "30m")
    inner = _seeded_inner_cmd()

    assert _flag_value(inner, "--print-timeout") == "30m"


def test_seeded_dispatch_puts_the_timeout_immediately_before_print(monkeypatch):
    """A value-taking flag consumes the next token whatever it is, so nothing
    may sit between `--print` and the prompt it seeds."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "30m")
    inner = _seeded_inner_cmd(task="task_abc123")

    assert inner[-4:] == ["--print-timeout", "30m", "--print", "/pull task_abc123"]


def test_seeded_dispatch_has_no_timeout_flag_when_unset():
    """Absent the env var the invocation is exactly what it was before."""
    inner = _seeded_inner_cmd()

    assert "--print-timeout" not in inner
    assert inner[-2:] == ["--print", "/pull task_abc123"]


def test_seeded_dispatch_end_to_end_through_the_cli(tmp_path, monkeypatch):
    """The same fix as it reaches the real `docker run` argv."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "45m")
    inner = _capture_inner_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )

    assert inner[-4:] == ["--print-timeout", "45m", "--print", "/pull task_abc123"]


def test_claude_seeded_dispatch_gets_no_timeout_flag(monkeypatch):
    """claude has no `--print-timeout`; passing one would be an unknown-option
    failure inside the container."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "30m")
    inner = _seeded_inner_cmd(agent_cmd="claude")

    assert "--print-timeout" not in inner


def test_explicit_prompt_dispatch_carries_the_print_timeout(monkeypatch):
    """agy's `--prompt` is an alias for `--print`, so that branch is headless
    too and must honour the timeout the same way."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "30m")
    inner, _, _, _ = cli._build_inner_command(
        "agy",
        extra_args=(),
        is_interactive=False,
        explicit_headless=False,
        task=None,
        prompt="hello",
    )

    assert inner[-4:] == ["--print-timeout", "30m", "--prompt", "hello"]


# --------------------------------------------------------------------------
# Defect 2: the value must be a Go duration by the time agy sees it
# --------------------------------------------------------------------------


def test_bare_integer_is_normalised_to_seconds(monkeypatch):
    """`900` alone is `time: missing unit in duration "900"` and exit 2. Read
    it as seconds rather than shipping a run-killing value."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "900")

    assert cli._print_timeout_args() == ["--print-timeout", "900s"]


@pytest.mark.parametrize("value", ["30m", "1h", "1h30m", "900s", "500ms", "2.5h"])
def test_values_that_already_carry_a_unit_pass_through_unchanged(value, monkeypatch):
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", value)

    assert cli._print_timeout_args() == ["--print-timeout", value]


def test_surrounding_whitespace_is_stripped(monkeypatch):
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "  30m  ")

    assert cli._print_timeout_args() == ["--print-timeout", "30m"]


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_value_is_the_same_as_unset(value, monkeypatch):
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", value)

    assert cli._print_timeout_args() == []


def test_unset_value_adds_no_flag():
    assert cli._print_timeout_args() == []


@pytest.mark.parametrize("value", ["30 minutes", "half an hour", "30x", "m30", "-"])
def test_garbage_is_dropped_with_a_visible_warning(value, monkeypatch, capsys):
    """Never silently: a dropped timeout the operator believes is in force is
    how a long run dies at 5m with no explanation."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", value)

    assert cli._print_timeout_args() == []
    stderr = capsys.readouterr().err
    assert "POLECAT_PRINT_TIMEOUT" in stderr
    assert "Go duration" in stderr


def test_garbage_does_not_reach_the_container(monkeypatch):
    """The whole point: an unparseable value must not become argv."""
    monkeypatch.setenv("POLECAT_PRINT_TIMEOUT", "30 minutes")
    inner = _seeded_inner_cmd()

    assert "--print-timeout" not in inner
    assert "30 minutes" not in inner
