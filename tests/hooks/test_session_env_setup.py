#!/usr/bin/env python3
"""Tests for session_env_setup.py hook.

Tests environment variable setup logic for SessionStart hook:
- PYTHONPATH addition to CLAUDE_ENV_FILE
- AOPS_SESSION_STATE_DIR persistence
"""

import sys
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
        assert "export CLAUDE_SESSION_ID=test-session-123" in content

        # Verify PYTHONPATH
        assert "export PYTHONPATH=" in content
        assert "aops-core" in content

        # Verify AOPS_SESSION_STATE_DIR
        assert "export AOPS_SESSION_STATE_DIR=/tmp/aops/sessions" in content

        # Gate mode env vars are set in pytest.ini_options env, so they are
        # already in the environment — the hook should NOT re-persist them.
        assert "CUSTODIET_GATE_MODE" not in content
        assert "HYDRATION_GATE_MODE" not in content
        assert "QA_GATE_MODE" not in content
        assert "HANDOVER_GATE_MODE" not in content

    def test_run_session_env_setup_persists_gate_mode_defaults_when_missing(self, tmp_path):
        """When gate mode env vars are absent, defaults should be persisted via CLAUDE_ENV_FILE.

        This covers the non-shell runtime case (Claude macOS app, Cowork) where
        ~/.env.local is not sourced and gate mode vars are missing from the environment.
        """
        env_file = tmp_path / "claude_env"
        env_file.touch()
        gate_vars = [
            "HANDOVER_GATE_MODE",
            "QA_GATE_MODE",
            "CUSTODIET_GATE_MODE",
            "HYDRATION_GATE_MODE",
            "COMMIT_GATE_MODE",
        ]
        # Set gate mode vars to "" to simulate them being absent.
        # os.environ.get(var) returns "" which is falsy, triggering persistence.
        env_overrides = {"CLAUDE_ENV_FILE": str(env_file), "PYTHONPATH": ""}
        for var in gate_vars:
            env_overrides[var] = ""

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
        # Gate mode defaults should have been written since vars were absent.
        for var in gate_vars:
            assert var in content, f"{var} should be persisted when missing from env"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
