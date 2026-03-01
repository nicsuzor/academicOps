"""Integration test: credential isolation for headless CLI sessions.

Verifies that headless agent sessions launched by aops get AOPS_BOT_GH_TOKEN
as their working GH_TOKEN/GITHUB_TOKEN, and do NOT inherit the user's personal
GitHub credentials from the parent shell.

Architecture (unified for both CLIs):
- agent-env-map.conf defines TARGET=SOURCE mappings (single source of truth)
- lib/agent_env.py reads the config and applies mappings to subprocess envs
- hooks/session_env_setup.py also reads the config for CLAUDE_ENV_FILE persistence
- tests/conftest.py headless runners call apply_env_mappings() before launch

Test categories:
- Config unit tests: parsing, mapping, custom config files
- Hook unit tests: session_env_setup writes mapped vars to CLAUDE_ENV_FILE
- Claude e2e: launches Claude headless, verifies Bash tool sees bot token
- Gemini e2e: launches Gemini headless, verifies shell sees bot token
"""

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import HookContext
from hooks.session_env_setup import run_session_env_setup
from lib.agent_env import (
    EnvEntry,
    apply_env_mappings,
    get_env_mapping_persist_dict,
    load_env_entries,
    load_env_mappings,
)
from lib.session_state import SessionState

# --- Fixtures ---


@pytest.fixture
def credential_markers():
    """Generate unique non-secret-looking markers for credential testing.

    Values intentionally do NOT look like real tokens (no ghp_ prefix)
    to avoid Gemini's secret redaction matching on value patterns.
    """
    return {
        "bot": f"aopstest_bot_{uuid.uuid4().hex[:16]}",
        "personal": f"aopstest_personal_{uuid.uuid4().hex[:16]}",
    }


@pytest.fixture
def output_file(tmp_path):
    """Temporary file for CLI to write GH_TOKEN value to."""
    return tmp_path / "gh_token_output.txt"


def _get_plugin_dir() -> str | None:
    """Get aops-core plugin directory path."""
    aops_env = os.environ.get("AOPS")
    if aops_env:
        return str(Path(aops_env) / "aops-core")
    candidate = Path(__file__).parent.parent.parent / "aops-core"
    if candidate.exists():
        return str(candidate)
    return None


# ---------------------------------------------------------------------------
# Unit test: agent-env-map.conf parsing and mapping
# ---------------------------------------------------------------------------


