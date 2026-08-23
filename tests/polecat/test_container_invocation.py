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
import os
import re
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


def _capture_docker_run(monkeypatch, tmp_path, argv):
    """Invoke `polecat run ...` and return `(argv, env)` for the `docker run`.

    The env matters as much as the argv now: variable values are passed to
    docker through its own environment rather than on the command line, so a
    test that only reads the argv cannot tell "forwarded" from "dropped".

    CliRunner's stdin is never a tty, so this is exactly the piped/headless
    path that failed live.
    """
    _base_mocks(monkeypatch, tmp_path)
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, argv)
    assert result.exit_code == 0, result.output
    assert len(captured) == 1, f"expected one docker run, got {len(captured)}"
    return captured[0]


def _capture_docker_cmd(monkeypatch, tmp_path, argv):
    """The `docker run` argv alone, for assertions that do not touch env."""
    return _capture_docker_run(monkeypatch, tmp_path, argv)[0]


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
        "--output-format",
        "stream-json",
        "--print",
        "/pull task_abc123",
    ]
    assert "--non-interactive" not in inner


# --------------------------------------------------------------------------
# Agent persona selection
# --------------------------------------------------------------------------


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_default_agent_is_unspecified(client, tmp_path, monkeypatch):
    """When no agent is named, no --agent flag is passed to the container by default."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert "--agent" not in inner


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_no_agent_flag_disables_default_agent(client, tmp_path, monkeypatch):
    """When --no-agent is passed, no --agent flag is passed to the container."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), "--no-agent", "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert "--agent" not in inner


