#!/usr/bin/env python3
"""Tests for polecat CLI Docker-related functions.

Covers:
- NVM semver version sorting (_node_version_key)
- Docker command building (_build_docker_cmd)
- Worker environment construction (_make_worker_env)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from cli import (
    _build_docker_cmd,
    _clone_has_changes,
    _find_docker_sock,
    _format_oom_message,
    _is_colima_env,
    _node_version_key,
    _parse_memory_string,
    _replicate_gemini_auth,
    _resolve_docker_binary,
    _resolve_memory_limit,
)


class TestNodeVersionKey:
    """Tests for semver-aware NVM version sorting."""

    def test_standard_version(self):
        assert _node_version_key(Path("v20.11.1")) == (20, 11, 1)

    def test_single_digit_major(self):
        assert _node_version_key(Path("v9.11.2")) == (9, 11, 2)

    def test_no_v_prefix(self):
        assert _node_version_key(Path("18.0.0")) == (18, 0, 0)

    def test_non_version_dir(self):
        assert _node_version_key(Path("lts")) == (0, 0, 0)

    def test_v20_sorts_above_v9(self):
        """The bug this fixes: lexicographic sort puts v9 > v20."""
        dirs = [Path("v9.11.2"), Path("v20.11.1"), Path("v18.0.0")]
        result = sorted(dirs, key=_node_version_key, reverse=True)
        assert result[0] == Path("v20.11.1")
        assert result[1] == Path("v18.0.0")
        assert result[2] == Path("v9.11.2")

    def test_patch_version_ordering(self):
        dirs = [Path("v20.0.0"), Path("v20.0.1"), Path("v20.1.0")]
        result = sorted(dirs, key=_node_version_key, reverse=True)
        assert result[0] == Path("v20.1.0")
        assert result[1] == Path("v20.0.1")
        assert result[2] == Path("v20.0.0")


class TestBuildDockerCmd:
    """Tests for _build_docker_cmd Docker wrapper construction."""

    @pytest.fixture(autouse=True)
    def _patch_remote_daemon(self):
        """Force local-daemon (bind-mount) path so tests don't require Docker on PATH."""
        with patch("cli._is_remote_daemon", return_value=False):
            yield

    def _build(self, cli_tool="claude", env=None, agent_cmd=None, work_dir=None, cfg=None):
        docker_cmd = _build_docker_cmd(
            cli_tool=cli_tool,
            work_dir=work_dir or Path("/tmp/worktree"),
            env=env or {},
            agent_cmd=agent_cmd or ["claude", "--dangerously-skip-permissions"],
            is_interactive=False,
            cfg=cfg,
        )
        return docker_cmd.cmd

    def test_runs_as_current_user(self):
        cmd = self._build()
        idx = cmd.index("--user")
        uid_gid = cmd[idx + 1]
        assert uid_gid == f"{os.getuid()}:{os.getgid()}"

    def test_workspace_is_bind_mounted(self):
        """Workspace is bind-mounted rw into the container (local-daemon strategy)."""
        work_dir = Path("/tmp/test-worktree")
        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=work_dir,
            env={},
            agent_cmd=["claude", "--dangerously-skip-permissions"],
            is_interactive=False,
        )
        assert docker_cmd.workspace_dir == work_dir.resolve()
        vol_idx = [i for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
        volumes = [docker_cmd.cmd[i + 1] for i in vol_idx]
        expected = f"{work_dir.resolve()}:/workspace"
        assert expected in volumes, f"expected workspace bind-mount {expected} in {volumes}"
        assert "-w" in docker_cmd.cmd
        w_idx = docker_cmd.cmd.index("-w")
        assert docker_cmd.cmd[w_idx + 1] == "/workspace"

    def test_does_not_forward_anthropic_api_key(self):
        """ANTHROPIC_API_KEY must NOT be forwarded — Claude auth is OAuth-only
        per aops-06ab3ee0. A host with ANTHROPIC_API_KEY set should not leak it
        into the worker (and the env-map.conf entry was deliberately removed)."""
        env = {"ANTHROPIC_API_KEY": "sk-test-123"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        for arg in env_args:
            assert not arg.startswith("ANTHROPIC_API_KEY="), (
                f"ANTHROPIC_API_KEY must not be forwarded; got {arg}"
            )

    def test_forwards_claude_code_oauth_token(self):
        env = {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-test-token"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "CLAUDE_CODE_OAUTH_TOKEN=oauth-test-token" in env_args

    def test_does_not_forward_unlisted_keys(self):
        """Vars outside the conf allow-list (e.g. GOOGLE_API_KEY) are not forwarded.

        GEMINI_API_KEY is in agent-env-map.conf (forwarded for any cli_tool —
        harmless in claude containers). GOOGLE_API_KEY is not, so it must not
        leak into the container.
        """
        env = {"GEMINI_API_KEY": "gemini-test-key", "GOOGLE_API_KEY": "google-test-key"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any(a.startswith("GOOGLE_API_KEY=") for a in env_args)

    def test_forwards_polecat_prefixed_env(self):
        # The dispatcher's operational signals (aops-b368109a): AOPS_POLECAT_CONTAINER
        # (AOPS_ prefix) and POLECAT_CREW_NAME (POLECAT_ prefix) both forward.
        env = {"AOPS_POLECAT_CONTAINER": "1", "POLECAT_CREW_NAME": "test"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "AOPS_POLECAT_CONTAINER=1" in env_args
        assert "POLECAT_CREW_NAME=test" in env_args

    def test_does_not_forward_arbitrary_env(self):
        env = {"MY_SECRET": "leaked", "DATABASE_URL": "postgres://..."}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any("MY_SECRET" in a for a in env_args)
        assert not any("DATABASE_URL" in a for a in env_args)

    def test_polecat_yaml_not_staged_into_container(self, tmp_path):
        """polecat.yaml is NEVER staged into the container.

        The container reads no config file. The host resolves the config and
        injects only the values the container needs as env vars — here, the
        enabled-provider set (AOPS_ENABLED_PROVIDERS). The host's own
        AOPS_POLECAT_CONFIG path must NOT leak inward.
        """
        from lib.polecat_config import load_polecat_config

        p = tmp_path / "polecat.yaml"
        p.write_text(
            "session_defaults: {hooks_enabled: true, claude_model: m, gemini_model: gm, antigravity_model: g, "
            "debug: false, gates: {handover: warn, qa: warn, enforcer: warn, "
            "hydration: off, ida: warn, enforcer_threshold: 50}}\n"
            "crew_defaults: {}\nrun_defaults: {}\n"
            "docker: {image: ghcr.io/nicsuzor/aops-crew}\n"
            f"polecat_home: {tmp_path}\n"
            "external_agents: {github: {enabled: true}, codex: {enabled: false}}\n"
        )
        cfg = load_polecat_config(p)

        cmd = self._build(cfg=cfg)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any(a.startswith("AOPS_POLECAT_CONFIG=") for a in env_args)
        # Only the ENABLED provider is forwarded (codex is disabled).
        assert "AOPS_ENABLED_PROVIDERS=github" in env_args

    def test_forwards_aops_prefixed_env(self):
        """AOPS_* vars are forwarded (e.g. ACA_DATA, AOPS_SESSIONS)."""
        env = {"AOPS_SESSIONS": "/tmp/sessions", "AOPS_CUSTOM_VAR": "value"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/tmp/sessions" in env_args
        assert "AOPS_CUSTOM_VAR=value" in env_args

    def test_sets_timezone(self):
        """TZ is set in Docker env, detected from system when not in env."""
        with (
            patch.dict(os.environ, {"TZ": ""}),
            patch("cli._detect_system_timezone", return_value="US/Eastern"),
        ):
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        tz_args = [a for a in env_args if a.startswith("TZ=")]
        assert len(tz_args) == 1
        assert tz_args[0] == "TZ=US/Eastern"

    def test_timezone_from_env(self):
        """TZ can be overridden via environment variable."""
        with patch.dict(os.environ, {"TZ": "UTC"}):
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        tz_args = [a for a in env_args if a.startswith("TZ=")]
        assert tz_args[0] == "TZ=UTC"

    def test_sets_git_identity(self):
        """Git author/committer identity is set from agent-env-map.conf literals.

        The conf is the single source of truth — bot identity is fixed at
        polecat/aops-polecat regardless of host env. Container-level isolation
        ensures consistent commit attribution.
        """
        with patch.dict(os.environ):
            os.environ.pop("GIT_AUTHOR_NAME", None)
            os.environ.pop("GIT_AUTHOR_EMAIL", None)
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_AUTHOR_NAME=polecat" in env_args
        assert "GIT_AUTHOR_EMAIL=aops-polecat@users.noreply.github.com" in env_args
        assert "GIT_COMMITTER_NAME=aops-polecat" in env_args
        assert "GIT_COMMITTER_EMAIL=aops-polecat@users.noreply.github.com" in env_args

    def test_git_identity_not_overridable_via_host_env(self):
        """Conf literals win over host env — host can't override bot identity.

        Replaces test_git_identity_from_env (which encoded a footgun: the
        previous code's env-fallback meant a user with GIT_AUTHOR_NAME exported
        could attribute polecat-container commits to themselves). The conf
        ``:=`` literal is the SSoT.
        """
        with patch.dict(
            os.environ,
            {"GIT_AUTHOR_NAME": "custom-bot", "GIT_AUTHOR_EMAIL": "custom@example.com"},
        ):
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_AUTHOR_NAME=polecat" in env_args
        assert "GIT_AUTHOR_NAME=custom-bot" not in env_args
        assert "GIT_AUTHOR_EMAIL=aops-polecat@users.noreply.github.com" in env_args
        assert "GIT_AUTHOR_EMAIL=custom@example.com" not in env_args

    def test_ssh_isolation(self):
        """SSH fully blocked: agent cleared, command disabled, prompt off."""
        cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "SSH_AUTH_SOCK=" in env_args
        assert "GIT_SSH_COMMAND=false" in env_args
        assert "GIT_TERMINAL_PROMPT=0" in env_args

    def test_aops_bot_token_fans_out_to_gh_and_github(self):
        """AOPS_BOT_GH_TOKEN is the SSoT for git auth — fans out to GH_TOKEN,
        GITHUB_TOKEN, and AOPS_BOT_GH_TOKEN inside the container per the conf.
        GIT_ASKPASS=true is always-on (defence-in-depth, regardless of token).
        """
        env = {"AOPS_BOT_GH_TOKEN": "ghp_test123"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GH_TOKEN=ghp_test123" in env_args
        assert "GITHUB_TOKEN=ghp_test123" in env_args
        assert "AOPS_BOT_GH_TOKEN=ghp_test123" in env_args
        assert "GIT_ASKPASS=true" in env_args

    def test_git_askpass_always_on_even_without_token(self):
        """GIT_ASKPASS=true is forwarded unconditionally — no GH token required.

        Defence-in-depth: even if no token is present, the container must not
        be able to interactively prompt for git credentials.
        """
        cmd = self._build(env={})
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_ASKPASS=true" in env_args

    def test_passes_pkb_url_when_set(self):
        """PKB_MCP_URL is forwarded to the container."""
        env = {"PKB_MCP_URL": "http://host:8026/mcp"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "PKB_MCP_URL=http://host:8026/mcp" in env_args

    def test_no_brain_volume_mount(self, tmp_path):
        """ACA_DATA is NOT mounted — PKB uses HTTP now."""
        aca_dir = tmp_path / "brain"
        aca_dir.mkdir()
        env = {"ACA_DATA": str(aca_dir)}
        cmd = self._build(env=env)
        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        assert not any(str(aca_dir) in v for v in vol_args)

    def test_interactive_mode_sets_tty_flags(self):
        """Interactive mode sets both stdin and TTY flags (either split -i/-t or combined -it)."""
        docker_cmd = _build_docker_cmd(
            cli_tool="gemini",
            work_dir=Path("/tmp/worktree"),
            env={},
            agent_cmd=["gemini"],
            is_interactive=True,
        )
        cmd = docker_cmd.cmd
        has_stdin = "-i" in cmd or "-it" in cmd
        has_tty = "-t" in cmd or "-it" in cmd
        assert has_stdin, "stdin flag must be present (either -i or -it)"
        assert has_tty, "TTY flag must be present (either -t or -it)"

    def test_headless_mode_no_stdin_no_tty(self):
        """Headless mode gets neither -i (stdin) nor -t (TTY)."""
        cmd = self._build()
        assert "-i" not in cmd
        assert "-t" not in cmd

    def test_mounts_docker_socket_when_present(self, tmp_path):
        """Mounts host socket and adds --group-add when socket exists (DooD)."""
        sock = tmp_path / "docker.sock"
        sock.touch()
        env = {"DOCKER_HOST": f"unix://{sock}"}
        cmd = self._build(env=env)
        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        assert any("docker.sock" in v for v in vol_args)
        assert "--privileged" not in cmd
        assert "--user" in cmd

    # --- Empty-credential leak regression (task-ebc758fd) ---
    # Mirrors the spirit of test_shell_lines_skip_when_source_unset_or_empty
    # in test_credential_isolation.py: empty-string env vars must not be
    # forwarded into the container as `-e KEY=`.

    @pytest.mark.parametrize(
        "var",
        [
            "ANTHROPIC_API_KEY",
            "CLAUDE_CODE_OAUTH_TOKEN",
            "AOPS_BOT_GH_TOKEN",
            "GEMINI_API_KEY",
            "GEMINI_SESSION_ID",
            "POLECAT_FOO",
            "AOPS_BAR",
            "CUSTODIET_GATE_MODE",
        ],
    )
    def test_empty_env_var_not_forwarded(self, var):
        """Empty-string env vars must not leak into the container.

        The host shell exporting `ANTHROPIC_API_KEY=""` (or any other
        forwarded var) used to forward `-e ANTHROPIC_API_KEY=` and cause
        headless claude to send an empty x-api-key header → 401.
        """
        env = {var: ""}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        # No -e VAR=anything (empty or otherwise) for this var when source is empty.
        assert not any(a.startswith(f"{var}=") for a in env_args), (
            f"Empty {var} leaked into container: {[a for a in env_args if a.startswith(f'{var}=')]}"
        )

    @pytest.mark.parametrize(
        "var",
        [
            "ANTHROPIC_API_KEY",
            "CLAUDE_CODE_OAUTH_TOKEN",
            "AOPS_BOT_GH_TOKEN",
            "GEMINI_API_KEY",
            "GEMINI_SESSION_ID",
            "POLECAT_FOO",
            "AOPS_BAR",
        ],
    )
    def test_unset_env_var_not_forwarded(self, var):
        """Inverse boundary: unset (not in env at all) must also not forward."""
        cmd = self._build(env={})  # var not present
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any(a.startswith(f"{var}=") for a in env_args)

    def test_ssh_isolation_emits_empty_literal(self):
        """SSH_AUTH_SOCK="" literal forwards to container even when host has SSH_AUTH_SOCK set.

        The conf entry `SSH_AUTH_SOCK:=` (literal empty) is the deliberate
        isolation idiom: the container must NOT inherit a host SSH agent.
        """
        env = {"SSH_AUTH_SOCK": "/tmp/host-ssh-agent.sock"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "SSH_AUTH_SOCK=" in env_args
        assert "SSH_AUTH_SOCK=/tmp/host-ssh-agent.sock" not in env_args

    def test_gate_mode_env_vars_forwarded(self):
        """Gate modes are resolved from polecat.yaml on the host by the run /
        crew handlers (via ``_apply_gate_env``) and stamped into the env dict
        as plain env vars. ``_build_docker_cmd`` then forwards them into the
        container so hooks can read them directly without ever touching
        polecat.yaml.
        """
        env = {"HYDRATION_GATE_MODE": "off", "ENFORCER_GATE_MODE": "warn"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "HYDRATION_GATE_MODE=off" in env_args
        assert "ENFORCER_GATE_MODE=warn" in env_args

    @pytest.mark.parametrize("cli_tool", ["claude", "gemini"])
    def test_hook_log_and_gate_file_env_stamped_when_host_unset(self, cli_tool):
        """Issue #1196: polecat-run dispatched from cron has no host
        AOPS_HOOK_LOG_PATH / AOPS_GATE_FILE_ENFORCER. _build_docker_cmd must
        stamp placeholder paths inside the container session_state_dir so the
        in-container env (visible to `docker exec env` and to subprocesses
        running before SessionStart) has these vars set. Without this, the
        run path silently degraded vs the crew path (which inherited host
        values from an interactive Claude shell)."""
        from lib.session_paths import GATE_NAMES

        cmd = self._build(cli_tool=cli_tool, env={})
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]

        # AOPS_SESSION_STATE_DIR must be set first (anchor for the rest).
        state_dir_entries = [a for a in env_args if a.startswith("AOPS_SESSION_STATE_DIR=")]
        assert len(state_dir_entries) == 1, (
            f"Expected exactly one AOPS_SESSION_STATE_DIR entry, got: {state_dir_entries}"
        )
        state_dir = state_dir_entries[0].split("=", 1)[1]

        # Hook log path stamped, prefixed by the container session_state_dir.
        hook_log_entries = [a for a in env_args if a.startswith("AOPS_HOOK_LOG_PATH=")]
        assert len(hook_log_entries) == 1, (
            f"Expected AOPS_HOOK_LOG_PATH to be stamped, got: {hook_log_entries}"
        )
        assert hook_log_entries[0].startswith(f"AOPS_HOOK_LOG_PATH={state_dir}/")

        # Each gate name gets a gate-file env var.
        for gate in GATE_NAMES:
            key = f"AOPS_GATE_FILE_{gate.upper()}"
            gate_entries = [a for a in env_args if a.startswith(f"{key}=")]
            assert len(gate_entries) == 1, f"Expected {key} to be stamped, got: {gate_entries}"
            assert gate_entries[0].startswith(f"{key}={state_dir}/")

    @pytest.mark.parametrize("cli_tool", ["claude", "gemini"])
    def test_host_gate_file_and_hook_log_env_not_forwarded(self, cli_tool):
        """Host AOPS_GATE_FILE_* and AOPS_HOOK_LOG_PATH values must NOT be
        forwarded into the container.  These vars contain host-filesystem paths
        (e.g. /home/nic/...) that do not exist inside the container
        (/home/worker/...); forwarding them causes permission-denied errors in
        gate hooks and silently bypasses the gate mechanism (aops-d883c4ce).

        Container-local placeholder paths must always be stamped regardless of
        what the host env supplies.  The SessionStart hook later overrides the
        placeholders with session-id-anchored filenames."""
        from lib.session_paths import GATE_NAMES

        host_hook = "/home/user/.claude/projects/-w/20260522-1200-abcd-q-h-session-hooks.jsonl"
        host_gate = "/home/user/.claude/projects/-w/20260522-1200-abcd-q-h-session-enforcer.md"
        env = {
            "AOPS_HOOK_LOG_PATH": host_hook,
            **{f"AOPS_GATE_FILE_{g.upper()}": host_gate for g in GATE_NAMES},
        }
        cmd = self._build(cli_tool=cli_tool, env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]

        # Host value must NOT appear; container-local placeholder must be stamped.
        state_dir_entries = [a for a in env_args if a.startswith("AOPS_SESSION_STATE_DIR=")]
        assert len(state_dir_entries) == 1
        state_dir = state_dir_entries[0].split("=", 1)[1]

        hook_entries = [a for a in env_args if a.startswith("AOPS_HOOK_LOG_PATH=")]
        assert len(hook_entries) == 1, (
            f"Expected exactly one AOPS_HOOK_LOG_PATH, got: {hook_entries}"
        )
        assert hook_entries[0].startswith(f"AOPS_HOOK_LOG_PATH={state_dir}/"), (
            f"Expected container-local AOPS_HOOK_LOG_PATH, got: {hook_entries}"
        )
        assert host_hook not in hook_entries[0], (
            f"Host AOPS_HOOK_LOG_PATH must not be forwarded, got: {hook_entries}"
        )

        for gate in GATE_NAMES:
            key = f"AOPS_GATE_FILE_{gate.upper()}"
            gate_entries = [a for a in env_args if a.startswith(f"{key}=")]
            assert len(gate_entries) == 1, f"Expected exactly one {key}, got: {gate_entries}"
            assert gate_entries[0].startswith(f"{key}={state_dir}/"), (
                f"Expected container-local {key}, got: {gate_entries}"
            )
            assert host_gate not in gate_entries[0], (
                f"Host {key} must not be forwarded, got: {gate_entries}"
            )

    @pytest.mark.parametrize("cli_tool", ["claude", "gemini"])
    def test_gemini_api_key_forwarded_for_any_cli_tool(self, cli_tool):
        """GEMINI_API_KEY is conf-driven now — forwarded for any cli_tool.

        Harmless on the claude path (claude ignores it). The previous
        cli_tool-conditional forwarding was a structural-drift artifact.
        """
        env = {"GEMINI_API_KEY": "sk-g-test"}
        cmd = self._build(cli_tool=cli_tool, env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        gemini = [a for a in env_args if a.startswith("GEMINI_API_KEY=")]
        assert gemini == ["GEMINI_API_KEY=sk-g-test"], (
            f"Expected exactly one GEMINI_API_KEY entry for {cli_tool}, got {gemini}"
        )

    @pytest.mark.parametrize("cli_tool", ["claude", "gemini"])
    def test_gemini_cli_home_forwarded_when_set_for_any_cli_tool(self, cli_tool):
        """GEMINI_CLI_HOME is env-forwarded (not a literal) — only propagated
        when set in the parent env. Fix for #930: the old literal default
        `/home/worker` leaked into host sessions via SessionStart hooks.
        polecat/cli.py sets it explicitly per-launch for containers.
        """
        custom_home = "/tmp/test-gemini-home"
        cmd = self._build(cli_tool=cli_tool, env={"GEMINI_CLI_HOME": custom_home})
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert f"GEMINI_CLI_HOME={custom_home}" in env_args

    @pytest.mark.parametrize("cli_tool", ["claude", "gemini"])
    def test_gemini_cli_home_not_emitted_when_unset(self, cli_tool):
        """GEMINI_CLI_HOME is NOT forwarded when absent from parent env (fix #930).

        The literal default `/home/worker` is gone — polecat/cli.py sets it
        explicitly per-launch so the host SessionStart hook is unaffected.
        """
        cmd = self._build(cli_tool=cli_tool, env={})
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any(a.startswith("GEMINI_CLI_HOME=") for a in env_args)

    def test_all_conf_literals_appear_in_cmd(self):
        """Property test: every `:=` literal in agent-env-map.conf must appear
        as `-e TARGET=VALUE` in the cmd, regardless of source_env state.

        Future-proofs against anyone re-introducing a token-existence guard
        around any literal — the empty-string SSH_AUTH_SOCK isolation idiom
        is the most important case but the rule generalises.
        """
        from lib.agent_env import load_env_entries

        cmd = self._build(env={})
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        for entry in load_env_entries():
            if entry.is_literal:
                expected = f"{entry.target}={entry.value}"
                assert expected in env_args, (
                    f"Literal `{entry.target}:={entry.value}` from agent-env-map.conf "
                    f"must be forwarded; got env_args={env_args}"
                )

    def test_sessions_mount_via_flag(self, tmp_path, monkeypatch):
        """Verify sessions transcripts mount when with_sessions=True is passed."""
        sessions_dir = tmp_path / "sessions"
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=Path("/tmp/worktree"),
            env={},
            agent_cmd=["claude"],
            is_interactive=False,
            with_sessions=True,
        )

        env_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/sessions" in env_args

        vol_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
        expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"
        assert expected_mount in vol_args

    def test_sessions_mount_via_project(self, tmp_path, monkeypatch):
        """Verify sessions transcripts mount when project has sessions_access config."""
        sessions_dir = tmp_path / "sessions"
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

        from unittest.mock import MagicMock

        from polecat.manager import PolecatManager

        manager = MagicMock(spec=PolecatManager)
        manager.resolve_project_alias.side_effect = lambda slug: slug
        manager.projects = {
            "myproj": {
                "sessions_access": True,
                "mounts": [],
            }
        }

        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=Path("/tmp/worktree"),
            env={},
            agent_cmd=["claude"],
            is_interactive=False,
            project_slug="myproj",
            manager=manager,
        )

        env_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/sessions" in env_args

        vol_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
        expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"
        assert expected_mount in vol_args

    def test_sessions_mount_via_project_singular(self, tmp_path, monkeypatch):
        """Verify sessions transcripts mount when project has session_access config (singular spelling)."""
        sessions_dir = tmp_path / "sessions"
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

        from unittest.mock import MagicMock

        from polecat.manager import PolecatManager

        manager = MagicMock(spec=PolecatManager)
        manager.resolve_project_alias.side_effect = lambda slug: slug
        manager.projects = {
            "myproj": {
                "session_access": True,
                "mounts": [],
            }
        }

        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=Path("/tmp/worktree"),
            env={},
            agent_cmd=["claude"],
            is_interactive=False,
            project_slug="myproj",
            manager=manager,
        )

        env_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/sessions" in env_args

        vol_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
        expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"
        assert expected_mount in vol_args

    def test_sessions_mount_not_present_by_default(self, tmp_path, monkeypatch):
        """Verify sessions transcripts are NOT mounted by default."""
        sessions_dir = tmp_path / "sessions"
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=Path("/tmp/worktree"),
            env={},
            agent_cmd=["claude"],
            is_interactive=False,
        )

        env_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/sessions" not in env_args

        vol_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
        expected_mount_prefix = f"{(sessions_dir / 'transcripts').resolve()}:"
        assert not any(v.startswith(expected_mount_prefix) for v in vol_args)

    def test_sessions_mount_remote_daemon(self, tmp_path, monkeypatch):
        """Verify sessions mount is skipped on remote daemons, but env var is still set."""
        sessions_dir = tmp_path / "sessions"
        monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

        with patch("cli._is_remote_daemon", return_value=True):
            docker_cmd = _build_docker_cmd(
                cli_tool="claude",
                work_dir=Path("/tmp/worktree"),
                env={},
                agent_cmd=["claude"],
                is_interactive=False,
                with_sessions=True,
            )

            env_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-e"]
            assert "AOPS_SESSIONS=/sessions" in env_args

            vol_args = [docker_cmd.cmd[i + 1] for i, x in enumerate(docker_cmd.cmd) if x == "-v"]
            expected_mount = f"{(sessions_dir / 'transcripts').resolve()}:/sessions/transcripts:ro"
            assert expected_mount not in vol_args


class TestClaudeAuthEnvOnly:
    """Claude auth must be env-var only: no `.claude.json`/`.credentials.json`/
    `settings.json` staging from the host. See aops-06ab3ee0."""

    @pytest.fixture(autouse=True)
    def _patch_remote_daemon(self):
        with patch("cli._is_remote_daemon", return_value=False):
            yield

    def test_no_claude_auth_files_staged(self, tmp_path):
        """Host `.claude.json`, `.claude/.credentials.json`, and
        `.claude/settings.json` must NOT be copied into the staging dir."""
        # Seed all three host files that the old code path would have staged.
        (tmp_path / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"emailAddress": "host@example.com"}})
        )
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".credentials.json").write_text('{"token": "host-token"}')
        (claude_dir / "settings.json").write_text("{}")

        with patch("cli.Path.home", return_value=tmp_path):
            docker_cmd = _build_docker_cmd(
                cli_tool="claude",
                work_dir=Path("/tmp/worktree"),
                env={},
                agent_cmd=["claude", "--dangerously-skip-permissions"],
                is_interactive=False,
            )

        assert docker_cmd.staging_dir is not None
        # None of the host auth files should appear in the staging dir.
        assert not (docker_cmd.staging_dir / ".claude.json").exists(), (
            "staged .claude.json leaked host auth — must be env-var only"
        )
        assert not (docker_cmd.staging_dir / ".claude" / ".credentials.json").exists(), (
            "staged .credentials.json leaked host auth — must be env-var only"
        )
        assert not (docker_cmd.staging_dir / ".claude" / "settings.json").exists(), (
            "staged settings.json leaked host config — must be env-var only"
        )


class TestClaudeConfigSeed:
    """The baked-in `.claude.json` seed must skip onboarding AND folder-trust.

    The Dockerfile copies polecat/defaults/claude-config.json to /home/worker/.claude.json
    in the image. Without the per-project hasTrustDialogAccepted flag, recent Claude Code
    releases prompt for folder trust on the first interactive turn — and plugins
    (aops-core@academicOps) are gated behind that acceptance, so framework hooks/skills
    silently don't load until the user clicks Trust.

    Field name parallel to the host's freshly-trusted .claude.json — verified against a
    live trusted host file, not guessed. See aops-542d82d4.
    """

    SEED_PATH = Path(__file__).parent.parent.parent / "polecat" / "defaults" / "claude-config.json"
    CONTAINER_WORKDIR = "/workspace"

    def test_seed_exists(self):
        assert self.SEED_PATH.exists(), f"claude-config.json seed missing at {self.SEED_PATH}"

    def test_seed_skips_onboarding(self):
        """Regression guard: onboarding must remain skipped (existing behaviour)."""
        seed = json.loads(self.SEED_PATH.read_text())
        assert seed.get("hasCompletedOnboarding") is True
        assert seed.get("bypassPermissionsModeAccepted") is True

    def test_seed_has_oauth_account(self):
        """oauthAccount must be present to suppress the OAuth paste-back prompt.

        Claude Code checks for oauthAccount in .claude.json to determine whether
        an account has been previously configured. Without it, even when
        CLAUDE_CODE_OAUTH_TOKEN is set in the environment, the interactive REPL
        presents the first-run OAuth paste-back flow. The placeholder values are
        display metadata only — actual auth uses CLAUDE_CODE_OAUTH_TOKEN. See
        GitHub issue #938 and commit 7b4365bd (env-only auth migration).
        """
        seed = json.loads(self.SEED_PATH.read_text())
        oauth_account = seed.get("oauthAccount")
        assert oauth_account is not None, (
            "seed must have oauthAccount to suppress the Claude Code OAuth "
            "paste-back prompt in interactive REPL mode (issue #938)"
        )
        assert isinstance(oauth_account.get("accountUuid"), str), (
            "oauthAccount.accountUuid must be a string"
        )
        assert isinstance(oauth_account.get("emailAddress"), str), (
            "oauthAccount.emailAddress must be a string"
        )

    def test_seed_accepts_workspace_trust(self):
        """New behaviour: /workspace must be pre-trusted so plugins load on first turn.

        Field set matches a freshly-trusted host project entry (verified
        against /home/nic/brain in ~/.claude.json after clicking Trust).
        Claude Code v2.1.146 triggers project-onboarding on the first
        interactive launch — which itself includes a trust prompt — even
        when hasTrustDialogAccepted is true. Seeding the full set
        suppresses every interactive gate observed on the host.
        """
        seed = json.loads(self.SEED_PATH.read_text())
        projects = seed.get("projects", {})
        workspace = projects.get(self.CONTAINER_WORKDIR)
        assert workspace is not None, (
            f"seed must pre-populate projects['{self.CONTAINER_WORKDIR}'] "
            f"to bypass the Claude Code folder-trust prompt"
        )
        required = {
            "hasTrustDialogAccepted": True,
            "hasCompletedProjectOnboarding": True,
            "hasClaudeMdExternalIncludesApproved": True,
            "hasClaudeMdExternalIncludesWarningShown": True,
        }
        for key, expected in required.items():
            assert workspace.get(key) is expected, (
                f"projects['/workspace'].{key} must be {expected!r} to "
                f"suppress the corresponding interactive gate. Got: {workspace.get(key)!r}"
            )


class TestRequireClaudeOauth:
    """Pre-flight: polecat must fail fast when CLAUDE_CODE_OAUTH_TOKEN is unset."""

    def test_exits_when_oauth_token_missing_for_claude(self, monkeypatch, capsys, tmp_path):
        from cli import _require_claude_oauth_or_exit

        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.delenv("AOPS_CC_OAUTH_TOKEN", raising=False)
        # Isolate the host secret store too: resolve_forward_values reads
        # ~/.env.local (the authoritative source) before the process env, so a
        # real token on the dev host would mask the "missing" case. Point
        # AOPS_HOST_ENV_FILE at a nonexistent file so load_host_secrets is empty.
        monkeypatch.setenv("AOPS_HOST_ENV_FILE", str(tmp_path / "no-env-local"))
        with pytest.raises(SystemExit) as excinfo:
            _require_claude_oauth_or_exit("claude")
        assert excinfo.value.code == 4
        stderr = capsys.readouterr().err
        assert "CLAUDE_CODE_OAUTH_TOKEN" in stderr
        assert "claude setup-token" in stderr

    def test_passes_when_oauth_token_set_for_claude(self, monkeypatch):
        from cli import _require_claude_oauth_or_exit

        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake-token")
        # Must return None without raising.
        assert _require_claude_oauth_or_exit("claude") is None

    def test_noop_for_gemini(self, monkeypatch):
        from cli import _require_claude_oauth_or_exit

        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        # Gemini path must not be gated on Claude token.
        assert _require_claude_oauth_or_exit("gemini") is None

    def test_noop_for_shell(self, monkeypatch):
        from cli import _require_claude_oauth_or_exit

        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        # Shell mode (interactive) doesn't run an autonomous claude worker.
        assert _require_claude_oauth_or_exit("shell") is None


class TestFindDockerSock:
    """Live tests for _find_docker_sock — no mocking, real filesystem paths in tmp_path."""

    def test_returns_none_when_no_socket_anywhere(self, tmp_path, monkeypatch):
        """No socket file → None (DooD skipped gracefully)."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        result = _find_docker_sock({}, home=tmp_path)
        assert result is None

    def test_docker_host_unix_socket_found(self, tmp_path):
        """DOCKER_HOST=unix://... with existing file → that path is returned."""
        sock = tmp_path / "custom.sock"
        sock.touch()
        result = _find_docker_sock({"DOCKER_HOST": f"unix://{sock}"}, home=tmp_path)
        assert result is not None
        assert result.mount_source == sock
        assert result.host_path == sock

    def test_docker_host_colima_unix_socket(self, tmp_path):
        """DOCKER_HOST pointing to a Colima socket → mount_source is /var/run/docker.sock."""
        colima = tmp_path / ".colima" / "default"
        colima.mkdir(parents=True)
        sock = colima / "docker.sock"
        sock.touch()
        result = _find_docker_sock({"DOCKER_HOST": f"unix://{sock}"}, home=tmp_path)
        assert result is not None
        assert result.mount_source == Path("/var/run/docker.sock")
        assert result.host_path == sock

    def test_docker_host_unix_socket_missing(self, tmp_path):
        """DOCKER_HOST=unix://... pointing at a nonexistent file → None (not a fallback)."""
        result = _find_docker_sock({"DOCKER_HOST": f"unix://{tmp_path}/ghost.sock"}, home=tmp_path)
        assert result is None

    def test_docker_host_tcp_skips_local_probe(self, tmp_path):
        """DOCKER_HOST=tcp://... → None even when local Colima sockets exist."""
        colima = tmp_path / ".colima" / "default"
        colima.mkdir(parents=True)
        (colima / "docker.sock").touch()
        result = _find_docker_sock({"DOCKER_HOST": "tcp://remote:2375"}, home=tmp_path)
        assert result is None

    def test_env_dict_takes_precedence_over_os_environ(self, tmp_path, monkeypatch):
        """DOCKER_HOST in env dict is used even when os.environ has a different value."""
        env_sock = tmp_path / "env-dict.sock"
        env_sock.touch()
        os_sock = tmp_path / "os-environ.sock"
        os_sock.touch()
        monkeypatch.setenv("DOCKER_HOST", f"unix://{os_sock}")
        result = _find_docker_sock({"DOCKER_HOST": f"unix://{env_sock}"}, home=tmp_path)
        assert result is not None
        assert result.mount_source == env_sock
        assert result.host_path == env_sock

    def test_colima_default_profile(self, tmp_path, monkeypatch):
        """Falls back to ~/.colima/default/docker.sock when DOCKER_HOST unset.
        Colima paths use /var/run/docker.sock as mount_source (VM-internal)."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        colima = tmp_path / ".colima" / "default"
        colima.mkdir(parents=True)
        sock = colima / "docker.sock"
        sock.touch()
        result = _find_docker_sock({}, home=tmp_path)
        assert result is not None
        assert result.mount_source == Path("/var/run/docker.sock")
        assert result.host_path == sock

    def test_colima_legacy_path(self, tmp_path, monkeypatch):
        """Falls back to ~/.colima/docker.sock when default profile is absent."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        colima = tmp_path / ".colima"
        colima.mkdir(parents=True)
        sock = colima / "docker.sock"
        sock.touch()
        result = _find_docker_sock({}, home=tmp_path)
        assert result is not None
        assert result.mount_source == Path("/var/run/docker.sock")
        assert result.host_path == sock

    def test_colima_default_preferred_over_legacy(self, tmp_path, monkeypatch):
        """default/docker.sock wins over legacy docker.sock when both exist."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        (tmp_path / ".colima" / "default").mkdir(parents=True)
        (tmp_path / ".colima").mkdir(parents=True, exist_ok=True)
        default_sock = tmp_path / ".colima" / "default" / "docker.sock"
        legacy_sock = tmp_path / ".colima" / "docker.sock"
        default_sock.touch()
        legacy_sock.touch()
        result = _find_docker_sock({}, home=tmp_path)
        assert result is not None
        assert result.mount_source == Path("/var/run/docker.sock")
        assert result.host_path == default_sock

    @pytest.mark.skipif(
        not Path("/var/run/docker.sock").exists(),
        reason="/var/run/docker.sock not present on this host",
    )
    def test_standard_linux_sock_found_in_production_mode(self, monkeypatch):
        """Production mode (home=None) picks up /var/run/docker.sock on Linux/CI."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        # Production call — no home override, so /var/run/docker.sock is in the probe list.
        result = _find_docker_sock({})
        assert result is not None
        assert "docker.sock" in str(result.mount_source)


class TestResolveDockerBinary:
    """Tests for _resolve_docker_binary fallback chain.

    Regression suite for task-1929bf59 (and prior task-dff66ab3): ``pc run``
    must locate ``docker`` even when the worker subprocess env's PATH does not
    contain it. The fallback chain is env PATH → os.environ PATH → common
    install locations on macOS/Linux.
    """

    def test_uses_env_path_first(self, tmp_path):
        """When env PATH contains docker, it wins over os.environ and fallbacks."""
        env_bin = tmp_path / "env_bin"
        env_bin.mkdir()
        docker_in_env = env_bin / "docker"
        docker_in_env.write_text("#!/bin/sh\n")
        docker_in_env.chmod(0o755)

        with patch.dict(os.environ, {"PATH": "/nonexistent/path"}, clear=False):
            result = _resolve_docker_binary({"PATH": str(env_bin)})
        assert result == str(docker_in_env)

    def test_falls_back_to_os_environ_path(self, tmp_path):
        """When env's PATH lacks docker but os.environ has it, use os.environ."""
        os_bin = tmp_path / "os_bin"
        os_bin.mkdir()
        docker_in_os = os_bin / "docker"
        docker_in_os.write_text("#!/bin/sh\n")
        docker_in_os.chmod(0o755)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with (
            patch.dict(os.environ, {"PATH": str(os_bin)}, clear=True),
            patch("cli._DOCKER_BINARY_FALLBACK_PATHS", ()),
        ):
            result = _resolve_docker_binary({"PATH": str(empty_dir)})
        assert result == str(docker_in_os)

    def test_falls_back_to_install_locations(self, tmp_path):
        """When neither env nor os.environ have docker, probe install locations.

        This is the regression that produced ``'claude' command not found`` on
        the user's MacBook (task-1929bf59): docker was at ``/usr/local/bin/docker``
        but the subprocess env PATH didn't include it.
        """
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        fallback_docker = tmp_path / "fallback_bin" / "docker"
        fallback_docker.parent.mkdir()
        fallback_docker.write_text("#!/bin/sh\n")
        fallback_docker.chmod(0o755)

        with (
            patch.dict(os.environ, {"PATH": str(empty_dir)}, clear=True),
            patch("cli._DOCKER_BINARY_FALLBACK_PATHS", (str(fallback_docker),)),
        ):
            result = _resolve_docker_binary({"PATH": str(empty_dir)})
        assert result == str(fallback_docker)

    def test_returns_literal_docker_when_unresolvable(self, tmp_path):
        """When no path works, return ``"docker"`` so the caller fails with a clear error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with (
            patch.dict(os.environ, {"PATH": str(empty_dir)}, clear=True),
            patch("cli._DOCKER_BINARY_FALLBACK_PATHS", ()),
        ):
            result = _resolve_docker_binary({"PATH": str(empty_dir)})
        assert result == "docker"

    def test_no_env_uses_os_environ(self, tmp_path):
        """When env=None, look up docker via os.environ PATH."""
        os_bin = tmp_path / "os_bin"
        os_bin.mkdir()
        docker_in_os = os_bin / "docker"
        docker_in_os.write_text("#!/bin/sh\n")
        docker_in_os.chmod(0o755)

        with patch.dict(os.environ, {"PATH": str(os_bin)}, clear=True):
            result = _resolve_docker_binary(None)
        assert result == str(docker_in_os)

    def test_skips_non_executable_fallback(self, tmp_path):
        """A fallback path that exists but is not executable is skipped."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        non_exec = tmp_path / "not-exec" / "docker"
        non_exec.parent.mkdir()
        non_exec.write_text("#!/bin/sh\n")
        non_exec.chmod(0o644)  # Not executable

        with (
            patch.dict(os.environ, {"PATH": str(empty_dir)}, clear=True),
            patch("cli._DOCKER_BINARY_FALLBACK_PATHS", (str(non_exec),)),
        ):
            result = _resolve_docker_binary({"PATH": str(empty_dir)})
        assert result == "docker"


class TestBuildDockerCmdResolvesBinary:
    """_build_docker_cmd must produce a docker command with an absolute binary
    path so the eventual ``subprocess.run(..., env=env)`` cannot trip over a
    sanitised env's PATH (regression of task-dff66ab3 / task-1929bf59)."""

    @pytest.fixture(autouse=True)
    def _patch_remote_daemon(self):
        with patch("cli._is_remote_daemon", return_value=False):
            yield

    def test_first_arg_is_resolved_path_when_resolver_finds_docker(self, tmp_path):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        docker_bin = bin_dir / "docker"
        docker_bin.write_text("#!/bin/sh\n")
        docker_bin.chmod(0o755)

        with patch("cli._resolve_docker_binary", return_value=str(docker_bin)):
            docker_cmd = _build_docker_cmd(
                cli_tool="claude",
                work_dir=Path("/tmp/worktree"),
                env={},
                agent_cmd=["claude", "--dangerously-skip-permissions"],
                is_interactive=False,
            )
        assert docker_cmd.cmd[0] == str(docker_bin)
        # Sanity check: the rest of the command is unchanged.
        assert docker_cmd.cmd[1:3] == ["run", "--rm"]


class TestMakeWorkerEnv:
    """Tests for _make_worker_env environment construction."""

    def test_nvm_semver_sort_in_path(self, tmp_path):
        """When NVM_DIR has multiple versions, highest semver wins in PATH."""
        nvm_dir = tmp_path / ".nvm"
        versions_dir = nvm_dir / "versions" / "node"
        # Create version dirs — v9 would win lexicographically but v20 should win
        for v in ["v9.11.2", "v18.0.0", "v20.11.1"]:
            (versions_dir / v / "bin").mkdir(parents=True)

        with (
            patch.dict(os.environ, {"NVM_DIR": str(nvm_dir)}, clear=False),
            patch.dict(os.environ, {"NVM_BIN": ""}, clear=False),
        ):
            from cli import _make_worker_env

            env = _make_worker_env()

        # v20.11.1 bin should be in PATH, not v9.11.2
        assert str(versions_dir / "v20.11.1" / "bin") in env["PATH"]
        assert str(versions_dir / "v9.11.2" / "bin") not in env["PATH"]

    def test_gh_prompt_disabled(self):
        from cli import _make_worker_env

        env = _make_worker_env()
        assert env.get("GH_PROMPT_DISABLED") == "1"


class TestDetectSystemTimezone:
    """Tests for _detect_system_timezone."""

    def test_from_localtime_symlink(self):
        from cli import _detect_system_timezone

        mock_localtime = type(
            "MockPath",
            (),
            {
                "is_symlink": lambda self: True,
                "resolve": lambda self: Path("/usr/share/zoneinfo/Europe/London"),
            },
        )()
        mock_no_timezone = type("MockPath", (), {"exists": lambda self: False})()

        def path_factory(p):
            if p == "/etc/localtime":
                return mock_localtime
            if p == "/etc/timezone":
                return mock_no_timezone
            return Path(p)

        with patch("cli.Path", side_effect=path_factory):
            result = _detect_system_timezone()
        assert result == "Europe/London"

    def test_fallback_to_utc(self):
        from cli import _detect_system_timezone

        mock_path = type(
            "MockPath",
            (),
            {"is_symlink": lambda self: False, "exists": lambda self: False},
        )()
        with patch("cli.Path", side_effect=lambda p: mock_path):
            result = _detect_system_timezone()
        assert result == "UTC"


class TestReplicateGeminiAuth:
    """Tests for _replicate_gemini_auth extension replication."""

    def test_extensions_are_copied_not_symlinked(self, tmp_path):
        """Extensions must be copied (not symlinked) because symlinks break inside Docker.

        Bug: symlinks to host paths (e.g. /home/debian/.gemini/extensions/aops-core)
        don't resolve inside Docker containers, causing 'no extensions installed'.
        """
        # Create fake gemini home with extensions
        gemini_dir = tmp_path / ".gemini"
        ext_dir = gemini_dir / "extensions" / "aops-core"
        ext_dir.mkdir(parents=True)
        (ext_dir / "GEMINI.md").write_text("extension content")
        (ext_dir / "hooks").mkdir()
        (ext_dir / "hooks" / "router.sh").write_text("#!/bin/bash")

        # Create enablement file
        enablement = {"aops-core": {"overrides": ["/home/user/*"]}}
        (gemini_dir / "extensions" / "extension-enablement.json").write_text(json.dumps(enablement))

        # Create auth file so the function doesn't bail early
        (gemini_dir / "settings.json").write_text("{}")

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None

        # Verify extensions were COPIED, not symlinked
        replicated_ext = result / ".gemini" / "extensions" / "aops-core"
        assert replicated_ext.exists()
        assert not replicated_ext.is_symlink(), "Extension should be copied, not symlinked"
        assert (replicated_ext / "GEMINI.md").read_text() == "extension content"
        assert (replicated_ext / "hooks" / "router.sh").read_text() == "#!/bin/bash"

        # Clean up
        import shutil

        shutil.rmtree(result)

    def test_enablement_overrides_are_wildcarded(self, tmp_path):
        """Extension enablement overrides should be set to '*' for any workspace path."""
        gemini_dir = tmp_path / ".gemini"
        ext_dir = gemini_dir / "extensions" / "aops-core"
        ext_dir.mkdir(parents=True)
        (ext_dir / "GEMINI.md").write_text("content")

        enablement = {"aops-core": {"overrides": ["/home/user/*"]}}
        (gemini_dir / "extensions" / "extension-enablement.json").write_text(json.dumps(enablement))
        (gemini_dir / "settings.json").write_text("{}")

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        enablement_file = result / ".gemini" / "extensions" / "extension-enablement.json"
        assert enablement_file.exists()
        data = json.loads(enablement_file.read_text())
        assert data["aops-core"]["overrides"] == ["*"]

        import shutil

        shutil.rmtree(result)

    def test_replicates_policies(self, tmp_path):
        """Replicates all policy TOML files to the sandbox auth home."""
        gemini_dir = tmp_path / ".gemini"
        policies_dir = gemini_dir / "policies"
        policies_dir.mkdir(parents=True)

        (gemini_dir / "settings.json").write_text("{}")
        (policies_dir / "rule1.toml").write_text("# policy 1")
        (policies_dir / "rule2.toml").write_text("# policy 2")
        # Non-toml files should be ignored
        (policies_dir / "ignore.me").write_text("not a policy")

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None
        dst_policies = result / ".gemini" / "policies"
        assert dst_policies.is_dir()
        assert (dst_policies / "rule1.toml").read_text() == "# policy 1"
        assert (dst_policies / "rule2.toml").read_text() == "# policy 2"
        assert not (dst_policies / "ignore.me").exists()

        import shutil

        shutil.rmtree(result)

    def test_replicated_settings_is_minimal(self, tmp_path):
        """Replicated settings.json uses controlled template, not user settings.

        User baggage (MCP servers, UI prefs, auth selectedType, shell config)
        must not leak into sandbox sessions. The template provides only
        hooksConfig.enabled — no auth type (let Gemini auto-detect), no sandbox
        settings, no user preferences.
        """
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)

        settings = {
            "security": {"auth": {"selectedType": "oauth-personal"}},
            "tools": {"shell": {"showColor": True}},
            "mcpServers": {
                "playwright": {"command": "npx", "args": ["playwright"]},
            },
            "ui": {"showCitations": True},
            "hooks": {"some_hook": {}},
        }
        (gemini_dir / "settings.json").write_text(json.dumps(settings))

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None
        replicated = json.loads((result / ".gemini" / "settings.json").read_text())

        # Hooks explicitly enabled
        assert replicated["hooksConfig"]["enabled"] is True
        # No auth selectedType (Gemini auto-detects — avoids auth mismatch crash).
        # security.policyEngine is allowed (template-defined); security.auth must not leak.
        assert replicated.get("security", {}).get("auth") is None
        # User baggage stripped
        assert "mcpServers" not in replicated
        assert "ui" not in replicated
        assert "hooks" not in replicated

        import shutil

        shutil.rmtree(result)

    def test_missing_auth_type_still_writes_settings(self, tmp_path):
        """Settings.json is always written from template, regardless of user settings."""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)

        # Settings with no auth type — template should still be written
        (gemini_dir / "settings.json").write_text(json.dumps({"tools": {}}))

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None
        # settings.json should exist — written from template
        assert (result / ".gemini" / "settings.json").exists()
        replicated = json.loads((result / ".gemini" / "settings.json").read_text())
        assert replicated["hooksConfig"]["enabled"] is True

        import shutil

        shutil.rmtree(result)

    def test_corrupt_settings_still_writes_template(self, tmp_path):
        """Even with corrupt user settings, template is written."""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)

        (gemini_dir / "settings.json").write_text("not valid json{{{")

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None
        # settings.json should exist — written from template (user settings irrelevant)
        assert (result / ".gemini" / "settings.json").exists()

        import shutil

        shutil.rmtree(result)

    def test_replicated_dir_writable_by_other_uid(self, tmp_path):
        """Replicated auth dir must be accessible by a different UID (sandbox container).

        Gemini's --sandbox mounts GEMINI_CLI_HOME into a Docker container that
        runs as a different UID. The container writes temp files like
        projects.json.tmp, so dirs must be world-writable and files readable.
        """
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)

        # Create auth files with restrictive source permissions (like real ~/.gemini)
        (gemini_dir / "settings.json").write_text("{}")
        (gemini_dir / "oauth_creds.json").write_text("{}")
        os.chmod(gemini_dir / "oauth_creds.json", 0o600)

        env = {}
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth(env)

        assert result is not None

        # Parent dir must be traversable
        parent_mode = os.stat(result).st_mode & 0o777
        assert parent_mode & 0o005, f"Parent dir not world-readable: {oct(parent_mode)}"

        # .gemini dir must be world-writable (container writes projects.json.tmp)
        gemini_mode = os.stat(result / ".gemini").st_mode & 0o777
        assert gemini_mode & 0o007 == 0o007, f".gemini dir not world-rwx: {oct(gemini_mode)}"

        # Auth files must be world-readable (container reads oauth_creds.json)
        for f in (result / ".gemini").iterdir():
            if f.is_file():
                fmode = os.stat(f).st_mode & 0o777
                assert fmode & 0o004, f"{f.name} not world-readable: {oct(fmode)}"

        import shutil

        shutil.rmtree(result)

    def test_workspace_added_to_existing_trusted_folders(self, tmp_path):
        """/workspace is injected into an existing trustedFolders.json."""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        (gemini_dir / "settings.json").write_text("{}")
        existing = {"/home/user/project": "TRUST_FOLDER"}
        (gemini_dir / "trustedFolders.json").write_text(json.dumps(existing))

        work_dir = tmp_path / "project"
        work_dir.mkdir()
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth({}, work_dir=work_dir)

        assert result is not None
        trust = json.loads((result / ".gemini" / "trustedFolders.json").read_text())
        assert trust.get("/workspace") == "TRUST_FOLDER"

        import shutil

        shutil.rmtree(result)

    def test_workspace_added_when_trusted_folders_created(self, tmp_path):
        """/workspace is included when trustedFolders.json is created from scratch."""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True)
        (gemini_dir / "settings.json").write_text("{}")

        work_dir = tmp_path / "project"
        work_dir.mkdir()
        with patch("cli.Path.home", return_value=tmp_path):
            result = _replicate_gemini_auth({}, work_dir=work_dir)

        assert result is not None
        trust = json.loads((result / ".gemini" / "trustedFolders.json").read_text())
        assert trust.get("/workspace") == "TRUST_FOLDER"
        assert trust.get(str(work_dir.resolve())) == "TRUST_FOLDER"

        import shutil

        shutil.rmtree(result)


