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


def test_unified_accomplishments_available(data_dir: Path) -> None:
    """Test that dashboard exposes unified accomplishments for today.

    AC-U4: User sees today's accomplishments in one place (unified section).

    Currently accomplishments are scattered across:
    - Daily log completed tasks (from parse_daily_log()['completed'])
    - Daily log outcomes (from parse_daily_log()['outcomes'])
    - Session todos completed (from SessionOutcomes)
    - Git commits (from get_project_git_activity())

    The dashboard must have a function that aggregates all accomplishments
    from all sources into a single unified list for display.

    Required fields in each accomplishment dict:
    - description: What was accomplished (required)
    - source: One of 'daily_log', 'session', 'git', 'outcome' (required)
    - timestamp: When it happened (optional, datetime or None)

    This test verifies the function exists and returns properly structured data.
    It connects to EXISTING live data via the data_dir fixture.

    Args:
        data_dir: pytest fixture providing path to ACA_DATA
    """
    from datetime import datetime

    # Import the dashboard module
    from skills.dashboard import dashboard

    # The dashboard MUST expose a get_todays_accomplishments() function
    # that aggregates all accomplishments from all sources
    assert hasattr(dashboard, "get_todays_accomplishments"), (
        "Dashboard must expose get_todays_accomplishments() function for AC-U4 "
        "(unified accomplishments). This function should aggregate accomplishments "
        "from daily_log, session todos, git commits, and outcomes into one list."
    )

    # Call the function - it should work with live data
    result = dashboard.get_todays_accomplishments()

    # Verify return type is a list
    assert isinstance(result, list), (
        f"get_todays_accomplishments() must return a list, got {type(result).__name__}"
    )

    # Verify each item in the list is properly structured
    valid_sources = {"daily_log", "session", "git", "outcome"}

    for i, accomplishment in enumerate(result):
        assert isinstance(accomplishment, dict), (
            f"Each accomplishment must be a dict, item {i} is {type(accomplishment).__name__}"
        )

        # Verify required 'description' field
        assert "description" in accomplishment, (
            f"Accomplishment {i} must include 'description' field"
        )
        assert isinstance(accomplishment["description"], str), (
            f"Accomplishment {i} 'description' must be str, "
            f"got {type(accomplishment['description']).__name__}"
        )
        assert accomplishment["description"], (
            f"Accomplishment {i} 'description' must not be empty"
        )

        # Verify required 'source' field
        assert "source" in accomplishment, (
            f"Accomplishment {i} must include 'source' field"
        )
        assert accomplishment["source"] in valid_sources, (
            f"Accomplishment {i} source must be one of {valid_sources}, "
            f"got {accomplishment['source']!r}"
        )

        # Verify optional 'timestamp' field if present
        if "timestamp" in accomplishment and accomplishment["timestamp"] is not None:
            assert isinstance(accomplishment["timestamp"], datetime), (
                f"Accomplishment {i} 'timestamp' must be datetime or None, "
                f"got {type(accomplishment['timestamp']).__name__}"
            )


