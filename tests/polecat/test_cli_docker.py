#!/usr/bin/env python3
"""Tests for polecat CLI Docker-related functions.

Covers:
- NVM semver version sorting (_node_version_key)
- Docker command building (_build_docker_cmd)
- Worker environment construction (_make_worker_env)
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from cli import _build_docker_cmd, _node_version_key


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

    def _build(self, cli_tool="claude", env=None, agent_cmd=None, work_dir=None):
        return _build_docker_cmd(
            cli_tool=cli_tool,
            work_dir=work_dir or Path("/tmp/worktree"),
            env=env or {},
            agent_cmd=agent_cmd or ["claude", "--dangerously-skip-permissions"],
            is_interactive=False,
        )

    def test_runs_as_current_user(self):
        cmd = self._build()
        idx = cmd.index("--user")
        uid_gid = cmd[idx + 1]
        assert uid_gid == f"{os.getuid()}:{os.getgid()}"

    def test_mounts_worktree(self):
        cmd = self._build(work_dir=Path("/tmp/test-worktree"))
        assert "-v" in cmd
        vol_idx = [i for i, x in enumerate(cmd) if x == "-v"]
        volumes = [cmd[i + 1] for i in vol_idx]
        assert any("/tmp/test-worktree:/workspace" in v for v in volumes)

    def test_forwards_anthropic_api_key(self):
        env = {"ANTHROPIC_API_KEY": "sk-test-123"}
        cmd = self._build(env=env)
        assert "-e" in cmd
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "ANTHROPIC_API_KEY=sk-test-123" in env_args

    def test_does_not_forward_gemini_keys(self):
        """Gemini keys not needed in Claude Docker container — Gemini uses its own sandbox."""
        env = {"GEMINI_API_KEY": "gemini-test-key", "GOOGLE_API_KEY": "google-test-key"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any("GEMINI_API_KEY" in a for a in env_args)
        assert not any("GOOGLE_API_KEY" in a for a in env_args)

    def test_forwards_polecat_prefixed_env(self):
        env = {"POLECAT_SESSION_TYPE": "crew", "POLECAT_CREW_NAME": "test"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "POLECAT_SESSION_TYPE=crew" in env_args
        assert "POLECAT_CREW_NAME=test" in env_args

    def test_does_not_forward_arbitrary_env(self):
        env = {"MY_SECRET": "leaked", "DATABASE_URL": "postgres://..."}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert not any("MY_SECRET" in a for a in env_args)
        assert not any("DATABASE_URL" in a for a in env_args)

    def test_claude_mounts_config(self, tmp_path):
        """Claude config is mounted: .claude.json as temp copy with bypass flag, .claude dir read-write."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{}")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        json_vols = [v for v in vol_args if ".claude.json" in v]
        dir_vols = [v for v in vol_args if ".claude" in v and ".claude.json" not in v]
        # .claude.json is a temp copy (not the original) — mounted without :ro
        assert len(json_vols) == 1, f"Expected one .claude.json mount, got: {json_vols}"
        assert ":/home/worker/.claude.json" in json_vols[0]
        # The temp copy should NOT be the original file
        assert str(tmp_path / ".claude.json") not in json_vols[0].split(":")[0]
        assert all(not v.endswith(":ro") for v in dir_vols), (
            f".claude dir should be read-write for session data, got: {dir_vols}"
        )

    def test_claude_json_has_bypass_flag(self, tmp_path):
        """Temp .claude.json copy has bypassPermissionsModeAccepted=true."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text('{"projects": {}}')
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        json_vols = [v for v in vol_args if ".claude.json" in v]
        # Read the temp file to verify bypass flag was injected
        tmp_file = json_vols[0].split(":")[0]
        with open(tmp_file) as f:
            config = json.load(f)
        assert config["bypassPermissionsModeAccepted"] is True
        assert config["projects"] == {}

    def test_sets_home_to_worker_dir(self):
        """HOME is /home/worker, not host $HOME — avoids tmpfs mount conflicts."""
        cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        home_args = [a for a in env_args if a.startswith("HOME=")]
        assert len(home_args) == 1
        assert home_args[0] == "HOME=/home/worker"

    def test_no_tmpfs_mount(self):
        """No --tmpfs: it overrides bind mounts at the same path, hiding .claude config."""
        cmd = self._build()
        assert "--tmpfs" not in cmd

    def test_sets_timezone(self):
        """TZ is set in Docker env."""
        cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        tz_args = [a for a in env_args if a.startswith("TZ=")]
        assert len(tz_args) == 1
        # Default is Australia/Brisbane
        assert tz_args[0] == "TZ=Australia/Brisbane"

    def test_timezone_from_env(self):
        """TZ can be overridden via environment variable."""
        with patch.dict(os.environ, {"TZ": "UTC"}):
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        tz_args = [a for a in env_args if a.startswith("TZ=")]
        assert tz_args[0] == "TZ=UTC"

    def test_sets_git_identity(self):
        """Git author/committer identity is set for commits inside container."""
        cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_AUTHOR_NAME=aops-bot" in env_args
        assert "GIT_AUTHOR_EMAIL=aops-bot@users.noreply.github.com" in env_args
        assert "GIT_COMMITTER_NAME=aops-bot" in env_args
        assert "GIT_COMMITTER_EMAIL=aops-bot@users.noreply.github.com" in env_args

    def test_git_identity_from_env(self):
        """Git identity can be overridden via environment variables."""
        with patch.dict(
            os.environ,
            {"GIT_AUTHOR_NAME": "custom-bot", "GIT_AUTHOR_EMAIL": "custom@example.com"},
        ):
            cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_AUTHOR_NAME=custom-bot" in env_args
        assert "GIT_AUTHOR_EMAIL=custom@example.com" in env_args

    def test_ssh_isolation(self):
        """SSH_AUTH_SOCK is cleared and GIT_TERMINAL_PROMPT=0 inside container."""
        cmd = self._build()
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "SSH_AUTH_SOCK=" in env_args
        assert "GIT_TERMINAL_PROMPT=0" in env_args

    def test_git_credential_helper_with_gh_token(self):
        """Git credential helper is configured when GH_TOKEN is available."""
        env = {"GH_TOKEN": "ghp_test123"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GIT_CONFIG_COUNT=3" in env_args
        config_vals = [a for a in env_args if a.startswith("GIT_CONFIG_VALUE_0=")]
        assert len(config_vals) == 1
        assert "x-access-token" in config_vals[0]
        # URL rewriting: git@github.com: → https://github.com/
        insteadof_keys = [a for a in env_args if a.startswith("GIT_CONFIG_KEY_1=")]
        assert insteadof_keys[0] == "GIT_CONFIG_KEY_1=url.https://github.com/.insteadOf"

    def test_forwards_gh_token(self):
        """GH_TOKEN is forwarded to Docker container."""
        env = {"GH_TOKEN": "ghp_test123"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GH_TOKEN=ghp_test123" in env_args

    def test_mounts_pkb_binary_when_available(self):
        """pkb binary is mounted read-only for MCP server access."""
        with patch(
            "cli.shutil.which",
            side_effect=lambda name, **kw: "/usr/bin/pkb" if name == "pkb" else None,
        ):
            cmd = self._build()
        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        assert any("/usr/bin/pkb:/usr/local/bin/pkb:ro" in v for v in vol_args)

    def test_no_pkb_mount_when_missing(self):
        """No pkb mount when binary is not found on host."""
        with patch("cli.shutil.which", return_value=None):
            cmd = self._build()
        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        assert not any("/usr/local/bin/pkb" in v for v in vol_args)

    def test_mounts_aca_data_when_set(self, tmp_path):
        """ACA_DATA directory is mounted for PKB access."""
        aca_dir = tmp_path / "brain"
        aca_dir.mkdir()
        env = {"ACA_DATA": str(aca_dir)}
        cmd = self._build(env=env)
        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        assert any(str(aca_dir) in v for v in vol_args)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert f"ACA_DATA={aca_dir}" in env_args


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