@pytest.mark.parametrize("client", ["claude", "agy"])
@pytest.mark.parametrize("flag", ["--agent", "-a"])
def test_cli_agent_option_sets_agent(client, flag, tmp_path, monkeypatch):
    """The --agent / -a Click option passes --agent on all clients."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), flag, "pauli", "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "pauli"


@pytest.mark.parametrize("agent_cmd", ["shell", "bash", "sleep", "some-other-tool"])
def test_non_agent_commands_never_get_the_agent_flag(agent_cmd, tmp_path, monkeypatch):
    """`--agent` means nothing to bash or sleep; a stray flag would break them."""
    cmd = _capture_docker_cmd(
        monkeypatch, tmp_path, ["run", agent_cmd, "-d", str(tmp_path / "repo")]
    )
    inner = _inner_cmd(cmd)

    assert "--agent" not in inner


def test_caller_supplied_agent_in_extra_args_for_claude(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--agent", "rbg", "hello"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "rbg"


def test_caller_supplied_agent_in_extra_args_for_agy(tmp_path, monkeypatch):
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "agy", "-d", str(tmp_path / "repo"), "--print", "hello", "--agent", "rbg"],
    )
    inner = _inner_cmd(cmd)

    assert inner.count("--agent") == 1
    assert inner[inner.index("--agent") + 1] == "rbg"


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
# No credential value on the command line
# --------------------------------------------------------------------------

#: Sentinels that must never appear anywhere in the `docker run` argv. Each is
#: distinct so a failure names the variable that leaked.
_SECRET_SENTINELS = {
    "AOPS_BOT_GH_TOKEN": "sentinel-bot-gh-token",
    "CLAUDE_CODE_OAUTH_TOKEN": "sentinel-cc-oauth-token",
    "GEMINI_API_KEY": "sentinel-gemini-key",
    "PKB_MCP_TOKEN": "sentinel-pkb-token",
}


def _e_flag_values(cmd):
    """Every `-e` argument that carries an inline `NAME=VALUE`."""
    return [
        cmd[i + 1]
        for i, arg in enumerate(cmd)
        if arg == "-e" and i + 1 < len(cmd) and "=" in cmd[i + 1]
    ]


def test_the_test_environment_itself_holds_no_real_credential():
    """conftest's scrub is what makes every other assertion here safe to fail.

    These tests inspect `{**os.environ, **env}`. Unscrubbed, one rendered dict
    in a failure diff publishes every credential the developer's shell exports
    — to their terminal and to CI. Pin the scrub, not just the intent.
    """
    leftover = [
        name
        for name in os.environ
        if re.search(r"TOKEN|SECRET|PASSWORD|API_KEY|OAUTH", name, re.IGNORECASE)
        and not os.environ[name].startswith("sentinel-")
    ]
    assert leftover == [], f"real credential names still in the test environment: {leftover}"


def test_no_secret_value_reaches_the_docker_command_line(monkeypatch, tmp_path):
    """argv is world-readable in the host process table.

    `docker run -e KEY=VALUE` published every forwarded token to `ps` and
    `/proc/<pid>/cmdline` for any local process, for the whole life of the
    container. The values must travel in docker's own environment instead.
    """
    for name, value in _SECRET_SENTINELS.items():
        monkeypatch.setenv(name, value)

    cmd, docker_env = _capture_docker_run(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )

    joined = " ".join(cmd)
    for name, value in _SECRET_SENTINELS.items():
        assert value not in joined, f"{name} value is on the docker command line"

    # And the only inline values left are the container-internal constants.
    for inline in _e_flag_values(cmd):
        name = inline.split("=", 1)[0]
        assert name in CONTAINER_SET_ENV, f"{name} carries its value on argv"


def test_secrets_still_reach_the_container_through_dockers_environment(monkeypatch, tmp_path):
    """The other half: hidden must not mean dropped.

    A dispatch that forwards nothing is a regression, not a fix. Every name
    flagged `-e NAME` has to be resolvable from the environment `docker` is
    launched with, or the container silently starts without it.
    """
    for name, value in _SECRET_SENTINELS.items():
        monkeypatch.setenv(name, value)

    cmd, docker_env = _capture_docker_run(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )

    flagged = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-e" and i + 1 < len(cmd)]
    bare = [name for name in flagged if "=" not in name]
    assert bare, "nothing is being forwarded by bare name at all"

    # Compare and report NAMES, never values. `docker_env` is os.environ plus
    # polecat's own, so letting pytest render it on failure would print every
    # credential the developer's shell exports. conftest strips those; this
    # keeps the assertion harmless even if a name shape slips past it.
    unresolvable = [name for name in bare if name not in docker_env]
    assert unresolvable == [], f"-e flags with no value for docker to resolve: {unresolvable}"

    # The AOPS_BOT_GH_TOKEN -> three-name fan-out has no host counterpart for
    # two of its three names, so it only survives via the subprocess env.
    expected = _SECRET_SENTINELS["AOPS_BOT_GH_TOKEN"]
    wrong = [
        n
        for n in ("AOPS_BOT_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
        if docker_env.get(n) != expected
    ]
    assert wrong == [], f"fan-out did not reach docker's environment for: {wrong}"


def test_ssh_auth_sock_is_still_blanked_not_forwarded(monkeypatch, tmp_path):
    """`get_env_forwards` sets SSH_AUTH_SOCK="" to deny the container every
    agent-backed git credential path. Resolving `-e SSH_AUTH_SOCK` against the
    operator's ambient environment would hand it a live agent socket instead —
    the exact inversion of that intent. polecat's value has to win over the
    host's in the environment docker is launched with."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/run/user/1000/keyring/ssh")

    cmd, docker_env = _capture_docker_run(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo")]
    )

    assert "SSH_AUTH_SOCK" in cmd
    assert docker_env["SSH_AUTH_SOCK"] == ""
    assert "/run/user/1000/keyring/ssh" not in " ".join(cmd)


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
    docker_cmd, docker_env = _capture_docker_run(
        monkeypatch, tmp_path, ["run", "claude", "-d", str(tmp_path / "repo"), "--with-sessions"]
    )
    sessions_dir = tmp_path / "sessions"
    expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"

    assert "-v" in docker_cmd
    assert expected_mount in docker_cmd
    assert "AOPS_SESSIONS" in docker_cmd
    assert docker_cmd[docker_cmd.index("AOPS_SESSIONS") - 1] == "-e"
    assert docker_env["AOPS_SESSIONS"] == "/sessions"


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
            captured.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])
    assert result.exit_code == 0, result.output
    docker_cmd, docker_env = captured[0]

    sessions_dir = tmp_path / "sessions"
    expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"

    assert expected_mount in docker_cmd
    assert "AOPS_SESSIONS" in docker_cmd
    assert docker_env["AOPS_SESSIONS"] == "/sessions"