class TestAgentEnvConfig:
    """Unit tests for lib/agent_env.py config parsing and mapping."""

    def test_load_default_config(self):
        """Default agent-env-map.conf should define GH_TOKEN mapping."""
        mappings = load_env_mappings()
        targets = [t for t, _s in mappings]
        assert "GH_TOKEN" in targets

    def test_load_default_config_sources(self):
        """GH_TOKEN should map from AOPS_BOT_GH_TOKEN."""
        mappings = load_env_mappings()
        mapping_dict = dict(mappings)
        assert mapping_dict["GH_TOKEN"] == "AOPS_BOT_GH_TOKEN"

    def test_load_custom_config(self, tmp_path):
        """Custom config file with arbitrary mappings should be parseable."""
        config = tmp_path / "custom.conf"
        config.write_text(
            "# Custom mappings\nDEPLOY_KEY=AOPS_BOT_DEPLOY_KEY\n\nNPM_TOKEN=AOPS_BOT_NPM_TOKEN\n"
        )
        mappings = load_env_mappings(config)
        assert ("DEPLOY_KEY", "AOPS_BOT_DEPLOY_KEY") in mappings
        assert ("NPM_TOKEN", "AOPS_BOT_NPM_TOKEN") in mappings

    def test_load_empty_config(self, tmp_path):
        """Empty config file should return no mappings."""
        config = tmp_path / "empty.conf"
        config.write_text("# only comments\n\n")
        assert load_env_mappings(config) == []

    def test_load_missing_config(self, tmp_path):
        """Missing config file should return no mappings (not crash)."""
        assert load_env_mappings(tmp_path / "nonexistent.conf") == []

    def test_apply_maps_bot_token(self, credential_markers):
        """apply_env_mappings should set GH_TOKEN from AOPS_BOT_GH_TOKEN."""
        bot = credential_markers["bot"]
        env = {"PATH": "/usr/bin"}
        source = {"AOPS_BOT_GH_TOKEN": bot}

        apply_env_mappings(env, source_env=source)

        assert env["GH_TOKEN"] == bot

    def test_apply_skips_absent_source(self):
        """apply_env_mappings should skip mappings where SOURCE is not set."""
        env = {"PATH": "/usr/bin"}
        source = {}  # No AOPS_BOT_GH_TOKEN

        apply_env_mappings(env, source_env=source)

        assert "GH_TOKEN" not in env

    def test_apply_overwrites_personal_token(self, credential_markers):
        """apply_env_mappings should overwrite existing GH_TOKEN with bot value."""
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        env = {"GH_TOKEN": personal}
        source = {"AOPS_BOT_GH_TOKEN": bot}

        apply_env_mappings(env, source_env=source)

        assert env["GH_TOKEN"] == bot

    def test_apply_with_custom_config(self, tmp_path, credential_markers):
        """apply_env_mappings should work with a custom config file."""
        bot = credential_markers["bot"]

        config = tmp_path / "custom.conf"
        config.write_text("MY_TOKEN=MY_SOURCE\n")

        env = {}
        source = {"MY_SOURCE": bot}

        apply_env_mappings(env, config_path=config, source_env=source)

        assert env["MY_TOKEN"] == bot
        assert "GH_TOKEN" not in env  # default config not loaded

    def test_get_persist_dict(self, credential_markers):
        """get_env_mapping_persist_dict should return {TARGET: value} for hook use."""
        bot = credential_markers["bot"]
        source = {"AOPS_BOT_GH_TOKEN": bot}

        result = get_env_mapping_persist_dict(source_env=source)

        assert result["GH_TOKEN"] == bot
        # Literals are always included
        assert result["SSH_AUTH_SOCK"] == ""
        assert result["GIT_TERMINAL_PROMPT"] == "0"

    def test_get_persist_dict_excludes_mappings_when_source_absent(self):
        """get_env_mapping_persist_dict should exclude env-to-env mappings when source is absent."""
        result = get_env_mapping_persist_dict(source_env={})
        # Literals are always included even with empty source_env
        # Only env-to-env mappings are excluded when source is absent
        for key, _val in result.items():
            entry = next(e for e in load_env_entries() if e.target == key)
            assert entry.is_literal, f"{key} should only appear as a literal"

    # --- Literal (:=) syntax tests ---

    def test_load_entries_includes_literals(self):
        """Default config should include SSH_AUTH_SOCK and GIT_TERMINAL_PROMPT literals."""
        entries = load_env_entries()
        targets = {e.target for e in entries}
        assert "SSH_AUTH_SOCK" in targets
        assert "GIT_TERMINAL_PROMPT" in targets

    def test_load_entries_literal_types(self):
        """Literal entries should have is_literal=True."""
        entries = load_env_entries()
        by_target = {e.target: e for e in entries}
        assert by_target["SSH_AUTH_SOCK"].is_literal is True
        assert by_target["SSH_AUTH_SOCK"].value == ""
        assert by_target["GIT_TERMINAL_PROMPT"].is_literal is True
        assert by_target["GIT_TERMINAL_PROMPT"].value == "0"

    def test_load_entries_mapping_types(self):
        """Env-to-env mappings should have is_literal=False."""
        entries = load_env_entries()
        by_target = {e.target: e for e in entries}
        assert by_target["GH_TOKEN"].is_literal is False
        assert by_target["GH_TOKEN"].value == "AOPS_BOT_GH_TOKEN"

    def test_load_mappings_excludes_literals(self):
        """load_env_mappings() (legacy) should only return env-to-env mappings."""
        mappings = load_env_mappings()
        targets = [t for t, _s in mappings]
        assert "GH_TOKEN" in targets
        assert "SSH_AUTH_SOCK" not in targets
        assert "GIT_TERMINAL_PROMPT" not in targets

    def test_load_custom_config_with_literals(self, tmp_path):
        """Custom config with both formats should parse correctly."""
        config = tmp_path / "mixed.conf"
        config.write_text("# Mixed config\nAPI_KEY=BOT_API_KEY\nDEBUG:=1\nEMPTY_VAR:=\n")
        entries = load_env_entries(config)
        assert len(entries) == 3
        assert entries[0] == EnvEntry("API_KEY", "BOT_API_KEY", is_literal=False)
        assert entries[1] == EnvEntry("DEBUG", "1", is_literal=True)
        assert entries[2] == EnvEntry("EMPTY_VAR", "", is_literal=True)

    def test_apply_sets_literals(self):
        """apply_env_mappings should set literal values unconditionally."""
        env = {"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock", "GIT_TERMINAL_PROMPT": "1"}
        apply_env_mappings(env, source_env={})

        assert env["SSH_AUTH_SOCK"] == ""
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_apply_literals_independent_of_source(self, tmp_path):
        """Literals should be applied regardless of source_env contents."""
        config = tmp_path / "literal_only.conf"
        config.write_text("MY_FLAG:=enabled\n")

        env = {}
        apply_env_mappings(env, config_path=config, source_env={})
        assert env["MY_FLAG"] == "enabled"

    def test_apply_clears_ssh_auth_sock(self):
        """Default config should clear SSH_AUTH_SOCK to disconnect SSH agent."""
        env = {"SSH_AUTH_SOCK": "/private/tmp/com.apple.launchd.xyz/Listeners"}
        apply_env_mappings(env, source_env={})
        assert env["SSH_AUTH_SOCK"] == ""

    def test_persist_dict_includes_literals(self, credential_markers):
        """get_env_mapping_persist_dict should include literal entries."""
        bot = credential_markers["bot"]
        result = get_env_mapping_persist_dict(source_env={"AOPS_BOT_GH_TOKEN": bot})

        assert result["GH_TOKEN"] == bot
        assert result["SSH_AUTH_SOCK"] == ""
        assert result["GIT_TERMINAL_PROMPT"] == "0"


