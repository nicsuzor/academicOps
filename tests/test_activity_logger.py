#!/usr/bin/env python3
"""
Tests for activity logging functionality.

Verifies:
1. log_activity() writes JSONL to $ACA_DATA/logs/activity.jsonl
2. File is created at correct location
3. JSONL format (valid JSON per line)
4. Append behavior works correctly
"""

import json
from pathlib import Path

import pytest

from lib.paths import get_logs_dir


def test_log_activity_writes_to_correct_location(tmp_path, monkeypatch):
    """Test that log_activity writes to $ACA_DATA/logs/activity.jsonl."""
    # Set up temporary data directory
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Point ACA_DATA to temp directory
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Import after environment is set
    from lib.activity import log_activity

    # Log an activity
    action = "test_action"
    session = "test-session-123"
    log_activity(action=action, session=session)

    # Verify file created at correct location
    activity_log = get_logs_dir() / "activity.jsonl"
    assert activity_log.exists(), f"Activity log not created at {activity_log}"

    # Verify JSONL format (valid JSON per line)
    with activity_log.open() as f:
        lines = f.readlines()
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"

        # Parse JSON
        entry = json.loads(lines[0])
        assert entry["action"] == action, f"Expected action={action}, got {entry['action']}"
        assert entry["session"] == session, f"Expected session={session}, got {entry['session']}"
        assert "timestamp" in entry, "Missing timestamp field"


def test_log_activity_append_behavior(tmp_path, monkeypatch):
    """Test that log_activity appends to existing file."""
    # Set up temporary data directory
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Point ACA_DATA to temp directory
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Import after environment is set
    from lib.activity import log_activity

    # Log multiple activities
    log_activity(action="action_1", session="session-1")
    log_activity(action="action_2", session="session-2")
    log_activity(action="action_3", session="session-3")

    # Verify all entries present
    activity_log = get_logs_dir() / "activity.jsonl"
    with activity_log.open() as f:
        lines = f.readlines()
        assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"

        # Verify each entry
        entries = [json.loads(line) for line in lines]
        assert entries[0]["action"] == "action_1"
        assert entries[1]["action"] == "action_2"
        assert entries[2]["action"] == "action_3"


def test_log_activity_creates_logs_directory(tmp_path, monkeypatch):
    """Test that log_activity creates logs directory if it doesn't exist."""
    # Set up temporary data directory WITHOUT logs/
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Point ACA_DATA to temp directory
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Verify logs directory doesn't exist yet
    logs_dir = data_dir / "logs"
    assert not logs_dir.exists(), "Logs directory should not exist yet"

    # Import after environment is set
    from lib.activity import log_activity

    # Log activity - should create logs directory
    log_activity(action="test_action", session="test-session")

    # Verify logs directory was created
    assert logs_dir.exists(), "Logs directory should be created"

    # Verify activity log was created
    activity_log = logs_dir / "activity.jsonl"
    assert activity_log.exists(), f"Activity log not created at {activity_log}"


def test_log_activity_includes_timestamp(tmp_path, monkeypatch):
    """Test that log_activity includes ISO 8601 timestamp."""
    # Set up temporary data directory
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Point ACA_DATA to temp directory
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Import after environment is set
    from lib.activity import log_activity

    # Log activity
    log_activity(action="test_action", session="test-session")

    # Verify timestamp format
    activity_log = get_logs_dir() / "activity.jsonl"
    with activity_log.open() as f:
        entry = json.loads(f.read())

        # Verify timestamp exists and is ISO 8601 format
        assert "timestamp" in entry, "Missing timestamp field"

        # Parse timestamp to verify format (will raise if invalid)
        from datetime import datetime
        timestamp = datetime.fromisoformat(entry["timestamp"])
        assert timestamp is not None, "Invalid ISO 8601 timestamp"
