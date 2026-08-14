"""Regression tests for the `docker run` invocation polecat constructs.

Three defects are covered here, all of them live-confirmed against a real
container:

Headless flag: with stdin not a tty and no headless flag from the caller,
`run()` used to append `--non-interactive` to the claude invocation. No such
flag exists — claude exits immediately with `error: unknown option
'--non-interactive'` — so every piped or scripted `polecat run claude` died
before it started. Claude's headless one-shot mode is `-p`/`--print`.

Credential isolation: lib/hooks/credentials.py scopes a session's environment
only when `CLAUDE_ENV_FILE` names a file it can write. Nothing ever set it, so
the isolation silently never happened. It must be set to a container-local
path — one no bind mount covers, so the credentials it holds die with the
container.

Environment contract: the same name must reach a plain `docker run` assembled
from `env_contract --docker-args`, which is how the Makefile's docker targets
start a container.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.polecat import cli
from lib.polecat.env_contract import CONTAINER_SET_ENV, docker_env_args

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _base_mocks(monkeypatch, tmp_path):
    """Everything docker- and filesystem-heavy stubbed out, so `run()` is
    exercised purely for the command it builds."""
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
    """Invoke `polecat run ...` and return the `docker run` argv it built.

    CliRunner's stdin is never a tty, so this is exactly the piped/headless
    path that failed live.
    """
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
    return captured[0]


def _inner_cmd(docker_cmd, image="test-image:latest"):
    """The part of the docker argv after the image — the agent invocation."""
    return docker_cmd[docker_cmd.index(image) + 1 :]


def _invoke_capturing(monkeypatch, tmp_path, argv):
    """Invoke `polecat run ...` without asserting success, returning the click
    result and every docker argv it built (normally none, for a rejected run)."""
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    return CliRunner().invoke(cli.main, argv), captured


# --------------------------------------------------------------------------
# Headless invocation
# --------------------------------------------------------------------------


def test_headless_claude_uses_print_not_a_nonexistent_flag(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )
    inner = _inner_cmd(cmd)

    assert inner[0] == "claude"
    assert "--print" in inner
    assert "--non-interactive" not in inner
    # -it against a pipe is a hard docker failure, so it must stay off too.
    assert "-it" not in cmd


def test_headless_claude_keeps_the_prompt_positional(tmp_path, monkeypatch):
    """`--print` is a boolean and the prompt is a positional, so a seeded task
    must still arrive as its own argument after the flag."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--print") == 1
    assert inner[-1] == "/pull task_abc123"


def test_caller_supplied_print_is_not_duplicated(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--print", "hello"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--print") == 1
    assert inner[-1] == "hello"


@pytest.mark.parametrize("agent", ["claude", "agy"])
def test_caller_supplied_non_interactive_is_rejected_before_anything_starts(
    agent, tmp_path, monkeypatch
):
    """`--non-interactive` was once documented as a headless flag but neither
    CLI has ever had one — `claude --help` and `agy --help` both offer only
    `-p`/`--print`. Forwarded verbatim it dies inside the container; polecat
    must reject it up front and name the replacement."""
    result, captured = _invoke_capturing(
        monkeypatch,
        tmp_path,
        ["run", agent, "-d", str(tmp_path / "repo"), "--non-interactive"],
    )

    assert result.exit_code != 0
    assert "--print" in result.output
    assert captured == [], "no container may start for an invocation that cannot work"


@pytest.mark.parametrize(
    "argv",
    [
        ["run", "ida", "-d", "repo"],
        ["run", "claude", "-d", "repo", "--agent", "ida"],
        ["run", "claude", "-d", "repo", "--agent=ida"],
        ["run", "agy", "-d", "repo", "--agent", "ida"],
        ["run", "agy", "-d", "repo", "--agent=ida"],
    ],
)
def test_ida_is_rejected_as_agent_cmd_or_agent_flag(argv, tmp_path, monkeypatch):
    """ida is the interactive face plugin and is not installed in polecat containers."""
    argv_with_path = [a if a != "repo" else str(tmp_path / "repo") for a in argv]
    result, captured = _invoke_capturing(monkeypatch, tmp_path, argv_with_path)

    assert result.exit_code != 0
    assert "ida is the interactive face plugin and is not installed" in result.output
    assert captured == [], "no container may start when ida is requested"


