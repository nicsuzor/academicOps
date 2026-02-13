#!/usr/bin/env python3
"""Tests for session_env_setup.py hook.

Tests environment variable setup logic for SessionStart hook:
- PYTHONPATH addition to CLAUDE_ENV_FILE
- AOPS_SESSION_STATE_DIR persistence
- Default enforcement modes
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


class TestSessionEnvSetup:
    """Test environment setup logic."""

    @pytest.fixture
    def temp_env_file(self, tmp_path):
        """Create a temporary CLAUDE_ENV_FILE."""
        env_file = tmp_path / "claude_env"
        env_file.touch()
        with patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file)}):
            yield env_file

    def test_run_session_env_setup_persists_variables(self, temp_env_file):
        """Test that run_session_env_setup persists required variables."""
        ctx = HookContext(session_id="test-session-123", hook_event="SessionStart", raw_input={})

        # We need to mock get_session_status_dir to return a consistent path
        with patch(
            "hooks.session_env_setup.get_session_status_dir",
            return_value="/tmp/aops/sessions",
        ):
            run_session_env_setup(ctx)

        content = temp_env_file.read_text()

        # Verify Session ID
        assert 'export CLAUDE_SESSION_ID="test-session-123"' in content

        # Verify PYTHONPATH
        assert 'export PYTHONPATH="' in content
        assert "aops-core" in content

        # Verify AOPS_SESSION_STATE_DIR
        assert 'export AOPS_SESSION_STATE_DIR="/tmp/aops/sessions"' in content

        # Verify enforcement modes
        assert "export CUSTODIET_MODE=" in content
        assert "export TASK_GATE_MODE=" in content
        assert "export HYDRATION_GATE_MODE=" in content

    def test_run_session_env_setup_ignored_for_other_events(self, temp_env_file):
        """Verify setup is ignored for non-SessionStart events."""
        ctx = HookContext(session_id="test-session-123", hook_event="PreToolUse", raw_input={})

        result = run_session_env_setup(ctx)
        assert result is None

        content = temp_env_file.read_text()
        assert content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