# ---------------------------------------------------------------------------
# Unit test: hook-based credential bridge (uses config)
# ---------------------------------------------------------------------------


class TestCredentialBridgeHook:
    """Unit tests for session_env_setup credential mapping via agent-env-map.conf."""

    @pytest.fixture
    def temp_env_file(self, tmp_path):
        """Create a temporary CLAUDE_ENV_FILE and patch it into os.environ."""
        env_file = tmp_path / "claude_env"
        env_file.touch()
        with patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file)}):
            yield env_file

    def test_hook_maps_bot_token_to_gh_token(self, temp_env_file, credential_markers):
        """session_env_setup should write GH_TOKEN=bot_token to CLAUDE_ENV_FILE.

        The hook reads agent-env-map.conf and persists the mapped values.
        """
        bot = credential_markers["bot"]

        ctx = HookContext(
            session_id="test-cred-isolation-001",
            session_short_hash="credtest",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict("os.environ", {"AOPS_BOT_GH_TOKEN": bot}),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=Path("/tmp/aops/test-sessions"),
            ),
        ):
            result = run_session_env_setup(ctx, state)

        assert result is not None
        assert result.verdict.value == "allow"

        content = temp_env_file.read_text()
        assert f'export GH_TOKEN="{bot}"' in content, (
            f"Hook should write GH_TOKEN to CLAUDE_ENV_FILE.\n"
            f'Expected: export GH_TOKEN="{bot}"\n'
            f"Got: {content}"
        )

    def test_hook_persists_ssh_isolation(self, temp_env_file):
        """session_env_setup should write SSH isolation vars to CLAUDE_ENV_FILE."""
        ctx = HookContext(
            session_id="test-ssh-isolation",
            session_short_hash="sshtest1",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict("os.environ", {}, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=Path("/tmp/aops/test-sessions"),
            ),
        ):
            run_session_env_setup(ctx, state)

        content = temp_env_file.read_text()
        assert 'export SSH_AUTH_SOCK=""' in content, (
            f"Hook should clear SSH_AUTH_SOCK in CLAUDE_ENV_FILE.\nGot: {content}"
        )
        assert 'export GIT_TERMINAL_PROMPT="0"' in content, (
            f"Hook should set GIT_TERMINAL_PROMPT=0 in CLAUDE_ENV_FILE.\nGot: {content}"
        )

    def test_hook_does_not_map_when_bot_token_absent(self, temp_env_file):
        """When AOPS_BOT_GH_TOKEN is not set, hook should not write GH_TOKEN."""
        ctx = HookContext(
            session_id="test-cred-no-bot",
            session_short_hash="nobot123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        env_patch = {k: v for k, v in os.environ.items() if k != "AOPS_BOT_GH_TOKEN"}
        env_patch["CLAUDE_ENV_FILE"] = str(temp_env_file)

        with (
            patch.dict("os.environ", env_patch, clear=True),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=Path("/tmp/aops/test-sessions"),
            ),
        ):
            run_session_env_setup(ctx, state)

        content = temp_env_file.read_text()
        assert "GH_TOKEN" not in content, (
            f"Hook should NOT write GH_TOKEN when AOPS_BOT_GH_TOKEN is absent.\nGot: {content}"
        )

    def test_hook_overrides_existing_personal_token(self, temp_env_file, credential_markers):
        """Hook should override user's personal GH_TOKEN with bot token."""
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        ctx = HookContext(
            session_id="test-cred-override",
            session_short_hash="override1",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict(
                "os.environ",
                {
                    "AOPS_BOT_GH_TOKEN": bot,
                    "GH_TOKEN": personal,
                    "GITHUB_TOKEN": personal,
                },
            ),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=Path("/tmp/aops/test-sessions"),
            ),
        ):
            run_session_env_setup(ctx, state)

        content = temp_env_file.read_text()
        assert f'export GH_TOKEN="{bot}"' in content
        assert personal not in content, (
            f"SECURITY: Personal token {personal!r} leaked into CLAUDE_ENV_FILE!"
        )


