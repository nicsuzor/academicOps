"""Tests for dashboard layout and primary focus prominence.

Tests that the dashboard provides programmatic access to primary focus data,
supporting AC-U2: User immediately sees their primary task (most prominent
element, no clicking required).

Uses existing test infrastructure from conftest.py.
"""

from pathlib import Path
from typing import Any

import pytest


def test_primary_focus_data_available(data_dir: Path) -> None:
    """Test that dashboard exposes primary focus data for prominent display.

    AC-U2: User immediately sees their primary task (most prominent element,
    no clicking required).

    The dashboard must have a function that returns structured primary focus
    data suitable for prominent display. This data should include:
    - task_title: The primary task title (required)
    - source: Where this came from - 'daily_log' or 'synthesis' (required)

    This test verifies the function exists and returns properly structured data.
    It connects to EXISTING live data via the data_dir fixture.

    Args:
        data_dir: pytest fixture providing path to ACA_DATA
    """
    # Import the dashboard module
    from skills.dashboard import dashboard

    # The dashboard MUST expose a get_primary_focus() function
    # that returns structured data for prominent display
    assert hasattr(dashboard, "get_primary_focus"), (
        "Dashboard must expose get_primary_focus() function for AC-U2 "
        "(primary task prominence). This function should return structured "
        "data with at minimum: task_title and source fields."
    )

    # Call the function - it should work with live data
    result: dict[str, Any] = dashboard.get_primary_focus()

    # Verify return type
    assert isinstance(result, dict), (
        f"get_primary_focus() must return a dict, got {type(result).__name__}"
    )

    # Verify required fields are present
    assert "task_title" in result, (
        "get_primary_focus() result must include 'task_title' field "
        "for the primary task to be displayed prominently"
    )
    assert "source" in result, (
        "get_primary_focus() result must include 'source' field "
        "indicating where the focus came from ('daily_log' or 'synthesis')"
    )

    # Verify source is a valid value
    valid_sources = {"daily_log", "synthesis", "none"}
    assert result["source"] in valid_sources, (
        f"source must be one of {valid_sources}, got {result['source']!r}"
    )

    # If source is not 'none', task_title should be non-empty
    if result["source"] != "none":
        assert result["task_title"], (
            "task_title must be non-empty when source is not 'none'"
        )


def test_session_identity_available() -> None:
    """Test that dashboard exposes session identity for terminal disambiguation.

    AC-U1: User can identify which terminal/session is doing what work
    (session cards show distinguishing info).

    The dashboard must have a function that extracts displayable session
    identity from a SessionInfo object. This enables users to distinguish
    between multiple terminal sessions.

    Required fields in return value:
    - session_id_short: First 7 characters of session UUID (like git short hash)
    - project: Project name from the session
    - last_activity: Timestamp of last session activity

    This test verifies the function exists and returns properly structured data.
    Uses EXISTING SessionInfo structure from lib/session_reader.py.
    """
    from datetime import datetime, timezone

    # Import the dashboard module
    from skills.dashboard import dashboard

    # Import the real SessionInfo from session_reader
    from lib.session_reader import SessionInfo

    # The dashboard MUST expose a get_session_display_info() function
    # that extracts displayable identity from a SessionInfo
    assert hasattr(dashboard, "get_session_display_info"), (
        "Dashboard must expose get_session_display_info(session_info) function "
        "for AC-U1 (session identity). This function should accept a SessionInfo "
        "and return structured data with: session_id_short, project, last_activity."
    )

    # Create a real SessionInfo instance using the actual dataclass
    # This uses the real structure, not fake test data
    from pathlib import Path

    test_session = SessionInfo(
        path=Path("/tmp/test-session.jsonl"),
        project="-Users-suzor-src-academicOps",
        session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        last_modified=datetime.now(timezone.utc),
    )

    # Call the function with a real SessionInfo
    result = dashboard.get_session_display_info(test_session)

    # Verify return type
    assert isinstance(result, dict), (
        f"get_session_display_info() must return a dict, got {type(result).__name__}"
    )

    # Verify required fields are present
    assert "session_id_short" in result, (
        "get_session_display_info() result must include 'session_id_short' field "
        "(first 7 chars of session UUID for quick identification)"
    )
    assert "project" in result, (
        "get_session_display_info() result must include 'project' field "
        "showing which project the session is working in"
    )
    assert "last_activity" in result, (
        "get_session_display_info() result must include 'last_activity' field "
        "with timestamp of last session activity"
    )

    # Verify session_id_short is first 7 characters
    assert result["session_id_short"] == "a1b2c3d", (
        f"session_id_short should be first 7 chars of session_id, "
        f"expected 'a1b2c3d', got {result['session_id_short']!r}"
    )

    # Verify project is extracted
    assert result["project"] == "-Users-suzor-src-academicOps" or result["project"] == "academicOps", (
        f"project should be the session project name, got {result['project']!r}"
    )

    # Verify last_activity is a datetime
    assert isinstance(result["last_activity"], datetime), (
        f"last_activity must be a datetime, got {type(result['last_activity']).__name__}"
    )
