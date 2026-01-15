#!/usr/bin/env python3
"""Tests for hydration_gate.py hook.

Tests the hydration gate's bypass logic for subagents, CLI invocations,
and hydrator spawning, as well as blocking/warning behavior.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from hydration_gate import (
    get_session_id,
    is_first_prompt_from_cli,
    is_hydrator_task,
    is_subagent_session,
    main,
)


class TestSubagentDetection:
    """Test is_subagent_session logic."""

    def test_subagent_when_env_var_set(self, monkeypatch):
        """Test that CLAUDE_AGENT_TYPE env var triggers subagent detection."""
        monkeypatch.setenv("CLAUDE_AGENT_TYPE", "prompt-hydrator")
        assert is_subagent_session() is True

    def test_subagent_with_different_agent_type(self, monkeypatch):
        """Test that any CLAUDE_AGENT_TYPE value triggers detection."""
        monkeypatch.setenv("CLAUDE_AGENT_TYPE", "worker")
        assert is_subagent_session() is True

    def test_not_subagent_when_env_var_missing(self, monkeypatch):
        """Test that missing CLAUDE_AGENT_TYPE means not a subagent."""
        monkeypatch.delenv("CLAUDE_AGENT_TYPE", raising=False)
        assert is_subagent_session() is False

    def test_not_subagent_when_env_var_empty(self, monkeypatch):
        """Test that empty CLAUDE_AGENT_TYPE means not a subagent."""
        monkeypatch.setenv("CLAUDE_AGENT_TYPE", "")
        assert is_subagent_session() is False


class TestSessionIdExtraction:
    """Test get_session_id logic."""

    def test_session_id_from_input_data(self):
        """Test extracting session ID from hook input data."""
        input_data = {"session_id": "abc123"}
        assert get_session_id(input_data) == "abc123"

    def test_session_id_from_env_var(self, monkeypatch):
        """Test fallback to CLAUDE_SESSION_ID env var."""
        monkeypatch.setenv("CLAUDE_SESSION_ID", "xyz789")
        input_data = {}
        assert get_session_id(input_data) == "xyz789"

    def test_session_id_prefers_input_data(self, monkeypatch):
        """Test that input data takes precedence over env var."""
        monkeypatch.setenv("CLAUDE_SESSION_ID", "from-env")
        input_data = {"session_id": "from-input"}
        assert get_session_id(input_data) == "from-input"

    def test_session_id_empty_when_missing(self):
        """Test that missing session ID returns empty string."""
        input_data = {}
        assert get_session_id(input_data) == ""


class TestFirstPromptDetection:
    """Test is_first_prompt_from_cli logic."""

    def test_first_prompt_when_no_session_state(self):
        """Test that missing session state indicates first prompt."""
        with patch("hydration_gate.load_session_state", return_value=None):
            assert is_first_prompt_from_cli("test-session") is True

    def test_not_first_prompt_when_session_state_exists(self):
        """Test that existing session state indicates not first prompt."""
        with patch("hydration_gate.load_session_state", return_value={"some": "state"}):
            assert is_first_prompt_from_cli("test-session") is False

    def test_not_first_prompt_when_no_session_id(self):
        """Test that missing session ID returns False."""
        assert is_first_prompt_from_cli("") is False


class TestHydratorTaskDetection:
    """Test is_hydrator_task logic."""

    def test_hydrator_task_when_subagent_type_matches(self):
        """Test that subagent_type='prompt-hydrator' is detected."""
        tool_input = {"subagent_type": "prompt-hydrator"}
        assert is_hydrator_task(tool_input) is True

    def test_not_hydrator_task_when_different_subagent(self):
        """Test that other subagent types are not detected as hydrator."""
        tool_input = {"subagent_type": "worker"}
        assert is_hydrator_task(tool_input) is False

    def test_not_hydrator_task_when_subagent_type_missing(self):
        """Test that missing subagent_type is not detected as hydrator."""
        tool_input = {}
        assert is_hydrator_task(tool_input) is False


class TestGateBypass:
    """Test the main gate bypass logic."""

    def test_bypass_for_subagent_session(self, monkeypatch, capsys):
        """CRITICAL: Test that subagents always bypass the gate."""
        import io

        # Set up subagent environment
        monkeypatch.setenv("CLAUDE_AGENT_TYPE", "worker")

        # Create input with hydration pending (gate should bypass anyway)
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock session state to indicate hydration is pending
        with patch("hydration_gate.is_hydration_pending", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 0 (allow) despite hydration pending
            assert exc_info.value.code == 0

            # Should output empty JSON (allow)
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {}

            # No warning/block message in stderr
            assert "HYDRATION GATE" not in captured.err

    def test_bypass_for_first_prompt_from_cli(self, monkeypatch, capsys):
        """Test that first prompt from CLI bypasses the gate."""
        import io

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "session_id": "new-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock to indicate this is first prompt (no session state)
        with patch("hydration_gate.is_first_prompt_from_cli", return_value=True), patch(
            "hydration_gate.is_hydration_pending", return_value=True
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 0 (allow)
            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {}

    def test_bypass_when_spawning_hydrator(self, monkeypatch, capsys):
        """Test that Task calls spawning hydrator clear the gate."""
        import io

        input_data = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "prompt-hydrator", "prompt": "test"},
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock to indicate hydration is pending
        with patch("hydration_gate.is_hydration_pending", return_value=True), patch(
            "hydration_gate.clear_hydration_pending"
        ) as mock_clear:
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 0 (allow)
            assert exc_info.value.code == 0

            # Should clear the gate
            mock_clear.assert_called_once_with("test-session")

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {}

    def test_bypass_when_hydration_not_pending(self, monkeypatch, capsys):
        """Test that tools are allowed when hydration is not pending."""
        import io

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock to indicate hydration is NOT pending
        with patch("hydration_gate.is_hydration_pending", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 0 (allow)
            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {}


class TestGateEnforcement:
    """Test gate enforcement in warn and block modes."""

    def test_warn_mode_allows_with_warning(self, monkeypatch, capsys):
        """Test that warn mode (default) logs warning but allows."""
        import io

        monkeypatch.setenv("HYDRATION_GATE_MODE", "warn")

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock to indicate hydration is pending and no bypass conditions
        with patch("hydration_gate.is_hydration_pending", return_value=True), patch(
            "hydration_gate.is_subagent_session", return_value=False
        ), patch("hydration_gate.is_first_prompt_from_cli", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 0 (allow in warn mode)
            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {}

            # Should have warning in stderr
            assert "⚠️  HYDRATION GATE (warn-only)" in captured.err
            assert "warn mode" in captured.err.lower()

    def test_block_mode_blocks_with_error(self, monkeypatch, capsys):
        """Test that block mode exits with code 2 to block tool."""
        import io

        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock to indicate hydration is pending and no bypass conditions
        with patch("hydration_gate.is_hydration_pending", return_value=True), patch(
            "hydration_gate.is_subagent_session", return_value=False
        ), patch("hydration_gate.is_first_prompt_from_cli", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit 2 (block)
            assert exc_info.value.code == 2

            captured = capsys.readouterr()
            # Should have block message in stderr
            assert "⛔ HYDRATION GATE" in captured.err
            assert "MANDATORY" in captured.err


class TestFailOpen:
    """Test fail-open behavior on errors."""

    def test_fail_open_on_json_parse_error(self, monkeypatch, capsys):
        """Test that invalid JSON input results in exit 0 (allow)."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("not valid json"))

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit 0 (fail-open)
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {}

    def test_fail_open_on_missing_session_id(self, monkeypatch, capsys):
        """Test that missing session ID results in exit 0 (allow)."""
        import io

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            # No session_id
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit 0 (fail-open)
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
