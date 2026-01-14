#!/usr/bin/env python3
"""Tests for unified_logger.py hook.

Tests SessionStart session file creation, SubagentStop recording, and Stop event insights.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the functions we're testing
import sys

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from unified_logger import (
    handle_stop,
    handle_subagent_stop,
    log_event_to_session,
    main,
)


@pytest.fixture
def temp_session_dir(monkeypatch):
    """Create temporary session directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock the session paths to use temp dir
        session_path = Path(tmpdir) / "test-session"
        session_path.mkdir(parents=True)

        # Mock get_session_directory to return our temp path
        def mock_get_session_directory(session_id, date=None):
            if date is None:
                date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # Create directory structure: {YYYYMMDD}-{hash}/
            date_compact = date.replace("-", "")
            short_id = session_id[-8:] if len(session_id) >= 8 else session_id
            session_dir = Path(tmpdir) / f"{date_compact}-{short_id}"
            session_dir.mkdir(parents=True, exist_ok=True)
            return session_dir

        with patch("lib.session_paths.get_session_directory", mock_get_session_directory):
            yield tmpdir


class TestSessionStartEvent:
    """Test SessionStart event creates session file."""

    def test_session_file_created_on_first_event(self, temp_session_dir):
        """Test that SessionStart creates session file."""
        session_id = "test-session-12345678"
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart",
        }

        # Call log_event_to_session
        log_event_to_session(session_id, "SessionStart", input_data)

        # Verify session file was created
        from lib.session_state import get_session_file_path

        session_file = get_session_file_path(session_id)
        assert session_file.exists(), "Session file should be created"

        # Verify basic structure
        state = json.loads(session_file.read_text())
        assert state["session_id"] == session_id
        assert "date" in state
        assert "started_at" in state
        assert state["state"]["custodiet_blocked"] is False

    def test_session_file_has_correct_structure(self, temp_session_dir):
        """Test that created session file has all required fields."""
        session_id = "test-abc12345"
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart",
        }

        log_event_to_session(session_id, "SessionStart", input_data)

        from lib.session_state import load_session_state

        state = load_session_state(session_id)
        assert state is not None

        # Check all required top-level fields
        assert "session_id" in state
        assert "date" in state
        assert "started_at" in state
        assert "ended_at" in state
        assert state["ended_at"] is None  # Should be None initially

        # Check nested structures
        assert "state" in state
        assert "hydration" in state
        assert "main_agent" in state
        assert "subagents" in state
        assert "insights" in state

        # Check state defaults
        assert state["state"]["custodiet_blocked"] is False
        assert state["state"]["current_workflow"] is None
        assert state["state"]["hydration_pending"] is False

    def test_unknown_session_id_skipped(self, temp_session_dir):
        """Test that unknown session_id is gracefully skipped."""
        # Should not raise or create files
        log_event_to_session("unknown", "SessionStart", {})
        log_event_to_session("", "SessionStart", {})

        # Verify no files created in temp dir
        temp_path = Path(temp_session_dir)
        session_files = list(temp_path.rglob("session-state.json"))
        assert len(session_files) == 0


class TestSubagentStopEvent:
    """Test SubagentStop event records subagent invocations."""

    def test_subagent_invocation_recorded(self, temp_session_dir):
        """Test that SubagentStop records subagent data."""
        session_id = "test-subagent-87654321"

        # First create session with SessionStart
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Now record a subagent stop
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SubagentStop",
            "subagent_type": "critic",
            "subagent_result": {"verdict": "PROCEED", "reasoning": "Looks good"},
        }

        handle_subagent_stop(session_id, input_data)

        # Verify subagent was recorded
        from lib.session_state import load_session_state

        state = load_session_state(session_id)
        assert "critic" in state["subagents"]
        assert state["subagents"]["critic"]["verdict"] == "PROCEED"
        assert state["subagents"]["critic"]["reasoning"] == "Looks good"
        assert "stopped_at" in state["subagents"]["critic"]

    def test_subagent_string_result_handled(self, temp_session_dir):
        """Test that string subagent results are properly wrapped."""
        session_id = "test-string-result"

        # Create session
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Record subagent with string result
        input_data = {
            "session_id": session_id,
            "subagent_type": "explore",
            "subagent_result": "Found 3 files matching pattern",
        }

        handle_subagent_stop(session_id, input_data)

        # Verify string was wrapped in dict
        from lib.session_state import load_session_state

        state = load_session_state(session_id)
        assert "explore" in state["subagents"]
        assert state["subagents"]["explore"]["output"] == "Found 3 files matching pattern"
        assert "stopped_at" in state["subagents"]["explore"]

    def test_multiple_subagents_recorded(self, temp_session_dir):
        """Test that multiple subagent invocations are tracked separately."""
        session_id = "test-multi-agents"

        # Create session
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Record multiple subagents
        agents = [
            ("critic", {"verdict": "PROCEED"}),
            ("qa-verifier", {"status": "passed"}),
            ("effectual-planner", {"plan": "Step 1, Step 2"}),
        ]

        for agent_type, result in agents:
            input_data = {
                "session_id": session_id,
                "subagent_type": agent_type,
                "subagent_result": result,
            }
            handle_subagent_stop(session_id, input_data)

        # Verify all recorded
        from lib.session_state import load_session_state

        state = load_session_state(session_id)
        assert len(state["subagents"]) == 3
        assert "critic" in state["subagents"]
        assert "qa-verifier" in state["subagents"]
        assert "effectual-planner" in state["subagents"]