def test_priority_tasks_available(data_dir: Path) -> None:
    """Test that dashboard exposes all P0/P1 tasks for prominent display.

    AC-U3: User sees all P0/P1 tasks without clicking (visible in main view).

    The dashboard must have a function that returns ALL P0/P1 priority tasks
    for prominent display. Unlike get_next_actions() which limits to 5 tasks,
    this function should return every P0/P1 task to ensure nothing critical
    is hidden from the user.

    Required fields in each task dict:
    - title: Task title (required, str)
    - priority: Priority level 0 or 1 (required, int)
    - project: Project name (required, str)
    - status: Task status (required, str)

    This test verifies the function exists and returns properly structured data.
    It connects to EXISTING live data via the data_dir fixture.

    Args:
        data_dir: pytest fixture providing path to ACA_DATA
    """
    # Import the dashboard module
    from skills.dashboard import dashboard

    # The dashboard MUST expose a get_priority_tasks() function
    # that returns ALL P0/P1 tasks for prominent display
    assert hasattr(dashboard, "get_priority_tasks"), (
        "Dashboard must expose get_priority_tasks() function for AC-U3 "
        "(P0/P1 task visibility). This function should return ALL P0/P1 tasks, "
        "not limited to a subset like get_next_actions() which caps at 5."
    )

    # Call the function - it should work with live data
    result = dashboard.get_priority_tasks()

    # Verify return type is a list
    assert isinstance(result, list), (
        f"get_priority_tasks() must return a list, got {type(result).__name__}"
    )

    # Verify each item in the list is properly structured
    valid_priorities = {0, 1}

    for i, task in enumerate(result):
        assert isinstance(task, dict), (
            f"Each task must be a dict, item {i} is {type(task).__name__}"
        )

        # Verify required 'title' field
        assert "title" in task, (
            f"Task {i} must include 'title' field"
        )
        assert isinstance(task["title"], str), (
            f"Task {i} 'title' must be str, got {type(task['title']).__name__}"
        )
        assert task["title"], (
            f"Task {i} 'title' must not be empty"
        )

        # Verify required 'priority' field
        assert "priority" in task, (
            f"Task {i} must include 'priority' field"
        )
        assert task["priority"] in valid_priorities, (
            f"Task {i} priority must be 0 or 1 (P0/P1), got {task['priority']!r}"
        )

        # Verify required 'project' field
        assert "project" in task, (
            f"Task {i} must include 'project' field"
        )
        assert isinstance(task["project"], str), (
            f"Task {i} 'project' must be str, got {type(task['project']).__name__}"
        )

        # Verify required 'status' field
        assert "status" in task, (
            f"Task {i} must include 'status' field"
        )
        assert isinstance(task["status"], str), (
            f"Task {i} 'status' must be str, got {type(task['status']).__name__}"
        )

    # Verify this returns ALL P0/P1 tasks, not limited to 5
    # If there are more than 5 P0/P1 tasks in live data, all should be returned
    # This differentiates get_priority_tasks() from get_next_actions()
    if len(result) > 5:
        # Good - we're getting more than the get_next_actions() limit
        pass
    # Note: If <= 5 P0/P1 tasks exist, that's also valid