def test_non_interactive_is_not_treated_as_a_headless_signal(tmp_path, monkeypatch):
    """It must not satisfy the headless check either: counting a flag that
    does not exist as 'the caller asked for headless' suppressed the real
    `--print` polecat would otherwise add."""
    assert "--non-interactive" not in cli.HEADLESS_FLAGS
    assert cli.HEADLESS_FLAGS == {"-p", "--print"}


def test_passthrough_commands_keep_their_own_flags(tmp_path, monkeypatch):
    """The guard covers the two agent CLIs polecat knows. An arbitrary command
    gets its args forwarded untouched — polecat does not police flags for a
    binary whose interface it has no knowledge of."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "some-other-tool", "-d", str(tmp_path / "repo"), "--non-interactive"],
    )

    assert _inner_cmd(cmd) == ["some-other-tool", "--non-interactive"]


def test_agy_invocation_is_unchanged_by_the_claude_headless_fix(tmp_path, monkeypatch):
    """The headless handling is claude-specific: agy gets its own `--print`
    from the prompt path and must never pick up claude's flags."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "agy",
        "--dangerously-skip-permissions",
        "--log-file",
        "/home/worker/.gemini/antigravity-cli/cli.log",
        "--agent",
        "james",
        "--print",
        "/pull task_abc123",
    ]
    assert "--non-interactive" not in inner


# --------------------------------------------------------------------------
# Default agent
# --------------------------------------------------------------------------


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_all_clients_boot_as_the_default_agent(client, tmp_path, monkeypatch):
    """A dispatched worker with no agent named must boot as DEFAULT_AGENT (james) on all clients."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == cli.DEFAULT_AGENT


@pytest.mark.parametrize("client", ["claude", "agy"])
@pytest.mark.parametrize("flag", ["--agent", "-a"])
def test_cli_agent_option_overrides_default_agent(client, flag, tmp_path, monkeypatch):
    """The --agent / -a Click option allows changing the agent persona on all clients."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), flag, "pauli", "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "pauli"
    assert cli.DEFAULT_AGENT not in inner


@pytest.mark.parametrize("agent_cmd", ["shell", "bash", "sleep", "some-other-tool"])
def test_non_agent_commands_never_get_the_agent_flag(agent_cmd, tmp_path, monkeypatch):
    """`--agent` means nothing to bash or sleep; a stray flag would break them."""
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", agent_cmd, "-d", str(tmp_path / "repo")]
    )
    inner = _inner_cmd(cmd)

    assert "--agent" not in inner
    assert cli.DEFAULT_AGENT not in inner


