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
- Subprocess tests: verify mapped env propagates through process boundaries
"""

import os
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

from hooks.session_env_setup import run_session_env_setup
from lib.agent_env import (
    EnvEntry,
    apply_env_mappings,
    get_env_mapping_persist_dict,
    load_env_entries,
    load_env_mappings,
)
from lib.hook_context import HookContext
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

    def test_apply_skips_empty_source(self):
        """apply_env_mappings should skip mappings where SOURCE is empty.

        Empty-string sources are treated identically to unset — closes the
        credential-leak class where a host shell exporting AOPS_BOT_GH_TOKEN=""
        would otherwise propagate empty GH_TOKEN to the container, causing gh
        CLI to fall through to keyring auth (or worse, headless claude to
        send an empty x-api-key header). See task-ebc758fd.
        """
        env = {"PATH": "/usr/bin"}
        source = {"AOPS_BOT_GH_TOKEN": ""}  # set but empty

        apply_env_mappings(env, source_env=source)

        assert "GH_TOKEN" not in env
        assert "GITHUB_TOKEN" not in env

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
        """Default config should include SSH isolation and GIT_TERMINAL_PROMPT literals."""
        entries = load_env_entries()
        targets = {e.target for e in entries}
        assert "SSH_AUTH_SOCK" in targets
        assert "GIT_SSH_COMMAND" in targets
        assert "GIT_TERMINAL_PROMPT" in targets

    def test_load_entries_literal_types(self):
        """Literal entries should have is_literal=True."""
        entries = load_env_entries()
        by_target = {e.target: e for e in entries}
        assert by_target["SSH_AUTH_SOCK"].is_literal is True
        assert by_target["SSH_AUTH_SOCK"].value == ""
        assert by_target["GIT_SSH_COMMAND"].is_literal is True
        assert by_target["GIT_SSH_COMMAND"].value == "false"
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
# Unit test: polecat worker env sanitization
# ---------------------------------------------------------------------------


class TestWorkerEnvSanitization:
    """Tests that polecat worker env sanitization works correctly.

    Simulates what _make_worker_env() does: os.environ.copy() + apply_env_mappings().
    Tests the contract rather than importing polecat.cli (which has heavy deps).
    """

    def test_ssh_auth_sock_cleared(self, credential_markers):
        """Worker env should have SSH_AUTH_SOCK cleared."""
        bot = credential_markers["bot"]
        with patch.dict(
            "os.environ",
            {
                "SSH_AUTH_SOCK": "/private/tmp/com.apple.launchd.xyz/Listeners",
                "AOPS_BOT_GH_TOKEN": bot,
            },
        ):
            env = os.environ.copy()
            apply_env_mappings(env)
        assert env["SSH_AUTH_SOCK"] == "", "SECURITY: SSH_AUTH_SOCK should be cleared in worker env"

    def test_gh_token_mapped_to_bot(self, credential_markers):
        """Worker env should have GH_TOKEN set to AOPS_BOT_GH_TOKEN."""
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]
        with patch.dict(
            "os.environ",
            {
                "AOPS_BOT_GH_TOKEN": bot,
                "GH_TOKEN": personal,
            },
        ):
            env = os.environ.copy()
            apply_env_mappings(env)
        assert env["GH_TOKEN"] == bot, "Worker should use bot token, not personal"
        assert env.get("GH_TOKEN") != personal, "SECURITY: Personal token leaked to worker env"

    def test_git_terminal_prompt_disabled(self):
        """Worker env should have GIT_TERMINAL_PROMPT=0."""
        with patch.dict("os.environ", {}, clear=False):
            env = os.environ.copy()
            apply_env_mappings(env)
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_full_worker_env_contract(self, credential_markers):
        """Full contract: SSH stripped, token mapped, prompts disabled."""
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]
        with patch.dict(
            "os.environ",
            {
                "SSH_AUTH_SOCK": "/private/tmp/com.apple.launchd.xyz/Listeners",
                "AOPS_BOT_GH_TOKEN": bot,
                "GH_TOKEN": personal,
                "GITHUB_TOKEN": personal,
            },
        ):
            # This is exactly what _make_worker_env() does
            env = os.environ.copy()
            apply_env_mappings(env)

        assert env["SSH_AUTH_SOCK"] == "", "SSH agent must be disconnected"
        assert env["GH_TOKEN"] == bot, "GH_TOKEN must be bot token"
        assert env["GITHUB_TOKEN"] == bot, "GITHUB_TOKEN must be bot token"
        assert env["GIT_TERMINAL_PROMPT"] == "0", "Interactive prompts must be disabled"
        assert personal not in env.values(), "SECURITY: Personal token must not appear anywhere"


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
        """Sourcing the env file with the bot token set yields GH_TOKEN=bot.

        GH_TOKEN/GITHUB_TOKEN are now exported as deferred shell expressions
        (`${AOPS_BOT_GH_TOKEN:-}`) rather than hook-time literals, so we verify
        the runtime effect by sourcing the file rather than grepping for a
        literal value.
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

        # Source the env file with the bot token present, then read GH_TOKEN.
        proc = subprocess.run(
            [
                "/bin/bash",
                "-c",
                f"export AOPS_BOT_GH_TOKEN={bot}; source {temp_env_file}; "
                f'printf "%s\\n%s\\n" "$GH_TOKEN" "$GITHUB_TOKEN"',
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        gh, github = proc.stdout.strip().split("\n")
        assert gh == bot, f"GH_TOKEN should resolve to bot token; got {gh!r}"
        assert github == bot, f"GITHUB_TOKEN should resolve to bot token; got {github!r}"

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
        # shlex.quote('') → '' (single quotes), shlex.quote('0') → 0 (no quotes)
        assert "export SSH_AUTH_SOCK=''" in content, (
            f"Hook should clear SSH_AUTH_SOCK in CLAUDE_ENV_FILE.\nGot: {content}"
        )
        assert "export GIT_TERMINAL_PROMPT=0" in content, (
            f"Hook should set GIT_TERMINAL_PROMPT=0 in CLAUDE_ENV_FILE.\nGot: {content}"
        )
        assert "export GIT_SSH_COMMAND=false" in content, (
            f"Hook should set GIT_SSH_COMMAND=false in CLAUDE_ENV_FILE.\nGot: {content}"
        )
        # SSH→HTTPS rewrite must be configured via GIT_CONFIG env vars
        assert "GIT_CONFIG_COUNT" in content, (
            f"Hook should set GIT_CONFIG_COUNT for insteadOf rewrite.\nGot: {content}"
        )
        assert "url.https://github.com/.insteadOf" in content, (
            f"Hook should rewrite SSH URLs to HTTPS.\nGot: {content}"
        )

    def test_hook_fails_closed_when_bot_token_absent(self, temp_env_file):
        """When AOPS_BOT_GH_TOKEN is absent, sourcing the env file must leave
        GH_TOKEN/GITHUB_TOKEN EMPTY — fail-closed — and must clobber any
        personal token that was already present in the parent env.

        This is the deliberate reversal of the prior skip-when-absent contract
        (task-ebc758fd): on the host, skipping left an inherited personal token
        intact. Exporting the bot token's value (empty when it is unset) both
        fails closed and overwrites the leak.
        """
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

        # Source the env file with a PERSONAL token pre-set and AOPS_BOT_GH_TOKEN
        # unset. GH_TOKEN/GITHUB_TOKEN must end up empty (personal clobbered).
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                "unset AOPS_BOT_GH_TOKEN; "
                "export GH_TOKEN=personal_leak GITHUB_TOKEN=personal_leak; "
                f"source {temp_env_file}; "
                'printf "GH=[%s]\\nGITHUB=[%s]\\n" "$GH_TOKEN" "$GITHUB_TOKEN"',
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        assert "GH=[]" in result.stdout, (
            f"GH_TOKEN must be EMPTY (fail-closed) when AOPS_BOT_GH_TOKEN is absent.\n"
            f"Output: {result.stdout!r}"
        )
        assert "GITHUB=[]" in result.stdout, (
            f"GITHUB_TOKEN must be EMPTY (fail-closed) when AOPS_BOT_GH_TOKEN is absent.\n"
            f"Output: {result.stdout!r}"
        )
        assert "personal_leak" not in result.stdout, (
            f"SECURITY: personal token survived into GH_TOKEN/GITHUB_TOKEN.\n"
            f"Output: {result.stdout!r}"
        )

    def test_hook_overrides_existing_personal_token(self, temp_env_file, credential_markers):
        """Hook should override user's personal GH_TOKEN with the bot token.

        Verified by sourcing the env file with a personal token pre-set: the
        bot token must win, and the personal value must never appear in the
        file (it is referenced only via ${AOPS_BOT_GH_TOKEN}).
        """
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
        assert personal not in content, (
            f"SECURITY: Personal token {personal!r} leaked into CLAUDE_ENV_FILE!"
        )

        # Source with personal token pre-set: bot must override it.
        proc = subprocess.run(
            [
                "/bin/bash",
                "-c",
                f"export AOPS_BOT_GH_TOKEN={bot} GH_TOKEN={personal} GITHUB_TOKEN={personal}; "
                f"source {temp_env_file}; "
                f'printf "%s\\n%s\\n" "$GH_TOKEN" "$GITHUB_TOKEN"',
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        gh, github = proc.stdout.strip().split("\n")
        assert gh == bot, f"Bot token must override personal; got {gh!r}"
        assert github == bot, f"Bot token must override personal; got {github!r}"


# ---------------------------------------------------------------------------
# E2E: Claude Code headless credential isolation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Subprocess credential isolation (no LLM needed)
# ---------------------------------------------------------------------------


class TestSubprocessCredentialIsolation:
    """Verify apply_env_mappings produces correct env for child processes.

    These tests spawn a simple subprocess (not an LLM) to verify that
    credential mapping works end-to-end through process boundaries.
    """

    def test_subprocess_gets_bot_token(self, credential_markers, tmp_path):
        """A subprocess inheriting mapped env should see GH_TOKEN = bot token."""
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        env = os.environ.copy()
        env["AOPS_BOT_GH_TOKEN"] = bot
        env["GH_TOKEN"] = personal

        # source_env must match env so mappings read our test markers, not real os.environ
        apply_env_mappings(env, source_env=dict(env))

        result = subprocess.run(
            ["printenv", "GH_TOKEN"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        actual_token = result.stdout.strip()
        assert actual_token == bot, (
            f"Credential isolation FAILED.\n"
            f"Expected GH_TOKEN = bot marker: {bot!r}\n"
            f"Got: {actual_token!r}\n"
            f"Personal marker was: {personal!r}"
        )
        assert actual_token != personal, (
            "SECURITY: Subprocess inherited personal token instead of bot token!"
        )

    def test_subprocess_ssh_auth_sock_cleared(self, tmp_path):
        """SSH_AUTH_SOCK should be empty in subprocess env after mapping."""
        env = os.environ.copy()
        env["SSH_AUTH_SOCK"] = "/tmp/fake-ssh-agent.sock"

        apply_env_mappings(env)

        result = subprocess.run(
            ["printenv", "SSH_AUTH_SOCK"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # printenv returns non-zero if var is empty/unset
        actual = result.stdout.strip()
        assert actual == "", f"SSH_AUTH_SOCK should be empty after mapping, got: {actual!r}"

    def test_subprocess_git_terminal_prompt_disabled(self, tmp_path):
        """GIT_TERMINAL_PROMPT should be 0 in subprocess env after mapping."""
        env = os.environ.copy()
        apply_env_mappings(env)

        result = subprocess.run(
            ["printenv", "GIT_TERMINAL_PROMPT"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.stdout.strip() == "0", (
            f"GIT_TERMINAL_PROMPT should be '0', got: {result.stdout.strip()!r}"
        )


# ---------------------------------------------------------------------------
# Deferred-shell exports: handles the macOS-Claude-Desktop case where
# AOPS_BOT_GH_TOKEN is set in the user's shell snapshot (~/.zshenv) but NOT
# in the launchd env that the Python hook sees. The persist dict path silently
# skipped GH_TOKEN/GITHUB_TOKEN; the shell-lines path defers resolution so
# the shell snapshot's value is picked up at source-time.
# ---------------------------------------------------------------------------


class TestDeferredShellLines:
    def test_shell_lines_defer_env_to_env(self):
        """Env-to-env mappings produce shell-conditional exports.

        The condition uses ``${SOURCE:+x}`` (colon-plus) which evaluates to
        ``x`` only if SOURCE is set AND non-empty. This is load-bearing —
        ``${SOURCE+x}`` (without colon) would propagate empty strings and
        re-introduce the credential-leak class closed in task-ebc758fd.
        """
        from lib.agent_env import get_env_mapping_shell_lines

        lines = get_env_mapping_shell_lines()
        gh_line = next((line for line in lines if "GH_TOKEN=" in line), None)
        assert gh_line is not None, "GH_TOKEN export must be present"
        assert "${AOPS_BOT_GH_TOKEN:+x}" in gh_line, (
            "Must use ${SOURCE:+x} (with colon) for set-AND-non-empty check"
        )
        assert "${AOPS_BOT_GH_TOKEN+x}" not in gh_line.replace("${AOPS_BOT_GH_TOKEN:+x}", ""), (
            "Plain ${SOURCE+x} (no colon) would forward empty strings — see task-ebc758fd"
        )
        assert '"${AOPS_BOT_GH_TOKEN}"' in gh_line, (
            "Must reference ${SOURCE} for value (defer to shell)"
        )

    def test_shell_lines_excludes_literals(self):
        """Literals are excluded from shell_lines — they're written by set_persistent_env."""
        from lib.agent_env import get_env_mapping_shell_lines

        lines = get_env_mapping_shell_lines()
        # SSH_AUTH_SOCK is a literal entry; it must NOT appear in deferred lines.
        assert not any("SSH_AUTH_SOCK" in line for line in lines), (
            "Literal entries must be excluded from shell_lines to avoid redundant writes"
        )

    def test_shell_lines_resolve_via_bash(self, credential_markers):
        """Bash-evaluating the shell lines must populate GH_TOKEN/GITHUB_TOKEN.

        Reproduces the macOS-Claude-Desktop scenario: Python hook sees no
        AOPS_BOT_GH_TOKEN, but the shell snapshot does. The deferred lines
        must pick up the shell value when sourced.
        """
        from lib.agent_env import get_env_mapping_shell_lines

        bot = credential_markers["bot"]
        lines = get_env_mapping_shell_lines()
        script = "\n".join(lines)

        # Simulate the shell-snapshot setting AOPS_BOT_GH_TOKEN, then sourcing
        # the deferred-export lines, then printing GH_TOKEN/GITHUB_TOKEN.
        full = f'export AOPS_BOT_GH_TOKEN={bot}\n{script}\nprintf \'%s\\n%s\\n\' "$GH_TOKEN" "$GITHUB_TOKEN"\n'
        result = subprocess.run(
            ["/bin/bash", "-c", full], capture_output=True, text=True, timeout=10, check=True
        )
        gh, github = result.stdout.strip().split("\n")
        assert gh == bot, "GH_TOKEN must resolve to bot value via deferred shell expansion"
        assert github == bot, "GITHUB_TOKEN must resolve too"

    def test_shell_lines_skip_when_source_unset_or_empty(self):
        """When SOURCE is unset OR empty, shell lines must not export TARGET.

        Avoids the regression where GH_TOKEN gets set to empty string,
        causing gh CLI to fall through to keyring auth (or, on the polecat
        path, headless claude sending an empty x-api-key → 401).
        Both "unset" and "set-but-empty" must skip — see task-ebc758fd.
        """
        from lib.agent_env import get_env_mapping_shell_lines

        lines = get_env_mapping_shell_lines()
        script = "\n".join(lines)

        # Both AOPS_BOT_GH_TOKEN AND GH_TOKEN/GITHUB_TOKEN unset upfront so the
        # test is hermetic — runner shells often export GH_TOKEN themselves.
        prologue = "unset AOPS_BOT_GH_TOKEN GH_TOKEN GITHUB_TOKEN"
        epilogue = (
            'printf "GH_TOKEN_SET=%s\\n" "${GH_TOKEN+yes}"; '
            'printf "GITHUB_TOKEN_SET=%s\\n" "${GITHUB_TOKEN+yes}"'
        )

        # Case 1: AOPS_BOT_GH_TOKEN truly unset.
        full = f"{prologue}\n{script}\n{epilogue}\n"
        result = subprocess.run(
            ["/bin/bash", "-c", full], capture_output=True, text=True, timeout=10, check=True
        )
        assert "GH_TOKEN_SET=yes" not in result.stdout, (
            "GH_TOKEN must NOT be exported when AOPS_BOT_GH_TOKEN is unset"
        )
        assert "GITHUB_TOKEN_SET=yes" not in result.stdout

        # Case 2: AOPS_BOT_GH_TOKEN set but empty.
        full_empty = f"{prologue}\nexport AOPS_BOT_GH_TOKEN=\n{script}\n{epilogue}\n"
        result = subprocess.run(
            ["/bin/bash", "-c", full_empty], capture_output=True, text=True, timeout=10, check=True
        )
        assert "GH_TOKEN_SET=yes" not in result.stdout, (
            "GH_TOKEN must NOT be exported when AOPS_BOT_GH_TOKEN is empty"
        )
        assert "GITHUB_TOKEN_SET=yes" not in result.stdout


# ---------------------------------------------------------------------------
# Credential helper override: plugs the host-specific helper precedence bug
# (~/.gitconfig: credential.https://github.com.helper = !gh auth git-credential).
# ---------------------------------------------------------------------------


class TestCredentialHelperOverride:
    def test_session_env_setup_writes_helper_override(self, tmp_path, monkeypatch):
        """SessionStart must write GIT_CONFIG_KEY_2/3 reset+install for github.com helper."""
        env_file = tmp_path / "env.sh"
        env_file.touch()
        monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
        monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "ghp_dummy_for_test")

        ctx = HookContext(
            session_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            hook_event="SessionStart",
            transcript_path="/tmp/test-transcript.jsonl",
            cwd=str(tmp_path),
            raw_input={"source": "startup"},
        )
        state = SessionState.create(session_id=ctx.session_id)
        run_session_env_setup(ctx, state)

        contents = env_file.read_text()
        assert "GIT_CONFIG_COUNT=4" in contents, (
            "GIT_CONFIG_COUNT must be 4 to enable both insteadOf and helper override"
        )
        # Reset entry then install entry — list-typed helper requires reset first
        helper_keys = [
            line
            for line in contents.splitlines()
            if "GIT_CONFIG_KEY_2" in line or "GIT_CONFIG_KEY_3" in line
        ]
        assert len(helper_keys) == 2
        assert all("credential.https://github.com.helper" in line for line in helper_keys)
        # Reset value must be empty
        assert "GIT_CONFIG_VALUE_2=''" in contents
        # Install value must contain the bot-PAT printf
        assert 'printf "username=x-access-token' in contents
        # The helper must read AOPS_BOT_GH_TOKEN *exclusively* — no fallback to
        # GH_TOKEN/GITHUB_TOKEN (which could carry a personal value).
        assert '"${AOPS_BOT_GH_TOKEN}"' in contents, (
            "Helper must reference ${AOPS_BOT_GH_TOKEN} as the sole credential source"
        )
        assert "${GH_TOKEN:-" not in contents, (
            "Helper must NOT fall back to GH_TOKEN/GITHUB_TOKEN (personal-leak vector)"
        )
        # gh CLI must be isolated from the user's keyring via an empty config dir.
        assert "export GH_CONFIG_DIR=" in contents, (
            "Hook must set GH_CONFIG_DIR to isolate gh from the user's keyring"
        )

    def _helper_env(self, tmp_path) -> dict:
        """Build the GIT_CONFIG_* env layer exactly as session_env_setup writes it."""
        env = os.environ.copy()
        env["GIT_CONFIG_COUNT"] = "4"
        env["GIT_CONFIG_KEY_0"] = "url.https://github.com/.insteadOf"
        env["GIT_CONFIG_VALUE_0"] = "git@github.com:"
        env["GIT_CONFIG_KEY_1"] = "url.https://github.com/.insteadOf"
        env["GIT_CONFIG_VALUE_1"] = "ssh://git@github.com/"
        env["GIT_CONFIG_KEY_2"] = "credential.https://github.com.helper"
        env["GIT_CONFIG_VALUE_2"] = ""
        env["GIT_CONFIG_KEY_3"] = "credential.https://github.com.helper"
        env["GIT_CONFIG_VALUE_3"] = (
            '!f() { test "$1" = get && '
            'printf "username=x-access-token\\npassword=%s\\n" '
            '"${AOPS_BOT_GH_TOKEN}"; }; f'
        )
        # Force git to ignore user-config so we test ONLY the GIT_CONFIG_KEY_*
        # env layer — the same layer the hook adds.
        env["HOME"] = str(tmp_path)
        env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
        return env

    def test_helper_resolves_bot_token_exclusively(self, tmp_path, credential_markers):
        """The helper must emit the bot PAT — reading AOPS_BOT_GH_TOKEN only.

        GH_TOKEN/GITHUB_TOKEN are set to a personal marker to prove the helper
        ignores them (no fallback chain).
        """
        bot = credential_markers["bot"]
        personal = credential_markers["personal"]

        env = self._helper_env(tmp_path)
        env["AOPS_BOT_GH_TOKEN"] = bot
        env["GH_TOKEN"] = personal
        env["GITHUB_TOKEN"] = personal

        result = subprocess.run(
            ["git", "credential", "fill"],
            env=env,
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        out = result.stdout
        assert "username=x-access-token" in out, f"Expected x-access-token username; got:\n{out}"
        assert f"password={bot}" in out, "Helper must emit the bot PAT"
        assert personal not in out, "SECURITY: personal token must NOT be emitted by the helper"

    def test_helper_fails_closed_when_bot_token_empty(self, tmp_path):
        """When AOPS_BOT_GH_TOKEN is empty, the helper must emit an EMPTY password
        (fail-closed) rather than any fallback credential."""
        env = self._helper_env(tmp_path)
        env["AOPS_BOT_GH_TOKEN"] = ""
        env["GH_TOKEN"] = "personal_leak"
        env["GITHUB_TOKEN"] = "personal_leak"

        result = subprocess.run(
            ["git", "credential", "fill"],
            env=env,
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        out = result.stdout
        assert "password=\n" in out or out.rstrip().endswith("password="), (
            f"Helper must emit empty password when bot token absent; got:\n{out}"
        )
        assert "personal_leak" not in out, "SECURITY: personal token leaked via helper fallback"


# ---------------------------------------------------------------------------
# Container env-forwarding helper (task-ebc758fd):
# polecat/cli.py:_build_docker_cmd consumes get_container_env_forwards to
# decide what crosses from host into the polecat container with -e flags.
# These tests pin the helper's contract independent of cli.py.
# ---------------------------------------------------------------------------


class TestGetContainerEnvForwards:
    """Tests for get_container_env_forwards: the conf-driven container -e set."""

    def test_literal_passthrough_including_empty(self, tmp_path):
        """`:=` literal entries are forwarded verbatim, including empty literals
        (the SSH_AUTH_SOCK="" isolation idiom).
        """
        from lib.agent_env import get_container_env_forwards

        config = tmp_path / "literals.conf"
        config.write_text(
            "GIT_TERMINAL_PROMPT:=0\nSSH_AUTH_SOCK:=\nGEMINI_CLI_HOME:=/home/worker\n"
        )

        forwards = get_container_env_forwards(source_env={}, config_path=config)

        assert forwards == {
            "GIT_TERMINAL_PROMPT": "0",
            "SSH_AUTH_SOCK": "",
            "GEMINI_CLI_HOME": "/home/worker",
        }

    def test_mapping_skipped_when_source_unset(self, tmp_path):
        """`TARGET=SOURCE` mapping is skipped when SOURCE is not in source_env."""
        from lib.agent_env import get_container_env_forwards

        config = tmp_path / "mapping.conf"
        config.write_text("ANTHROPIC_API_KEY=ANTHROPIC_API_KEY\n")

        forwards = get_container_env_forwards(source_env={}, config_path=config)

        assert "ANTHROPIC_API_KEY" not in forwards

    def test_mapping_skipped_when_source_empty(self, tmp_path):
        """`TARGET=SOURCE` mapping is skipped when SOURCE is set but empty.

        This is the regression closer for task-ebc758fd: a host shell with
        `ANTHROPIC_API_KEY=""` exported must not propagate the empty key.
        """
        from lib.agent_env import get_container_env_forwards

        config = tmp_path / "mapping.conf"
        config.write_text("ANTHROPIC_API_KEY=ANTHROPIC_API_KEY\n")

        forwards = get_container_env_forwards(
            source_env={"ANTHROPIC_API_KEY": ""}, config_path=config
        )

        assert "ANTHROPIC_API_KEY" not in forwards

    def test_mapping_passthrough_when_source_set(self, tmp_path, credential_markers):
        """Happy path: TARGET=SOURCE mapping forwards when source is set and non-empty."""
        from lib.agent_env import get_container_env_forwards

        config = tmp_path / "mapping.conf"
        config.write_text("GH_TOKEN=AOPS_BOT_GH_TOKEN\n")

        forwards = get_container_env_forwards(
            source_env={"AOPS_BOT_GH_TOKEN": credential_markers["bot"]},
            config_path=config,
        )

        assert forwards["GH_TOKEN"] == credential_markers["bot"]

    def test_default_config_includes_claude_and_gemini_auth(self):
        """The bundled agent-env-map.conf must declare Claude/Gemini auth vars,
        so `polecat run` doesn't have to hardcode them.

        CLAUDE_CODE_OAUTH_TOKEN is the ONLY supported Claude auth mechanism —
        the ANTHROPIC_API_KEY fallback was removed (see aops-06ab3ee0). Even
        when a host shell exports ANTHROPIC_API_KEY, the conf must NOT forward
        it into the container.
        """
        from lib.agent_env import get_container_env_forwards

        # Source env has all auth tokens set with sentinel values, including
        # ANTHROPIC_API_KEY — to prove it is deliberately NOT forwarded.
        source = {
            "ANTHROPIC_API_KEY": "sk-anthropic-sentinel",
            "CLAUDE_CODE_OAUTH_TOKEN": "claude-oauth-sentinel",
            "GEMINI_API_KEY": "sk-gemini-sentinel",
            "GEMINI_SESSION_ID": "session-sentinel",
        }
        forwards = get_container_env_forwards(source_env=source)

        assert forwards["CLAUDE_CODE_OAUTH_TOKEN"] == "claude-oauth-sentinel"
        assert forwards["GEMINI_API_KEY"] == "sk-gemini-sentinel"
        assert forwards["GEMINI_SESSION_ID"] == "session-sentinel"
        # ANTHROPIC_API_KEY fallback removed (aops-06ab3ee0) — must NOT be
        # forwarded even when set in the host env.
        assert "ANTHROPIC_API_KEY" not in forwards
        # SSH isolation idiom must survive any refactor.
        assert forwards["SSH_AUTH_SOCK"] == ""
        # Defence-in-depth literal.
        assert forwards["GIT_ASKPASS"] == "true"