# ---------------------------------------------------------------------------
# E2E: Claude Code headless credential isolation
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
class TestClaudeCredentialIsolation:
    """E2E tests: verify Claude Code gets bot token via unified env mapping."""

    @pytest.fixture(autouse=True)
    def _require_claude(self):
        if not shutil.which("claude"):
            pytest.skip("claude CLI not found in PATH")

    def test_claude_session_gets_bot_token(self, credential_markers, output_file, tmp_path):
        """Claude's Bash tool should see GH_TOKEN = AOPS_BOT_GH_TOKEN.

        Both the harness (apply_env_mappings) and the hook (session_env_setup)
        read agent-env-map.conf. The harness sets GH_TOKEN in the subprocess env,
        and the hook also writes it to CLAUDE_ENV_FILE (belt and suspenders).
        """
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        # Start with personal token in env (simulating user's shell)
        env = os.environ.copy()
        env["AOPS_BOT_GH_TOKEN"] = bot
        env["GH_TOKEN"] = personal

        # Apply config-driven mapping (overwrites personal → bot)
        apply_env_mappings(env)

        plugin_dir = _get_plugin_dir()
        assert plugin_dir, "Cannot find aops-core plugin directory"

        prompt = f"Use the Bash tool to run this exact command: printenv GH_TOKEN > {output_file}"

        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
            "--max-turns",
            "3",
            "--model",
            "haiku",
            "--no-session-persistence",
            "--plugin-dir",
            plugin_dir,
        ]

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp_path,
            check=False,
        )

        assert result.returncode == 0, (
            f"Claude CLI failed (exit {result.returncode}):\n"
            f"stderr: {result.stderr[:500]}\n"
            f"stdout: {result.stdout[:500]}"
        )

        assert output_file.exists(), (
            "Claude did not write the output file. The Bash tool may not have executed."
        )

        actual_token = output_file.read_text().strip()

        assert actual_token == bot, (
            f"Credential isolation FAILED for Claude.\n"
            f"Expected GH_TOKEN = bot marker: {bot!r}\n"
            f"Got: {actual_token!r}\n"
            f"Personal marker was: {personal!r}"
        )
        assert actual_token != personal, (
            "SECURITY: Claude inherited personal token instead of bot token!"
        )


