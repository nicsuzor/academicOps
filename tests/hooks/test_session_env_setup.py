#!/usr/bin/env python3
"""Tests for session_env_setup.py hook.

Tests environment variable setup logic for SessionStart hook:
- PYTHONPATH addition to CLAUDE_ENV_FILE
- AOPS_SESSION_STATE_DIR persistence
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import HookContext
from hooks.session_env_setup import run_session_env_setup
from lib.session_state import SessionState


class TestSessionEnvSetup:
    """Test environment setup logic."""

    @pytest.fixture(autouse=True)
    def _mock_home(self, monkeypatch, tmp_path):
        """Mock home to tmp_path."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

    @pytest.fixture
    def temp_env_file(self, tmp_path):
        """Create a temporary CLAUDE_ENV_FILE."""
        env_file = tmp_path / "claude_env"
        env_file.touch()
        with patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file), "PYTHONPATH": ""}):
            yield env_file

    def test_run_session_env_setup_persists_variables(self, temp_env_file):
        """Test that run_session_env_setup persists required variables."""
        ctx = HookContext(
            session_id="test-session-123",
            client_type="claude",
            session_short_hash="abc12345",
            hook_event="SessionStart",
            raw_input={},
        )

        # We need to mock get_session_status_dir to return a consistent path
        state = SessionState.create(ctx.session_id, client_type="claude")
        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value="/tmp/aops/sessions",
        ):
            run_session_env_setup(ctx, state)

        content = temp_env_file.read_text()

        # Verify Session ID (shlex.quote leaves shell-safe strings unquoted)
        assert "export AOPS_SESSION_ID=test-session-123" in content

        # Verify PYTHONPATH
        assert "export PYTHONPATH=" in content
        assert "aops-core" in content

        # Verify AOPS_SESSION_STATE_DIR
        assert "export AOPS_SESSION_STATE_DIR=/tmp/aops/sessions" in content

        # Gate modes now live in $AOPS_SESSIONS/polecat.yaml and are read by
        # hooks at runtime; they are no longer persisted as env vars at all.
        assert "ENFORCER_GATE_MODE" not in content
        assert "QA_GATE_MODE" not in content
        assert "HANDOVER_GATE_MODE" not in content
        assert "HYDRATION_GATE_MODE" not in content

    def test_run_session_env_setup_does_not_persist_gate_modes(self, tmp_path):
        """Gate modes are no longer env-var persisted: hooks read polecat.yaml.

        Replaces the legacy test that asserted gate-mode defaults were written
        into CLAUDE_ENV_FILE for non-shell runtimes (macOS app). With config
        as the SSoT, persistence is unnecessary — every hook re-reads the
        YAML at first access.
        """
        env_file = tmp_path / "claude_env"
        env_file.touch()
        env_overrides = {"CLAUDE_ENV_FILE": str(env_file), "PYTHONPATH": ""}
        ctx = HookContext(
            session_id="test-session-456",
            client_type="claude",
            session_short_hash="def56789",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")
        with (
            patch.dict("os.environ", env_overrides, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value="/tmp/aops/sessions",
            ),
        ):
            run_session_env_setup(ctx, state)

        content = env_file.read_text()
        for var in (
            "HANDOVER_GATE_MODE",
            "QA_GATE_MODE",
            "ENFORCER_GATE_MODE",
            "HYDRATION_GATE_MODE",
            "IDA_GATE_MODE",
            "ENFORCER_TOOL_CALL_THRESHOLD",
        ):
            assert var not in content, (
                f"{var} must not be persisted: gate modes live in polecat.yaml now"
            )

    def test_oauth_tokens_not_persisted_to_env_file(self, tmp_path):
        """OAuth trust boundary (PKB note-b5347f83, Q2): even when the OAuth
        tokens are present in the source env, the SessionStart hook must NOT
        write them to CLAUDE_ENV_FILE. A general agent (junior) never holds
        these in its own session env; the polecat launcher resolves them from
        ~/.env.local. This is the leak-closure regression guard.
        """
        env_file = tmp_path / "claude_env"
        env_file.touch()
        env_overrides = {
            "CLAUDE_ENV_FILE": str(env_file),
            "PYTHONPATH": "",
            # Both OAuth tokens present in the launching env...
            "CLAUDE_CODE_OAUTH_TOKEN": "sk-oauth-should-not-leak",
            "GEMINI_API_KEY": "gem-should-not-leak",
        }
        ctx = HookContext(
            session_id="test-session-oauth",
            client_type="claude",
            session_short_hash="oauth123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")
        with (
            patch.dict("os.environ", env_overrides, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=str(tmp_path),
            ),
        ):
            result = run_session_env_setup(ctx, state)

        content = env_file.read_text()
        # ...but neither the names nor the secret values reach CLAUDE_ENV_FILE.
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in content
        assert "GEMINI_API_KEY" not in content
        assert "sk-oauth-should-not-leak" not in content
        assert "gem-should-not-leak" not in content
        # And the metadata records they were not persisted.
        persisted = result.metadata["persisted_vars"]
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in persisted
        assert "GEMINI_API_KEY" not in persisted

    def test_provisioning_block_rendered_on_host(self, tmp_path):
        """Q1: SessionStart renders a prominent provisioning block. With the
        full required set present it must be the SUCCESS block; missing the bot
        token it must be the FAILURE block — and the verdict stays ALLOW.
        """
        env_file = tmp_path / "claude_env"
        env_file.touch()
        base = {
            "CLAUDE_ENV_FILE": str(env_file),
            "PYTHONPATH": "",
            "ACA_DATA": "/home/x/brain",
            "AOPS": "/home/x/src/academicOps",
            "AOPS_SESSIONS": "/home/x/.polecat/sessions",
            "PKB_MCP_URL": "http://services:8026/mcp",
            "AOPS_BOT_GH_TOKEN": "ghp_present",
            "GITHUB_ACTIONS": "",
            # Isolate the host secret store: the FAILURE path drops
            # AOPS_BOT_GH_TOKEN, but provisioning falls back to
            # load_host_secrets() (real ~/.env.local) which would resurrect it
            # and mask the "missing" case. Point at a nonexistent file so the
            # fallback resolves to {} regardless of import-order home mocking.
            "AOPS_HOST_ENV_FILE": str(tmp_path / "no-env-local"),
            # Resolved provider set is injected as env (host/container contract);
            # empty ⇒ no external agents, so session_naming uses builtins only and
            # never reaches for the (absent, sandboxed) polecat.yaml.
            "AOPS_ENABLED_PROVIDERS": "",
        }
        ctx = HookContext(
            session_id="test-session-prov",
            client_type="claude",
            session_short_hash="prov1234",
            hook_event="SessionStart",
            raw_input={},
        )

        # SUCCESS path.
        state = SessionState.create(ctx.session_id, client_type="claude")
        with (
            patch.dict("os.environ", base, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=str(tmp_path),
            ),
        ):
            result_ok = run_session_env_setup(ctx, state)
        assert result_ok.verdict.name == "ALLOW"
        assert "ENV OK" in result_ok.system_message
        assert result_ok.metadata["provision_ok"] is True
        assert result_ok.metadata["provision_surface"] == "host"

        # FAILURE path: drop the bot token. Must remain ALLOW (never brick the
        # session needed to fix the var), but render the FAILURE block.
        env_file.write_text("")
        no_bot = dict(base)
        no_bot.pop("AOPS_BOT_GH_TOKEN")
        # Clear AOPS_BOT_GH_TOKEN if the real shell exported it.
        with (
            patch.dict("os.environ", no_bot, clear=True),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=str(tmp_path),
            ),
        ):
            result_fail = run_session_env_setup(ctx, state)
        assert result_fail.verdict.name == "ALLOW"
        assert "ENV INCOMPLETE" in result_fail.system_message
        assert result_fail.metadata["provision_ok"] is False
        assert "AOPS_BOT_GH_TOKEN" in result_fail.metadata["provision_missing"]

    def test_gha_surface_skips_provisioning(self, tmp_path):
        """GHA surface: provisioning is skipped (Actions injects secrets). The
        required-var check must not fire even with none of the host vars set."""
        env_file = tmp_path / "claude_env"
        env_file.touch()
        ctx = HookContext(
            session_id="test-session-gha",
            client_type="claude",
            session_short_hash="gha12345",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")
        with (
            patch.dict(
                "os.environ",
                {
                    "CLAUDE_ENV_FILE": str(env_file),
                    "PYTHONPATH": "",
                    "GITHUB_ACTIONS": "true",
                    "AOPS_ENABLED_PROVIDERS": "",
                },
                clear=True,
            ),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=str(tmp_path),
            ),
        ):
            result = run_session_env_setup(ctx, state)
        assert result.verdict.name == "ALLOW"
        assert result.metadata["provision_surface"] == "gha"
        assert result.metadata["provision_ok"] is True
        assert "provisioning skipped" in result.system_message

    def test_run_session_env_setup_ignored_for_other_events(self, temp_env_file):
        """Verify setup is ignored for non-SessionStart events."""
        ctx = HookContext(
            session_id="test-session-123",
            client_type="claude",
            session_short_hash="abc12345",
            hook_event="PreToolUse",
            raw_input={},
        )

        state = SessionState.create(ctx.session_id, client_type="claude")
        result = run_session_env_setup(ctx, state)
        assert result is None

        content = temp_env_file.read_text()
        assert content == ""

    def test_creates_daily_note_in_aca_data_daily(self, monkeypatch, tmp_path):
        """Verify today's daily note is created if missing in ACA_DATA/daily."""
        aca_data = tmp_path / "data"
        aca_data.mkdir()
        monkeypatch.setenv("ACA_DATA", str(aca_data))

        ctx = HookContext(
            session_id="test-session-daily",
            client_type="claude",
            session_short_hash="daily123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")

        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value=str(tmp_path),
        ):
            result = run_session_env_setup(ctx, state)

        # Verify daily note was created in ACA_DATA/daily
        today_compact = datetime.now().strftime("%Y%m%d")
        daily_note = aca_data / "daily" / f"{today_compact}-daily.md"

        assert daily_note.exists()
        assert f"Daily Summary - {datetime.now().strftime('%Y-%m-%d')}" in daily_note.read_text()
        assert "Daily note: Created" in result.system_message

    def test_creates_daily_note_in_brain_daily(self, monkeypatch, tmp_path):
        """Verify today's daily note is created in brain/daily if it exists."""
        aca_data = tmp_path / "data"
        brain_daily = aca_data / "brain" / "daily"
        brain_daily.mkdir(parents=True)
        monkeypatch.setenv("ACA_DATA", str(aca_data))

        ctx = HookContext(
            session_id="test-session-brain",
            client_type="claude",
            session_short_hash="brain123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")

        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value=str(tmp_path),
        ):
            result = run_session_env_setup(ctx, state)

        # Verify daily note was created in ACA_DATA/brain/daily
        today_compact = datetime.now().strftime("%Y%m%d")
        daily_note = brain_daily / f"{today_compact}-daily.md"

        assert daily_note.exists()
        assert "Daily note: Created" in result.system_message
        assert not (aca_data / "daily").exists(), (
            "Should not create ACA_DATA/daily if brain/daily exists"
        )

    def test_reports_existing_daily_note(self, monkeypatch, tmp_path):
        """Verify it reports existing daily note without re-creating."""
        aca_data = tmp_path / "data"
        daily_dir = aca_data / "daily"
        daily_dir.mkdir(parents=True)
        today_compact = datetime.now().strftime("%Y%m%d")
        daily_note = daily_dir / f"{today_compact}-daily.md"
        original_content = "Existing daily note"
        daily_note.write_text(original_content)

        monkeypatch.setenv("ACA_DATA", str(aca_data))

        ctx = HookContext(
            session_id="test-session-existing",
            client_type="claude",
            session_short_hash="ext12345",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")

        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value=str(tmp_path),
        ):
            result = run_session_env_setup(ctx, state)

        assert daily_note.read_text() == original_content
        assert f"Daily note: {today_compact}-daily.md" in result.system_message
        assert "Created" not in result.system_message

    def test_restores_committed_note_instead_of_writing_stub(self, monkeypatch, tmp_path):
        """If the working-tree note is missing but a POPULATED version exists in
        git HEAD (transient mid-sync absence / fresh checkout), restore it rather
        than scaffolding a stub — the stub would diverge and can clobber the
        populated note on the next merge (#1739)."""
        import os
        import subprocess

        aca_data = tmp_path / "data"
        (aca_data / "daily").mkdir(parents=True)
        monkeypatch.setenv("ACA_DATA", str(aca_data))

        today_compact = datetime.now().strftime("%Y%m%d")
        rel = f"daily/{today_compact}-daily.md"
        note = aca_data / rel
        populated = (
            f"# Daily Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            "Real populated content — must not be lost.\n"
        )
        note.write_text(populated)

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        for cmd in (
            ["git", "init", "-q"],
            ["git", "add", rel],
            ["git", "commit", "-q", "-m", "populated note"],
        ):
            subprocess.run(cmd, cwd=aca_data, env=env, check=True, capture_output=True)

        # Transient-absence window: working tree file gone, HEAD still has it.
        note.unlink()
        assert not note.exists()

        ctx = HookContext(
            session_id="test-session-restore",
            client_type="claude",
            session_short_hash="rest1234",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id, client_type="claude")

        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value=str(tmp_path),
        ):
            result = run_session_env_setup(ctx, state)

        assert note.exists(), "note should be restored from HEAD, not left missing"
        assert note.read_text() == populated, "must restore populated content, not a stub"
        assert "has not been populated yet" not in note.read_text()
        assert "restored" in result.system_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