def test_branch_option_sets_env_var(monkeypatch, tmp_path):
    """Passing --branch sets AOPS_POLECAT_BRANCH in container env."""
    docker_cmd, docker_env = _capture_docker_run(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--branch", "feature/test-branch"],
    )
    assert "AOPS_POLECAT_BRANCH" in docker_cmd
    assert docker_cmd[docker_cmd.index("AOPS_POLECAT_BRANCH") - 1] == "-e"
    assert docker_env["AOPS_POLECAT_BRANCH"] == "feature/test-branch"


def test_agy_output_format_and_prompt_options(monkeypatch, tmp_path):
    """Passing --output-format and --prompt to agy constructs the expected flags in order."""
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
            "hello world",
        ],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "agy",
        "--dangerously-skip-permissions",
        "--log-file",
        "/home/worker/.gemini/antigravity-cli/cli.log",
        "--output-format",
        "stream-json",
        "--prompt",
        "hello world",
    ]
    assert "-it" not in cmd


def test_agy_output_format_with_positional_prompt(monkeypatch, tmp_path):
    """Passing --output-format with a positional prompt places format before prompt."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "agy",
            "-d",
            str(tmp_path / "repo"),
            "--output-format=stream-json",
            "hello positional",
        ],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "agy",
        "--dangerously-skip-permissions",
        "--log-file",
        "/home/worker/.gemini/antigravity-cli/cli.log",
        "--output-format",
        "stream-json",
        "--print",
        "hello positional",
    ]
    assert "-it" not in cmd


def test_claude_output_format_and_prompt_options(monkeypatch, tmp_path):
    """Passing --output-format and --prompt to claude constructs the expected flags."""
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
            "hello claude",
        ],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "claude",
        "--dangerously-skip-permissions",
        "--setting-sources=user,project",
        "--output-format",
        "json",
        "hello claude",
    ]
    assert "-it" not in cmd


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_dangerously_skip_permissions_is_passed_inside_container(client, tmp_path, monkeypatch):
    """Both claude and agy must be launched with --dangerously-skip-permissions inside the container."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", client, "-d", str(tmp_path / "repo"), "-t", "task_abc123"],
    )
    inner = _inner_cmd(cmd)

    assert "--dangerously-skip-permissions" in inner


# --------------------------------------------------------------------------
# Port publishing / dynamic host port mapping
# --------------------------------------------------------------------------


def test_dockerfile_exposes_port_8080():
    """Dockerfile must declare EXPOSE 8080."""
    dockerfile_path = _REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text()
    assert re.search(r"^\s*EXPOSE\s+8080\b", content, re.MULTILINE), (
        "Dockerfile must declare 'EXPOSE 8080'"
    )


def test_default_polecat_run_publishes_port_8080(tmp_path, monkeypatch):
    """Default polecat run with no CLI flags or config publishes port 8080 dynamically."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo")],
    )

    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == "8080"


@pytest.mark.parametrize("flag", ["--port", "--publish", "-P"])
def test_port_bare_number_maps_dynamically(flag, tmp_path, monkeypatch):
    """A bare port number passes dynamically (-p <port>) without loopback restriction."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), flag, "3000"],
    )

    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == "3000"