class TestStopEvent:
    """Test Stop event writes session insights."""

    def test_stop_event_writes_insights(self, temp_session_dir):
        """Test that Stop event generates and writes insights."""
        session_id = "test-stop-event"

        # Create session with some data
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Add some subagent activity
        handle_subagent_stop(
            session_id,
            {
                "subagent_type": "critic",
                "subagent_result": {"verdict": "PROCEED"},
            },
        )

        # Now trigger Stop event
        input_data = {
            "session_id": session_id,
            "hook_event_name": "Stop",
            "stop_reason": "end_turn",
        }

        # Mock the insights file path to use temp dir - patch where it's used
        insights_file = Path(temp_session_dir) / "test-insights.json"
        with patch(
            "unified_logger.get_insights_file_path", return_value=insights_file
        ), patch("unified_logger.write_insights_file") as mock_write:
            handle_stop(session_id, input_data)

            # Verify write_insights_file was called
            assert mock_write.called, "write_insights_file should be called"
            call_args = mock_write.call_args
            assert call_args[0][0] == insights_file

            # Verify insights structure passed to write_insights_file
            insights = call_args[0][1]
            assert "session_id" in insights
            assert "date" in insights
            assert "project" in insights
            assert "outcome" in insights
            assert "stop_reason" in insights
            assert insights["stop_reason"] == "end_turn"

    def test_stop_event_updates_session_state(self, temp_session_dir):
        """Test that Stop event updates session state with insights."""
        session_id = "test-stop-state"

        # Create session
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Trigger Stop
        input_data = {
            "session_id": session_id,
            "stop_reason": "user_exit",
        }

        # Mock insights file path and write function
        insights_file = Path(temp_session_dir) / "insights.json"
        with patch(
            "unified_logger.get_insights_file_path", return_value=insights_file
        ), patch("unified_logger.write_insights_file"):
            handle_stop(session_id, input_data)

        # Verify session state has insights and ended_at
        from lib.session_state import load_session_state

        state = load_session_state(session_id)
        assert state["insights"] is not None
        assert state["ended_at"] is not None
        assert "outcome" in state["insights"]

    def test_stop_includes_operational_metrics(self, temp_session_dir):
        """Test that Stop event includes operational metrics in insights."""
        session_id = "test-metrics"

        # Create session
        log_event_to_session(session_id, "SessionStart", {"session_id": session_id})

        # Add multiple subagents
        for agent_type in ["critic", "qa-verifier", "custodiet"]:
            handle_subagent_stop(
                session_id,
                {
                    "subagent_type": agent_type,
                    "subagent_result": {"status": "ok"},
                },
            )

        # Trigger Stop - mock write functions
        insights_file = Path(temp_session_dir) / "metrics-insights.json"
        with patch(
            "unified_logger.get_insights_file_path", return_value=insights_file
        ), patch("unified_logger.write_insights_file") as mock_write:
            handle_stop(session_id, {"stop_reason": "end_turn"})

            # Verify metrics in insights passed to write_insights_file
            assert mock_write.called
            insights = mock_write.call_args[0][1]
            assert insights["subagent_count"] == 3
            assert len(insights["subagents_invoked"]) == 3
            assert "critic" in insights["subagents_invoked"]
            assert "qa-verifier" in insights["subagents_invoked"]
            assert "custodiet" in insights["subagents_invoked"]


class TestMainHookEntry:
    """Test main() hook entry point."""

    def test_main_handles_valid_input(self, temp_session_dir, monkeypatch, capsys):
        """Test that main() processes valid hook input."""
        session_id = "test-main-valid"
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart",
        }

        # Mock stdin with JSON input
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit with 0 (success)
        assert exc_info.value.code == 0

        # Should output noop response
        captured = capsys.readouterr()
        assert "{}" in captured.out

        # Verify session file was created
        from lib.session_state import get_session_file_path

        session_file = get_session_file_path(session_id)
        assert session_file.exists()

    def test_main_handles_invalid_json(self, temp_session_dir, monkeypatch, capsys):
        """Test that main() gracefully handles invalid JSON input."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("not valid json"))

        # Should not crash - gracefully continue
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "{}" in captured.out

    def test_main_handles_missing_session_id(self, temp_session_dir, monkeypatch, capsys):
        """Test that main() handles missing session_id gracefully."""
        import io

        input_data = {"hook_event_name": "SessionStart"}  # No session_id
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Should not crash
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "{}" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
