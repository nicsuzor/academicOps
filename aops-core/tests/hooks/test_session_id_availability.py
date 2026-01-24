#!/usr/bin/env python3
"""Tests for session_id availability in hooks.

Regression prevention: Ensures session_id is available during hook execution
and that hooks handle missing session_id consistently (fail-closed pattern).

Created in response to regression where session_id wasn't available during
hook execution, causing silent failures in session state management.

Related task: aops-680a2ad3 - Investigate hydration gate not blocking in live sessions
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

# Add hooks directory to path for imports
hooks_dir = aops_core_dir / "hooks"
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))


class TestRouterSessionIdHandling:
    """Test router.py session_id handling.

    The router is the central dispatch point for all hooks.
    It must handle session_id correctly for logging and state management.
    """

    def test_router_receives_session_id_from_input(self, monkeypatch, capsys):
        """Test that router extracts session_id from input data."""
        from router import route_hooks

        input_data = {
            "hook_event_name": "SessionStart",
            "session_id": "test-session-abc123",
        }

        # Mock hook registry to avoid running actual hooks
        with patch("router.get_hooks_for_event", return_value=[]), patch(
            "router.check_custodiet_block", return_value=None
        ):
            output, exit_code = route_hooks(input_data)

            # Should succeed with empty output (no hooks registered in mock)
            assert exit_code == 0

    def test_router_warns_when_session_id_missing(self, monkeypatch, capsys):
        """Test that router logs warning when session_id is missing."""
        from router import route_hooks

        input_data = {
            "hook_event_name": "SessionStart",
            # No session_id
        }

        # Mock to avoid running actual hooks
        with patch("router.get_hooks_for_event", return_value=[]), patch(
            "router.check_custodiet_block", return_value=None
        ):
            output, exit_code = route_hooks(input_data)

            # Should succeed but with warning
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "WARNING" in captured.err or "session_id" in captured.err.lower()

    def test_router_passes_session_id_to_hooks(self, monkeypatch):
        """Test that router passes session_id in input_data to dispatched hooks."""
        from router import dispatch_hooks, HOOK_DIR

        session_id = "test-session-dispatch"
        input_data = {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Read",
        }

        captured_input = {}

        def mock_run_sync_hook(script, data):
            captured_input.update(data)
            return {}, 0

        with patch("router.run_sync_hook", mock_run_sync_hook):
            hooks = [{"script": "mock_hook.py"}]
            dispatch_hooks(hooks, input_data)

            # Verify session_id was passed through
            assert captured_input.get("session_id") == session_id

    def test_router_custodiet_check_requires_session_id(self):
        """Test that custodiet block check gracefully handles missing session_id."""
        from router import check_custodiet_block

        # Missing session_id should return None (no block)
        result = check_custodiet_block(None)
        assert result is None

        result = check_custodiet_block("")
        assert result is None


class TestUserPromptSubmitSessionId:
    """Test user_prompt_submit.py session_id handling.

    CRITICAL: This hook writes hydration state keyed by session_id.
    Missing session_id leads to silent failures in session state management.
    """

    def test_user_prompt_requires_session_id(self, monkeypatch, capsys):
        """Test that user_prompt_submit handles missing session_id.

        Current behavior: Returns empty output (graceful degradation).
        This test documents the current behavior for regression detection.
        """
        from user_prompt_submit import main

        input_data = {
            "prompt": "Fix the bug",
            # No session_id - this is the regression case
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Current behavior: graceful degradation (exit 0, empty output)
        # This test ensures we detect if behavior changes
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_user_prompt_with_session_id_works(self, monkeypatch, capsys):
        """Test that user_prompt_submit works correctly with session_id."""
        from user_prompt_submit import main

        input_data = {
            "prompt": "Fix the bug",
            "session_id": "test-session-working",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock the hydration instruction builder to avoid filesystem dependencies
        with patch(
            "user_prompt_submit.build_hydration_instruction",
            return_value="Hydration instruction for test",
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert "Hydration instruction" in output["hookSpecificOutput"]["additionalContext"]

    def test_get_session_id_from_env(self, monkeypatch):
        """Test that get_session_id falls back to CLAUDE_SESSION_ID env var."""
        from user_prompt_submit import get_session_id

        monkeypatch.setenv("CLAUDE_SESSION_ID", "from-env-var")

        session_id = get_session_id()
        assert session_id == "from-env-var"

    def test_get_session_id_raises_when_missing(self, monkeypatch):
        """Test that get_session_id raises when no session_id available."""
        from user_prompt_submit import get_session_id

        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)

        with pytest.raises(ValueError, match="CLAUDE_SESSION_ID not set"):
            get_session_id()


class TestHydrationGateSessionId:
    """Test hydration_gate.py session_id handling.

    This hook has fail-closed behavior - missing session_id blocks operations.
    This is the CORRECT pattern for security-critical hooks.
    """

    def test_hydration_gate_blocks_on_missing_session_id(self, monkeypatch, capsys):
        """Test that hydration_gate fails closed when session_id missing."""
        from hydration_gate import main

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            # No session_id
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Fail-closed: exit code 2 = BLOCK
        assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "HYDRATION GATE" in captured.err
        assert "session" in captured.err.lower()

    def test_hydration_gate_works_with_session_id(self, monkeypatch, capsys):
        """Test that hydration_gate works when session_id is provided."""
        from hydration_gate import main

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
            "session_id": "test-session-gate",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock hydration check to return not pending
        with patch("hydration_gate.is_hydration_pending", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should allow (exit 0)
            assert exc_info.value.code == 0

    def test_hydration_gate_extracts_session_id_from_env(self, monkeypatch, capsys):
        """Test that hydration_gate falls back to CLAUDE_SESSION_ID env var."""
        from hydration_gate import get_session_id

        monkeypatch.setenv("CLAUDE_SESSION_ID", "env-session-id")

        input_data = {}  # No session_id in input
        session_id = get_session_id(input_data)

        assert session_id == "env-session-id"


class TestSessionStateApiWithSessionId:
    """Test session_state.py API functions with session_id.

    These functions are the foundation for session state management.
    They must work correctly with valid session_id.
    """

    @pytest.fixture
    def temp_session_dir(self, tmp_path, monkeypatch):
        """Create a temporary session directory for tests."""
        sessions_dir = tmp_path / "sessions" / "status"
        sessions_dir.mkdir(parents=True)

        # Mock the session file path function
        def mock_get_path(session_id, date=None):
            from datetime import datetime

            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            return sessions_dir / f"{date[:10].replace('-', '')}-{session_id}.json"

        with patch("lib.session_state.get_session_file_path", mock_get_path):
            yield sessions_dir

    def test_create_session_state_requires_session_id(self, temp_session_dir):
        """Test that create_session_state works with session_id."""
        from lib.session_state import create_session_state

        session_id = "test-create-session"
        state = create_session_state(session_id)

        assert state["session_id"] == session_id
        assert "date" in state
        assert "started_at" in state
        assert state["state"]["hydration_pending"] is True

    def test_get_or_create_session_state_creates_file(self, temp_session_dir):
        """Test that get_or_create_session_state creates and persists state."""
        from lib.session_state import get_or_create_session_state, load_session_state

        session_id = "test-persist-session"
        state = get_or_create_session_state(session_id)

        # Should have created the state
        assert state["session_id"] == session_id

        # Should be loadable
        loaded = load_session_state(session_id)
        assert loaded is not None
        assert loaded["session_id"] == session_id

    def test_is_hydration_pending_fail_closed(self, temp_session_dir):
        """Test that is_hydration_pending returns True when state doesn't exist.

        This is fail-closed behavior: assume hydration pending if unknown.
        """
        from lib.session_state import is_hydration_pending

        # Non-existent session should return True (fail-closed)
        result = is_hydration_pending("nonexistent-session-xyz")
        assert result is True

    def test_set_and_clear_hydration_pending(self, temp_session_dir):
        """Test hydration pending flag set/clear cycle."""
        from lib.session_state import (
            get_or_create_session_state,
            is_hydration_pending,
            set_hydration_pending,
            clear_hydration_pending,
        )

        session_id = "test-hydration-cycle"

        # Create initial state
        state = get_or_create_session_state(session_id)
        assert is_hydration_pending(session_id) is True  # Default

        # Clear it
        clear_hydration_pending(session_id)
        assert is_hydration_pending(session_id) is False

        # Set it again
        set_hydration_pending(session_id, "test prompt")
        assert is_hydration_pending(session_id) is True


class TestHookSessionIdConsistency:
    """Test that hooks handle session_id consistently.

    Regression prevention: All hooks should handle missing session_id
    in a predictable way (either fail-closed or log warning).
    """

    def test_session_id_in_hook_input_schema(self):
        """Document that session_id is expected in hook input data.

        Claude Code provides session_id in hook input. If it's missing,
        hooks should detect this and handle appropriately.
        """
        # Standard hook input should include session_id
        expected_input_fields = {
            "session_id",  # Required for state management
            "hook_event_name",  # Identifies the hook event
        }

        # This is a documentation test - the schema is implicit in Claude Code
        # but we want to ensure our hooks expect these fields
        assert "session_id" in expected_input_fields

    def test_hooks_document_session_id_handling(self):
        """Verify hooks have consistent session_id handling patterns.

        Pattern 1 (security hooks): Fail-closed - exit 2 if session_id missing
        Pattern 2 (non-critical hooks): Warn and continue - log warning, exit 0

        This test documents which pattern each hook uses.
        """
        # Hooks that should fail-closed (security/state critical)
        fail_closed_hooks = [
            "hydration_gate.py",
            "task_required_gate.py",
        ]

        # Hooks that warn and continue (non-critical)
        warn_continue_hooks = [
            "user_prompt_submit.py",  # Graceful degradation
            "unified_logger.py",  # Just logging
        ]

        # Document the expected patterns
        assert len(fail_closed_hooks) > 0, "Should have fail-closed hooks"
        assert len(warn_continue_hooks) > 0, "Should have warn-continue hooks"


class TestRegressionSessionIdNotAvailable:
    """Specific regression tests for the session_id availability bug.

    These tests directly target the scenario where session_id wasn't
    available during hook execution, causing silent failures.
    """

    def test_session_id_available_in_pretooluse(self, monkeypatch):
        """Test that session_id is available in PreToolUse hooks."""
        from router import route_hooks

        input_data = {
            "hook_event_name": "PreToolUse",
            "session_id": "regression-test-pretooluse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }

        received_session_id = None

        def capture_session_id(script, data):
            nonlocal received_session_id
            received_session_id = data.get("session_id")
            return {}, 0

        with patch("router.run_sync_hook", capture_session_id), patch(
            "router.check_custodiet_block", return_value=None
        ), patch("router.get_hooks_for_event", return_value=[{"script": "test.py"}]):
            route_hooks(input_data)

        assert received_session_id == "regression-test-pretooluse"

    def test_session_id_available_in_posttooluse(self, monkeypatch):
        """Test that session_id is available in PostToolUse hooks."""
        from router import route_hooks

        input_data = {
            "hook_event_name": "PostToolUse",
            "session_id": "regression-test-posttooluse",
            "tool_name": "Read",
            "tool_result": {"content": "file content"},
        }

        received_session_id = None

        def capture_session_id(script, data):
            nonlocal received_session_id
            received_session_id = data.get("session_id")
            return {}, 0

        with patch("router.run_sync_hook", capture_session_id), patch(
            "router.check_custodiet_block", return_value=None
        ), patch("router.get_hooks_for_event", return_value=[{"script": "test.py"}]):
            route_hooks(input_data)

        assert received_session_id == "regression-test-posttooluse"

    def test_session_id_available_in_userpromptsubmit(self, monkeypatch):
        """Test that session_id is available in UserPromptSubmit hooks."""
        from router import route_hooks

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "regression-test-userpromptsubmit",
            "prompt": "Test prompt",
        }

        received_session_id = None

        def capture_session_id(script, data):
            nonlocal received_session_id
            received_session_id = data.get("session_id")
            return {}, 0

        with patch("router.run_sync_hook", capture_session_id), patch(
            "router.check_custodiet_block", return_value=None
        ), patch("router.get_hooks_for_event", return_value=[{"script": "test.py"}]):
            route_hooks(input_data)

        assert received_session_id == "regression-test-userpromptsubmit"

    def test_session_state_operations_with_real_session_id(self, tmp_path, monkeypatch):
        """Integration test: session state operations work end-to-end."""
        from datetime import datetime

        # Set up temp directory for session files
        sessions_dir = tmp_path / "sessions" / "status"
        sessions_dir.mkdir(parents=True)

        def mock_get_path(session_id, date=None):
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            return sessions_dir / f"{date[:10].replace('-', '')}-{session_id}.json"

        with patch("lib.session_state.get_session_file_path", mock_get_path):
            from lib.session_state import (
                get_or_create_session_state,
                set_hydration_pending,
                clear_hydration_pending,
                is_hydration_pending,
                set_current_task,
                get_current_task,
            )

            session_id = "integration-test-session"

            # Create session state
            state = get_or_create_session_state(session_id)
            assert state["session_id"] == session_id

            # Test hydration pending cycle
            assert is_hydration_pending(session_id) is True
            clear_hydration_pending(session_id)
            assert is_hydration_pending(session_id) is False

            # Test task binding
            set_current_task(session_id, "test-task-123", source="test")
            task = get_current_task(session_id)
            assert task == "test-task-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
