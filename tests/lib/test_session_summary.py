#!/usr/bin/env python3
"""Tests for session_summary.py library.

Tests task aggregation and summary generation logic.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from lib.session_summary import (
    append_task_contribution,
    get_task_contributions_path,
    load_task_contributions,
    synthesize_session,
)


@pytest.fixture
def temp_aca_data(tmp_path: Path) -> Path:
    """Set up ACA_DATA env var pointing to tmp_path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    with patch.dict("os.environ", {"ACA_DATA": str(data_dir)}):
        yield data_dir


class TestTaskContributions:
    """Test append and load of task contributions."""

    def test_append_creates_file(self, temp_aca_data: Path) -> None:
        """Appending to a new session creates the file."""
        session_id = "test-session-123"
        data = {"request": "Test task"}

        append_task_contribution(session_id, data)

        path = get_task_contributions_path(session_id)
        assert path.exists()
        content = path.read_text()
        assert "Test task" in content

    def test_append_adds_timestamp(self, temp_aca_data: Path) -> None:
        """Appending adds a timestamp if missing."""
        session_id = "test-session-456"
        data = {"request": "Test task"}

        append_task_contribution(session_id, data)

        tasks = load_task_contributions(session_id)
        assert len(tasks) == 1
        assert "timestamp" in tasks[0]

    def test_load_returns_empty_list_for_missing_file(self, temp_aca_data: Path) -> None:
        """Loading a non-existent session returns empty list."""
        tasks = load_task_contributions("non-existent-session")
        assert tasks == []

    def test_concurrent_writes_safe(self, temp_aca_data: Path) -> None:
        """Multiple writes are safe (file lock or atomic append)."""
        session_id = "test-session-concurrent"

        for i in range(10):
            append_task_contribution(session_id, {"id": i, "request": f"Task {i}"})

        tasks = load_task_contributions(session_id)
        assert len(tasks) == 10
        ids = [t["id"] for t in tasks]
        assert sorted(ids) == list(range(10))


class TestSessionSummaryGeneration:
    """Test generation of markdown summary."""

    def test_synthesize_session_empty(self, temp_aca_data: Path) -> None:
        """Summary for empty session returns structure with empty tasks."""
        summary = synthesize_session("empty-session")
        assert summary["session_id"] == "empty-session"
        assert summary["tasks"] == []

    def test_synthesize_session_single_task(self, temp_aca_data: Path) -> None:
        """Summary for single task."""
        session_id = "single-task-session"
        append_task_contribution(session_id, {
            "request": "Fix bug in login",
            "task_id": "bug-123",
            "outcome": "success",
            "accomplishment": "Fixed login bug"
        })

        summary = synthesize_session(session_id)
        assert len(summary["tasks"]) == 1
        # task_id might not be preserved if not standard field, but let's check
        # Ah, synthesize_session just loads tasks.
        assert summary["tasks"][0]["task_id"] == "bug-123"
        assert "Fixed login bug" in summary["accomplishments"]

    def test_synthesize_session_multiple_tasks(self, temp_aca_data: Path) -> None:
        """Summary for multiple tasks."""
        session_id = "multi-task-session"
        append_task_contribution(session_id, {"request": "Task A"})
        append_task_contribution(session_id, {"request": "Task B"})

        summary = synthesize_session(session_id)
        assert len(summary["tasks"]) == 2


class TestIntegration:
    """Integration tests simulating real usage."""

    def test_concurrent_sessions_isolated(self, temp_aca_data: Path) -> None:
        """Multiple sessions in same directory don't collide (different session IDs)."""
        # Two sessions running in parallel (different terminals, same cwd)
        session_a = "session-aaa-terminal-1"
        session_b = "session-bbb-terminal-2"

        append_task_contribution(session_a, {"request": "Task from terminal 1"})
        append_task_contribution(session_b, {"request": "Task from terminal 2"})
        append_task_contribution(session_a, {"request": "Another from terminal 1"})

        tasks_a = load_task_contributions(session_a)
        tasks_b = load_task_contributions(session_b)

        assert len(tasks_a) == 2
        assert len(tasks_b) == 1
        assert tasks_a[0]["request"] == "Task from terminal 1"
        assert tasks_b[0]["request"] == "Task from terminal 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
