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
            session_short_hash="abc12345",
            hook_event="SessionStart",
            raw_input={},
        )

        # We need to mock get_session_status_dir to return a consistent path
        state = SessionState.create(ctx.session_id)
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
            session_short_hash="def56789",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)
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
            "ENFORCER_TOOL_CALL_THRESHOLD",
        ):
            assert var not in content, (
                f"{var} must not be persisted: gate modes live in polecat.yaml now"
            )

    def test_run_session_env_setup_ignored_for_other_events(self, temp_env_file):
        """Verify setup is ignored for non-SessionStart events."""
        ctx = HookContext(
            session_id="test-session-123",
            session_short_hash="abc12345",
            hook_event="PreToolUse",
            raw_input={},
        )

        state = SessionState.create(ctx.session_id)
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
            session_short_hash="daily123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

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
            session_short_hash="brain123",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

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
            session_short_hash="ext12345",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value=str(tmp_path),
        ):
            result = run_session_env_setup(ctx, state)

        assert daily_note.read_text() == original_content
        assert f"Daily note: {today_compact}-daily.md" in result.system_message
        assert "Created" not in result.system_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