class TestCloneHasChanges:
    """Tests for _clone_has_changes — used for auto-nuke of crew with no work."""

    BRANCH = "crew/test"

    def _init_repo_with_remote(self, path):
        """Create a git repo with a real local bare remote (required for ls-remote)."""
        remote = path / "origin.git"
        remote.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=remote, check=True, capture_output=True)

        repo = path / "repo"
        repo.mkdir()
        for cmd in [
            ["git", "init"],
            ["git", "config", "user.email", "test@test"],
            ["git", "config", "user.name", "Test"],
            ["git", "remote", "add", "origin", str(remote)],
        ]:
            subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
        (repo / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "push", "origin", "HEAD:main"], cwd=repo, check=True, capture_output=True
        )
        subprocess.run(["git", "fetch", "origin"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    def test_no_changes_no_remote_branch_returns_false(self, tmp_path):
        """No remote crew branch exists — nothing was pushed, safe to nuke."""
        repo = self._init_repo_with_remote(tmp_path)
        # crew/test not on remote → ls-remote returns empty → False
        assert _clone_has_changes(repo, self.BRANCH) is False

    def test_uncommitted_changes_returns_true(self, tmp_path):
        """Local uncommitted changes → preserve (detected before remote check)."""
        repo = self._init_repo_with_remote(tmp_path)
        (repo / "new_file.txt").write_text("uncommitted")
        assert _clone_has_changes(repo, self.BRANCH) is True

    def test_pushed_commits_returns_true(self, tmp_path):
        """Remote crew branch has commits not in main → preserve.

        This is the Docker case: local clone may be stale (no local commits),
        but the agent pushed real work to origin/crew/test.
        """
        repo = self._init_repo_with_remote(tmp_path)
        (repo / "new_file.txt").write_text("committed and pushed")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "new work"], cwd=repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", f"HEAD:{self.BRANCH}"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        assert _clone_has_changes(repo, self.BRANCH) is True

    def test_remote_branch_merged_returns_false(self, tmp_path):
        """Remote crew branch exists but its commits are already in main → nuke."""
        repo = self._init_repo_with_remote(tmp_path)
        # Push crew/test at the same commit as main (merged or never diverged)
        subprocess.run(
            ["git", "push", "origin", f"HEAD:{self.BRANCH}"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        assert _clone_has_changes(repo, self.BRANCH) is False

    def test_squash_merged_returns_false(self, tmp_path):
        """Branch has commits beyond main but identical content (squash-merge) → nuke."""
        repo = self._init_repo_with_remote(tmp_path)
        # Create and push a crew/test commit
        (repo / "feature.txt").write_text("feature work")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feature"], cwd=repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", f"HEAD:{self.BRANCH}"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        # Squash merge: create a new main commit with the same tree (same content, different SHA)
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        parent = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        squash = subprocess.run(
            ["git", "commit-tree", tree, "-p", parent, "-m", "squash: feature"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "push", "origin", f"{squash}:refs/heads/main", "--force"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        assert _clone_has_changes(repo, self.BRANCH) is False

    def test_nonexistent_path_returns_true(self, tmp_path):
        """Safe default: if path doesn't exist, assume changes (don't auto-nuke)."""
        assert _clone_has_changes(tmp_path / "nonexistent", self.BRANCH) is True


# ---------------------------------------------------------------------------
# Docker memory management
# ---------------------------------------------------------------------------


class TestParseMemoryString:
    """Tests for _parse_memory_string."""

    def test_gigabytes(self):
        assert _parse_memory_string("4g") == 4 * 1024**3

    def test_megabytes(self):
        assert _parse_memory_string("2048m") == 2048 * 1024**2

    def test_kilobytes(self):
        assert _parse_memory_string("512k") == 512 * 1024

    def test_bytes_suffix(self):
        assert _parse_memory_string("1073741824b") == 1073741824

    def test_plain_integer(self):
        assert _parse_memory_string("1073741824") == 1073741824

    def test_uppercase(self):
        assert _parse_memory_string("4G") == 4 * 1024**3

    def test_fractional(self):
        assert _parse_memory_string("1.5g") == int(1.5 * 1024**3)

    def test_whitespace_stripped(self):
        assert _parse_memory_string("  4g  ") == 4 * 1024**3

    def test_invalid_returns_none(self):
        assert _parse_memory_string("abc") is None

    def test_empty_string_returns_none(self):
        assert _parse_memory_string("") is None


class TestResolveMemoryLimit:
    """Tests for _resolve_memory_limit priority: CLI > env > None."""

    def test_cli_flag_wins(self, monkeypatch):
        monkeypatch.setenv("POLECAT_DOCKER_MEMORY", "2g")
        assert _resolve_memory_limit("4g") == "4g"

    def test_env_var_when_no_cli(self, monkeypatch):
        monkeypatch.setenv("POLECAT_DOCKER_MEMORY", "2g")
        assert _resolve_memory_limit(None) == "2g"

    def test_none_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("POLECAT_DOCKER_MEMORY", raising=False)
        assert _resolve_memory_limit(None) is None


class TestBuildDockerCmdMemory:
    """Tests for memory flags in _build_docker_cmd."""

    def _build(self, memory_limit=None, **kwargs):
        docker_cmd = _build_docker_cmd(
            cli_tool=kwargs.get("cli_tool", "claude"),
            work_dir=kwargs.get("work_dir", Path("/tmp/worktree")),
            env=kwargs.get("env", {}),
            agent_cmd=kwargs.get("agent_cmd", ["claude", "--dangerously-skip-permissions"]),
            is_interactive=kwargs.get("is_interactive", False),
            memory_limit=memory_limit,
        )
        return docker_cmd.cmd

    def test_memory_limit_flags_added(self):
        cmd = self._build(memory_limit="4g")
        assert "--memory" in cmd
        mem_idx = cmd.index("--memory")
        assert cmd[mem_idx + 1] == "4g"
        assert "--memory-swap" in cmd
        swap_idx = cmd.index("--memory-swap")
        assert cmd[swap_idx + 1] == "4g"

    def test_no_memory_flags_when_none(self):
        cmd = self._build(memory_limit=None)
        assert "--memory" not in cmd
        assert "--memory-swap" not in cmd

    def test_memory_swap_equals_memory(self):
        """--memory-swap == --memory disables swap for predictable OOM."""
        cmd = self._build(memory_limit="6g")
        mem_idx = cmd.index("--memory")
        swap_idx = cmd.index("--memory-swap")
        assert cmd[mem_idx + 1] == cmd[swap_idx + 1] == "6g"


class TestIsColimaEnv:
    """Tests for _is_colima_env."""

    def test_colima_socket(self):
        from cli import DockerSock

        sock = DockerSock(
            mount_source=Path("/var/run/docker.sock"),
            host_path=Path("/Users/testuser/.colima/default/docker.sock"),
        )
        with patch("cli._find_docker_sock", return_value=sock):
            assert _is_colima_env({}) is True

    def test_standard_socket(self):
        from cli import DockerSock

        sock = DockerSock(
            mount_source=Path("/var/run/docker.sock"),
            host_path=Path("/var/run/docker.sock"),
        )
        with patch("cli._find_docker_sock", return_value=sock):
            assert _is_colima_env({}) is False

    def test_no_socket(self):
        with patch("cli._find_docker_sock", return_value=None):
            assert _is_colima_env({}) is False


class TestFormatOomMessage:
    """Tests for _format_oom_message."""

    def test_colima_remediation(self):
        from cli import DockerSock

        sock = DockerSock(
            mount_source=Path("/var/run/docker.sock"),
            host_path=Path("/Users/testuser/.colima/default/docker.sock"),
        )
        with patch("cli._find_docker_sock", return_value=sock):
            msg = _format_oom_message({}, daemon_mem_bytes=2 * 1024**3)
        assert "exit code 137" in msg
        assert "2.0 GB" in msg
        assert "colima stop" in msg
        assert "colima start --memory" in msg

    def test_linux_remediation(self):
        with (
            patch("cli._find_docker_sock", return_value=None),
            patch("cli.sys.platform", "linux"),
        ):
            msg = _format_oom_message({})
        assert "exit code 137" in msg
        assert "free -h" in msg

    def test_docker_desktop_remediation(self):
        from cli import DockerSock

        sock = DockerSock(
            mount_source=Path("/var/run/docker.sock"),
            host_path=Path("/var/run/docker.sock"),
        )
        with (
            patch("cli._find_docker_sock", return_value=sock),
            patch("cli.sys.platform", "darwin"),
        ):
            msg = _format_oom_message({})
        assert "Docker Desktop" in msg
        assert "Settings" in msg

    def test_includes_polecat_docker_memory_hint(self):
        with patch("cli._find_docker_sock", return_value=None):
            msg = _format_oom_message({})
        assert "POLECAT_DOCKER_MEMORY" in msg
        assert "--memory" in msg

    def test_no_daemon_mem_omits_gb_line(self):
        with patch("cli._find_docker_sock", return_value=None):
            msg = _format_oom_message({}, daemon_mem_bytes=None)
        assert "GB memory available" not in msg