@pytest.mark.parametrize(
    "spec",
    [
        "3000:3000",
        "127.0.0.1::8080",
        "127.0.0.1:8080:8080",
        "0.0.0.0:8080:8080",
    ],
)
def test_port_explicit_mapping_is_passed_verbatim(spec, tmp_path, monkeypatch):
    """Explicit mappings (HOST:CONTAINER, IP::CONTAINER, IP:HOST:CONTAINER) pass directly."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--port", spec],
    )

    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == spec


def test_multiple_ports_are_published_in_order(tmp_path, monkeypatch):
    """Multiple --port / -P options produce corresponding -p flags in order."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
            "--port",
            "8080",
            "-P",
            "3000:3000",
            "--publish",
            "9000",
        ],
    )

    p_indices = [i for i, arg in enumerate(cmd) if arg == "-p"]
    assert len(p_indices) == 3
    assert [cmd[i + 1] for i in p_indices] == [
        "8080",
        "3000:3000",
        "9000",
    ]


def test_ports_from_config_file(tmp_path, monkeypatch):
    """Config `docker.ports` or `ports` publishes ports when no CLI flag is passed."""
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
            "docker": {"ports": [8080, "3000:3000"]},
        },
    )
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])
    assert result.exit_code == 0, result.output
    docker_cmd, _ = captured[0]

    p_indices = [i for i, arg in enumerate(docker_cmd) if arg == "-p"]
    assert len(p_indices) == 2
    assert [docker_cmd[i + 1] for i in p_indices] == [
        "8080",
        "3000:3000",
    ]


def test_cli_ports_override_config_ports(tmp_path, monkeypatch):
    """CLI --port overrides config ports entirely."""
    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
            "docker": {"ports": [8080]},
        },
    )
    captured = []

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "docker" and "run" in cmd[:2]:
            captured.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    result = CliRunner().invoke(
        cli.main,
        ["run", "claude", "-d", str(tmp_path / "repo"), "--port", "9090"],
    )
    assert result.exit_code == 0, result.output
    docker_cmd, _ = captured[0]

    p_indices = [i for i, arg in enumerate(docker_cmd) if arg == "-p"]
    assert len(p_indices) == 1
    assert docker_cmd[p_indices[0] + 1] == "9090"


# --------------------------------------------------------------------------
# --prompt composes with forwarded args
# --------------------------------------------------------------------------


def test_claude_prompt_option_keeps_forwarded_args(monkeypatch, tmp_path):
    """`--prompt` composes with forwarded args: the args reach claude verbatim
    and the prompt stays claude's trailing positional."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "claude",
            "-d",
            str(tmp_path / "repo"),
            "--prompt",
            "hello claude",
            "--verbose",
            "--model",
            "opus",
        ],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "claude",
        "--dangerously-skip-permissions",
        "--setting-sources=user,project",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        "opus",
        "hello claude",
    ]


def test_agy_prompt_option_keeps_forwarded_args(monkeypatch, tmp_path):
    """Same for agy, with --prompt last so nothing can consume its value."""
    cmd = _capture_docker_cmd(
        monkeypatch,
        tmp_path,
        [
            "run",
            "agy",
            "-d",
            str(tmp_path / "repo"),
            "--prompt",
            "hello agy",
            "--verbose",
            "--model",
            "opus",
        ],
    )
    inner = _inner_cmd(cmd)

    assert inner == [
        "agy",
        "--dangerously-skip-permissions",
        "--log-file",
        "/home/worker/.gemini/antigravity-cli/cli.log",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        "opus",
        "--prompt",
        "hello agy",
    ]


@pytest.mark.parametrize("agent_cmd", ["shell", "bash", "sleep", "some-other-tool"])
def test_prompt_is_rejected_for_commands_that_take_no_prompt(agent_cmd, monkeypatch, tmp_path):
    """bash and sleep have no prompt to receive. Silently dropping one surfaces
    later as a worker that never got its instructions, so it is rejected up
    front and no container starts."""
    result, captured = _invoke_capturing(
        monkeypatch,
        tmp_path,
        ["run", agent_cmd, "-d", str(tmp_path / "repo"), "--prompt", "hello there"],
    )

    assert result.exit_code != 0
    assert "--prompt has no meaning for AGENT_CMD" in result.output
    assert captured == [], "no container may start for an invocation that cannot work"
