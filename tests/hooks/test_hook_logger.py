#!/usr/bin/env python3
"""Tests for unified_logger.py - centralized hook event logging.

Tests that log_hook_event correctly writes to per-session JSONL files.
"""

import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import CanonicalHookOutput, HookContext
from hooks.unified_logger import log_hook_event


@pytest.fixture
def temp_claude_projects(monkeypatch):
    """Create temporary Claude projects directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_dir = Path(tmpdir) / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # Mock Path.home() to use temp directory
        monkeypatch.setattr(Path, "home", lambda: Path(tmpdir))

        yield tmpdir


class TestLogHookEvent:
    """Test log_hook_event function."""

    def test_creates_hook_log_file(self, temp_claude_projects):
        """Test that log_hook_event creates the JSONL file."""
        session_id = "test-session-12345678"

        log_hook_event(
            HookContext(
                session_id=session_id,
                hook_event="TestEvent",
                raw_input={"foo": "bar"},
            ),
            output=CanonicalHookOutput(metadata={"result": "ok"}),
            exit_code=0,
        )

        # Find the created log file
        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))

        assert len(log_files) == 1, f"Expected 1 log file, found {len(log_files)}"
        assert log_files[0].exists()

    def test_log_entry_structure(self, temp_claude_projects):
        """Test that log entries have correct structure with separated input/output."""
        session_id = "test-structure-abcd1234"

        log_hook_event(
            HookContext(
                session_id=session_id,
                hook_event="PreToolUse",
                raw_input={"tool_name": "Edit", "tool_input": {"file": "test.py"}},
            ),
            output=CanonicalHookOutput(context_injection="some context"),
            exit_code=0,
        )

        # Read the log file
        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            entry = json.loads(f.readline())

        # Check required fields
        assert entry["hook_event"] == "PreToolUse"
        assert "logged_at" in entry
        assert entry["exit_code"] == 0
        # Input data should be in 'input' key
        assert "input" in entry
        assert entry["input"]["tool_name"] == "Edit"
        assert entry["input"]["tool_input"]["file"] == "test.py"
        # Output data should be in 'output' key
        assert "output" in entry
        assert entry["output"]["context_injection"] == "some context"

    def test_multiple_events_appended(self, temp_claude_projects):
        """Test that multiple events are appended to same file."""
        session_id = "test-multi-events"

        for i in range(3):
            log_hook_event(
                HookContext(
                    session_id=session_id,
                    hook_event=f"Event{i}",
                    raw_input={"index": i},
                ),
                exit_code=0,
            )

        # Read all entries
        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 3
        assert [e["hook_event"] for e in entries] == ["Event0", "Event1", "Event2"]

    def test_empty_session_id_skips_silently(self, temp_claude_projects):
        """Test that empty session_id silently skips (fail-safe for hooks)."""
        # Should not raise or create files
        log_hook_event(
            HookContext(
                session_id="",
                hook_event="TestEvent",
                raw_input={},
            ),
        )

        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 0, "Empty session_id should not create log file"

    def test_unknown_session_id_skips_silently(self, temp_claude_projects):
        """Test that 'unknown' session_id silently skips."""
        log_hook_event(
            HookContext(
                session_id="unknown",
                hook_event="TestEvent",
                raw_input={},
            ),
        )

        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 0, "'unknown' session_id should not create log file"

    def test_log_file_path_format(self, temp_claude_projects):
        """Test that log file path follows expected format: YYYYMMDD-shorthash-hooks.jsonl."""
        session_id = "test-path-format-xyz"
        today = datetime.now(UTC).strftime("%Y%m%d")

        log_hook_event(
            HookContext(
                session_id=session_id,
                hook_event="TestEvent",
                raw_input={},
            ),
        )

        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 1

        filename = log_files[0].name
        # Should be YYYYMMDD-8charhash-hooks.jsonl
        assert filename.startswith(today), f"Expected {today} prefix, got {filename}"
        assert filename.endswith("-hooks.jsonl")
        # Middle part should be 8-char hash
        middle = filename[len(today) + 1 : -len("-hooks.jsonl")]
        assert len(middle) == 8, f"Expected 8-char hash, got '{middle}'"

    def test_different_sessions_different_files(self, temp_claude_projects):
        """Test that different session IDs create different log files."""
        log_hook_event(HookContext(session_id="session-aaa", hook_event="Test", raw_input={}))
        log_hook_event(HookContext(session_id="session-bbb", hook_event="Test", raw_input={}))

        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))

        assert len(log_files) == 2, "Different sessions should create different files"


class TestLogHookEventEdgeCases:
    """Test edge cases and error handling."""

    def test_nonserializable_data_handled(self, temp_claude_projects):
        """Test that non-JSON-serializable data is converted to strings."""
        session_id = "test-serialize"

        # datetime is not JSON serializable by default
        log_hook_event(
            HookContext(
                session_id=session_id,
                hook_event="TestEvent",
                raw_input={"timestamp": datetime.now()},
            ),
        )

        # Should not raise - custom serializer handles it
        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 1

    def test_output_data_optional(self, temp_claude_projects):
        """Test that output_data is optional."""
        session_id = "test-no-output"

        log_hook_event(
            HookContext(
                session_id=session_id,
                hook_event="TestEvent",
                raw_input={"key": "value"},
            ),
            # No output_data
        )

        projects_dir = Path(temp_claude_projects) / ".claude" / "projects"
        log_files = list(projects_dir.rglob("*-hooks.jsonl"))
        assert len(log_files) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