def test_caller_supplied_agent_wins_over_the_default_for_claude(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--agent", "rbg", "hello"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "rbg"
    assert cli.DEFAULT_AGENT not in inner


def test_caller_supplied_agent_wins_over_the_default_for_agy(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "--print", "hello", "--agent", "rbg"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "rbg"
    assert cli.DEFAULT_AGENT not in inner


def test_caller_supplied_agent_in_equals_form_is_not_duplicated(tmp_path, monkeypatch):
    """`--agent=rbg` is parsed as setting the agent persona without duplicating."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--agent=rbg", "hello"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "rbg"
    assert cli.DEFAULT_AGENT not in inner


def test_the_default_agent_name_appears_once_in_the_source():
    """One constant, two branches. A second literal is a second place to change
    it and a chance for the two clients to drift apart."""
    source = (_REPO_ROOT / "lib" / "polecat" / "cli.py").read_text()

    assert source.count(f'"{cli.DEFAULT_AGENT}"') == 1


# --------------------------------------------------------------------------
# Credential isolation
# --------------------------------------------------------------------------


def test_env_file_is_set_for_the_container(monkeypatch):
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["CLAUDE_ENV_FILE"] == CONTAINER_SET_ENV["CLAUDE_ENV_FILE"]
    assert env["CLAUDE_ENV_FILE"].startswith("/")


def test_host_env_file_path_never_reaches_the_container(monkeypatch):
    """A host path names a file the container cannot see; the credential hook
    would fail to write it and the session would run unscoped."""
    monkeypatch.setenv("CLAUDE_ENV_FILE", "/home/someone/host-only/session.env")
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}

    assert cli.get_env_forwards(config)["CLAUDE_ENV_FILE"] == CONTAINER_SET_ENV["CLAUDE_ENV_FILE"]


def test_env_file_is_outside_every_bind_mount(tmp_path, monkeypatch):
    """The scoped env file holds GitHub tokens. If its path fell under a bind
    mount it would outlive the container on the host's disk."""
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )
    env_file = Path(CONTAINER_SET_ENV["CLAUDE_ENV_FILE"])

    mount_targets = [
        Path(cmd[i + 1].split(":")[1])
        for i, arg in enumerate(cmd)
        if arg == "-v" and i + 1 < len(cmd)
    ]
    for target in mount_targets:
        assert not env_file.is_relative_to(target), f"{env_file} lands inside bind mount {target}"


def test_docker_run_passes_the_env_file(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )

    expected = f"CLAUDE_ENV_FILE={CONTAINER_SET_ENV['CLAUDE_ENV_FILE']}"
    assert expected in cmd
    assert cmd[cmd.index(expected) - 1] == "-e"


# --------------------------------------------------------------------------
# Environment contract
# --------------------------------------------------------------------------


def test_docker_args_carry_the_env_file_with_its_value():
    """Forwarding it by bare name would propagate the host's value, or
    nothing. This one name has to carry the container's own path."""
    args = docker_env_args()

    assert f"CLAUDE_ENV_FILE={CONTAINER_SET_ENV['CLAUDE_ENV_FILE']}" in args
    assert "CLAUDE_ENV_FILE" not in args


def test_docker_args_cli_output_matches_the_makefile_contract():
    """The Makefile's docker targets splice this output straight into
    `docker run`, so the CLI surface must carry the name too."""
    result = subprocess.run(
        [sys.executable, "-m", "lib.polecat.env_contract", "--docker-args"],
        cwd=_REPO_ROOT,
        env={"PYTHONPATH": str(_REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"-e CLAUDE_ENV_FILE={CONTAINER_SET_ENV['CLAUDE_ENV_FILE']}" in result.stdout


# --------------------------------------------------------------------------
# Import shape
# --------------------------------------------------------------------------


def test_cli_runs_as_a_bare_script():
    """cli.py is documented as directly runnable (specs/polecat/), which takes
    the ImportError fallback rather than the package import."""
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "lib" / "polecat" / "cli.py"), "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Polecat" in result.stdout


@pytest.mark.skipif(shutil.which("basedpyright") is None, reason="basedpyright not installed")
def test_polecat_typechecks_clean():
    """Both import paths have to resolve for the type checker, not just at
    runtime: the fallback used to import a bare `env_contract` that no
    configured path could resolve."""
    result = subprocess.run(
        ["basedpyright", "--outputjson", "lib/polecat/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )

    diagnostics = json.loads(result.stdout)["generalDiagnostics"]
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    assert errors == [], errors


def test_sessions_mount_via_with_sessions_flag(monkeypatch, tmp_path):
    """Passing --with-sessions mounts transcripts ro and sets AOPS_SESSIONS=/sessions."""
    docker_cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo"), "--with-sessions"]
    )
    sessions_dir = tmp_path / "sessions"
    expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"

    assert "-v" in docker_cmd
    assert expected_mount in docker_cmd
    assert "-e" in docker_cmd
    assert "AOPS_SESSIONS=/sessions" in docker_cmd


def test_sessions_mount_via_project_config(monkeypatch, tmp_path):
    """Configuring sessions_access: true mounts transcripts ro and sets AOPS_SESSIONS=/sessions."""
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
            "sessions_access": True,
        },
    )
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])
    assert result.exit_code == 0, result.output
    docker_cmd = captured[0]

    sessions_dir = tmp_path / "sessions"
    expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"

    assert expected_mount in docker_cmd
    assert "AOPS_SESSIONS=/sessions" in docker_cmd


def test_branch_option_sets_env_var(monkeypatch, tmp_path):
    """Passing --branch sets AOPS_POLECAT_BRANCH in container env."""
    docker_cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--branch", "feature/test-branch"],
    )
    assert "AOPS_POLECAT_BRANCH=feature/test-branch" in docker_cmd