# ---------------------------------------------------------------------------
# E2E: Gemini CLI headless credential isolation
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
class TestGeminiCredentialIsolation:
    """E2E tests: verify Gemini CLI gets bot token via unified env mapping.

    Gemini redacts env vars matching /TOKEN/i by default, so the test creates
    a .gemini/settings.json with allowedEnvironmentVariables to ensure
    GH_TOKEN reaches the shell.
    """

    @pytest.fixture(autouse=True)
    def _require_gemini(self):
        if not shutil.which("gemini"):
            pytest.skip("gemini CLI not found in PATH")

    @pytest.fixture
    def gemini_workdir(self, tmp_path):
        """Create a temp working directory with Gemini settings that allowlist GH_TOKEN."""
        workdir = tmp_path / "gemini_cred_test"
        workdir.mkdir()

        gemini_dir = workdir / ".gemini"
        gemini_dir.mkdir()
        settings = {
            "security": {
                "allowedEnvironmentVariables": [
                    "GH_TOKEN",
                ]
            }
        }
        (gemini_dir / "settings.json").write_text(json.dumps(settings))

        return workdir

    def test_gemini_session_gets_bot_token(self, credential_markers, output_file, gemini_workdir):
        """Gemini's shell should see GH_TOKEN = bot token via apply_env_mappings.

        Same unified config (agent-env-map.conf) drives both CLIs.
        """
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        env = os.environ.copy()
        env["AOPS_BOT_GH_TOKEN"] = bot
        env["GH_TOKEN"] = personal

        # Apply config-driven mapping (same as Claude)
        apply_env_mappings(env)

        prompt = f"Execute this shell command: printenv GH_TOKEN > {output_file}"

        cmd = [
            "gemini",
            prompt,
            "-o",
            "json",
            "--yolo",
        ]

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(gemini_workdir),
            check=False,
        )

        assert result.returncode == 0, (
            f"Gemini CLI failed (exit {result.returncode}):\n"
            f"stderr: {result.stderr[:500]}\n"
            f"stdout: {result.stdout[:500]}"
        )

        assert output_file.exists(), (
            "Gemini did not write the output file. "
            "The shell tool may not have executed, or GH_TOKEN was redacted."
        )

        actual_token = output_file.read_text().strip()

        assert actual_token == bot, (
            f"Credential isolation FAILED for Gemini.\n"
            f"Expected GH_TOKEN = bot marker: {bot!r}\n"
            f"Got: {actual_token!r}\n"
            f"Personal marker was: {personal!r}"
        )
        assert actual_token != personal, (
            "SECURITY: Gemini inherited personal token instead of bot token!"
        )

    def test_gemini_redacts_token_without_allowlist(self, credential_markers, tmp_path):
        """Without allowedEnvironmentVariables, Gemini should redact GH_TOKEN.

        Verifies Gemini's default security: env vars matching /TOKEN/i
        are redacted before reaching shell tools.
        """
        bot = credential_markers["bot"]

        workdir = tmp_path / "gemini_no_allowlist"
        workdir.mkdir()
        output = workdir / "token_check.txt"

        env = os.environ.copy()
        env["AOPS_BOT_GH_TOKEN"] = bot
        apply_env_mappings(env)

        prompt = f"Execute this shell command: printenv GH_TOKEN > {output} ; echo done"

        cmd = ["gemini", prompt, "-o", "json", "--yolo"]

        subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(workdir),
            check=False,
        )

        if output.exists():
            actual = output.read_text().strip()
            assert actual != bot, (
                f"Gemini should redact GH_TOKEN without allowlist, but it leaked: {actual!r}"
            )
