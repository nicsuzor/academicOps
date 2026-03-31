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

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from cli import (
    _build_docker_cmd,
    _clone_has_changes,
    _node_version_key,
    _pass_pkb_url_sandbox,
    _replicate_gemini_auth,
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

    def test_forwards_gate_mode_vars(self):
        """Gate mode env vars must reach the hook subprocess inside the container."""
        env = {
            "CUSTODIET_GATE_MODE": "block",
            "HANDOVER_GATE_MODE": "warn",
            "QA_GATE_MODE": "warn",
            "CUSTODIET_TOOL_CALL_THRESHOLD": "50",
        }
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "CUSTODIET_GATE_MODE=block" in env_args
        assert "HANDOVER_GATE_MODE=warn" in env_args
        assert "QA_GATE_MODE=warn" in env_args
        assert "CUSTODIET_TOOL_CALL_THRESHOLD=50" in env_args

    def test_forwards_aops_prefixed_env(self):
        """AOPS_* vars are forwarded (e.g. ACA_DATA, AOPS_SESSIONS)."""
        env = {"AOPS_SESSIONS": "/tmp/sessions", "AOPS_CUSTOM_VAR": "value"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "AOPS_SESSIONS=/tmp/sessions" in env_args
        assert "AOPS_CUSTOM_VAR=value" in env_args

    def test_claude_mounts_config(self, tmp_path):
        """Claude auth files are staged into a temp dir and mounted as /tmp/staging:ro."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{}")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        # Staging dir is mounted read-only at /tmp/staging
        staging_vols = [v for v in vol_args if ":/tmp/staging:ro" in v]
        assert len(staging_vols) == 1, (
            f"Expected one staging mount at /tmp/staging:ro, got: {vol_args}"
        )
        # The original .claude.json should NOT be mounted directly
        direct_json_vols = [v for v in vol_args if ":/home/worker/.claude.json" in v]
        assert len(direct_json_vols) == 0, (
            f"Expected no direct .claude.json mount, got: {direct_json_vols}"
        )
        # Staging dir must exist and contain .claude.json
        staging_host = Path(staging_vols[0].split(":")[0])
        assert (staging_host / ".claude.json").exists()

    def test_claude_json_has_bypass_flag(self, tmp_path):
        """Staged .claude.json copy has bypassPermissionsModeAccepted=true."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text('{"projects": {}}')
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        staging_vols = [v for v in vol_args if ":/tmp/staging:ro" in v]
        staging_host = Path(staging_vols[0].split(":")[0])
        with open(staging_host / ".claude.json") as f:
            config = json.load(f)
        assert config["bypassPermissionsModeAccepted"] is True
        assert config["projects"] == {}

    def test_claude_stages_settings_json(self, tmp_path):
        """settings.json is staged for Claude containers.

        Regression test: Claude Code requires skipDangerousModePermissionPrompt
        and enabledPlugins from settings.json. Without it, --dangerously-skip-permissions
        hangs waiting for an interactive prompt in headless mode.
        """
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{}")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings = {
            "enabledPlugins": {"aops-core@aops": True},
            "skipDangerousModePermissionPrompt": True,
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        staging_vols = [v for v in vol_args if ":/tmp/staging:ro" in v]
        staging_host = Path(staging_vols[0].split(":")[0])
        staged_settings = staging_host / ".claude" / "settings.json"
        assert staged_settings.exists(), "settings.json must be staged for Claude containers"
        data = json.loads(staged_settings.read_text())
        assert data["skipDangerousModePermissionPrompt"] is True
        assert data["enabledPlugins"]["aops-core@aops"] is True

    def test_claude_does_not_stage_settings_local(self, tmp_path):
        """settings.local.json must NOT be staged — it contains the user's personal GH_TOKEN.

        Container uses bot token via env vars, not the user's personal token.
        """
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{}")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.local.json").write_text(
            '{"env": {"GH_TOKEN": "personal-token-DO-NOT-STAGE"}}'
        )

        with patch("cli.Path.home", return_value=tmp_path):
            cmd = self._build(cli_tool="claude")

        vol_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-v"]
        staging_vols = [v for v in vol_args if ":/tmp/staging:ro" in v]
        staging_host = Path(staging_vols[0].split(":")[0])
        assert not (staging_host / ".claude" / "settings.local.json").exists(), (
            "settings.local.json must NOT be staged — contains user's personal token"
        )

    def test_no_tmpfs_mount(self):
        """No --tmpfs: it overrides bind mounts at the same path, hiding .claude config."""
        cmd = self._build()
        assert "--tmpfs" not in cmd

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
        """GH_TOKEN and AOPS_BOT_GH_TOKEN are forwarded when available."""
        env = {"GH_TOKEN": "ghp_test123"}
        cmd = self._build(env=env)
        env_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
        assert "GH_TOKEN=ghp_test123" in env_args
        assert "AOPS_BOT_GH_TOKEN=ghp_test123" in env_args
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
        # No auth selectedType (Gemini auto-detects — avoids auth mismatch crash)
        assert "security" not in replicated
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


class TestPassPkbUrlSandbox:
    """Tests for _pass_pkb_url_sandbox — called by both crew -g and run -g."""

    def test_passes_url_from_env_dict(self):
        env: dict = {"PKB_MCP_URL": "http://localhost:8026/mcp"}
        _pass_pkb_url_sandbox(env)
        assert env["PKB_MCP_URL"] == "http://localhost:8026/mcp"

    def test_passes_url_from_os_environ(self, monkeypatch):
        monkeypatch.setenv("PKB_MCP_URL", "http://host:8026/mcp")
        env: dict = {}
        _pass_pkb_url_sandbox(env)
        assert env["PKB_MCP_URL"] == "http://host:8026/mcp"

    def test_noop_when_url_missing(self, monkeypatch):
        monkeypatch.delenv("PKB_MCP_URL", raising=False)
        env: dict = {}
        _pass_pkb_url_sandbox(env)
        assert "PKB_MCP_URL" not in env


class TestCloneHasChanges:
    """Tests for _clone_has_changes — used for auto-nuke of crew with no work."""

    def _init_repo(self, path):
        """Create a git repo with one commit and a remote-like ref."""
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True
        )
        (path / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)
        # Create a fake origin/main ref pointing at HEAD
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
            cwd=path,
            check=True,
            capture_output=True,
        )
        # Set symbolic HEAD for origin
        subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
            cwd=path,
            check=True,
            capture_output=True,
        )

    def test_no_changes_returns_false(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        assert _clone_has_changes(repo) is False

    def test_uncommitted_changes_returns_true(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        (repo / "new_file.txt").write_text("uncommitted")
        assert _clone_has_changes(repo) is True

    def test_committed_changes_returns_true(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        (repo / "new_file.txt").write_text("committed")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "new work"], cwd=repo, check=True, capture_output=True
        )
        assert _clone_has_changes(repo) is True

    def test_nonexistent_path_returns_true(self, tmp_path):
        """Safe default: if path doesn't exist, assume changes (don't auto-nuke)."""
        assert _clone_has_changes(tmp_path / "nonexistent") is True