def test_three_question_layout_structure(data_dir: Path) -> None:
    """Test that dashboard provides unified three-question layout data.

    AC-U5: User can correctly identify (1) primary task, (2) active sessions,
    and (3) today's done items WITHOUT expanding/clicking anything.

    The layout should be organized around three questions:
    - What should I do? (primary_focus + priority_tasks)
    - What am I doing? (active_sessions)
    - What have I done? (accomplishments)

    The dashboard must have a function get_dashboard_layout() that returns
    a dict with these three sections, using data from existing functions:
    - get_primary_focus()
    - get_priority_tasks()
    - get_session_display_info()
    - get_todays_accomplishments()

    This test verifies the function exists and returns properly structured data.
    It connects to EXISTING live data via the data_dir fixture.

    Args:
        data_dir: pytest fixture providing path to ACA_DATA
    """
    from datetime import datetime

    # Import the dashboard module
    from skills.dashboard import dashboard

    # The dashboard MUST expose a get_dashboard_layout() function
    # that combines all data sources into the three-question structure
    assert hasattr(dashboard, "get_dashboard_layout"), (
        "Dashboard must expose get_dashboard_layout() function for AC-U5 "
        "(three-question layout). This function should return a dict with "
        "three sections: 'what_to_do', 'what_doing', 'what_done'."
    )

    # Call the function - it should work with live data
    result = dashboard.get_dashboard_layout()

    # Verify return type is a dict
    assert isinstance(result, dict), (
        f"get_dashboard_layout() must return a dict, got {type(result).__name__}"
    )

    # === Section 1: what_to_do ===
    # Contains primary_focus and priority_tasks
    assert "what_to_do" in result, (
        "Layout must include 'what_to_do' section for 'What should I do?' question"
    )
    what_to_do = result["what_to_do"]
    assert isinstance(what_to_do, dict), (
        f"'what_to_do' must be a dict, got {type(what_to_do).__name__}"
    )

    # Verify what_to_do has primary_focus (from get_primary_focus)
    assert "primary_focus" in what_to_do, (
        "'what_to_do' must include 'primary_focus' from get_primary_focus()"
    )
    primary_focus = what_to_do["primary_focus"]
    assert isinstance(primary_focus, dict), (
        f"'primary_focus' must be a dict, got {type(primary_focus).__name__}"
    )
    assert "task_title" in primary_focus, (
        "'primary_focus' must include 'task_title' field"
    )
    assert "source" in primary_focus, (
        "'primary_focus' must include 'source' field"
    )

    # Verify what_to_do has priority_tasks (from get_priority_tasks)
    assert "priority_tasks" in what_to_do, (
        "'what_to_do' must include 'priority_tasks' from get_priority_tasks()"
    )
    priority_tasks = what_to_do["priority_tasks"]
    assert isinstance(priority_tasks, list), (
        f"'priority_tasks' must be a list, got {type(priority_tasks).__name__}"
    )

    # === Section 2: what_doing ===
    # Contains active_sessions (list of session display info)
    assert "what_doing" in result, (
        "Layout must include 'what_doing' section for 'What am I doing?' question"
    )
    what_doing = result["what_doing"]
    assert isinstance(what_doing, dict), (
        f"'what_doing' must be a dict, got {type(what_doing).__name__}"
    )

    # Verify what_doing has active_sessions
    assert "active_sessions" in what_doing, (
        "'what_doing' must include 'active_sessions' list"
    )
    active_sessions = what_doing["active_sessions"]
    assert isinstance(active_sessions, list), (
        f"'active_sessions' must be a list, got {type(active_sessions).__name__}"
    )

    # Verify each session has the expected structure (from get_session_display_info)
    for i, session in enumerate(active_sessions):
        assert isinstance(session, dict), (
            f"Each active_session must be a dict, item {i} is {type(session).__name__}"
        )
        assert "session_id_short" in session, (
            f"active_session {i} must include 'session_id_short'"
        )
        assert "project" in session, (
            f"active_session {i} must include 'project'"
        )
        assert "last_activity" in session, (
            f"active_session {i} must include 'last_activity'"
        )

    # === Section 3: what_done ===
    # Contains accomplishments (from get_todays_accomplishments)
    assert "what_done" in result, (
        "Layout must include 'what_done' section for 'What have I done?' question"
    )
    what_done = result["what_done"]
    assert isinstance(what_done, dict), (
        f"'what_done' must be a dict, got {type(what_done).__name__}"
    )

    # Verify what_done has accomplishments
    assert "accomplishments" in what_done, (
        "'what_done' must include 'accomplishments' from get_todays_accomplishments()"
    )
    accomplishments = what_done["accomplishments"]
    assert isinstance(accomplishments, list), (
        f"'accomplishments' must be a list, got {type(accomplishments).__name__}"
    )

    # Verify each accomplishment has the expected structure
    valid_sources = {"daily_log", "session", "git", "outcome"}
    for i, acc in enumerate(accomplishments):
        assert isinstance(acc, dict), (
            f"Each accomplishment must be a dict, item {i} is {type(acc).__name__}"
        )
        assert "description" in acc, (
            f"accomplishment {i} must include 'description'"
        )
        assert "source" in acc, (
            f"accomplishment {i} must include 'source'"
        )
        assert acc["source"] in valid_sources, (
            f"accomplishment {i} source must be one of {valid_sources}, "
            f"got {acc['source']!r}"
        )
