"""Tests for R3: Fix list_tasks Timestamps.

Verifies that task mutations record explicit ISO-8601 UTC timestamps,
that list_tasks returns accurate modified timestamps without falling back
to filesystem mtime, and that staleness sweeps (since/before filters) work accurately.
"""

from __future__ import annotations

from datetime import UTC, datetime

from transcripts.domain.tasks import (
    create_task,
    list_tasks,
    update_task,
    validate_task_timestamps,
)
from transcripts.domain.time import parse_iso_utc


def test_create_task_records_explicit_iso_utc_timestamps():
    """Verify create_task sets created and modified timestamps in ISO-8601 UTC format."""
    now = datetime.now(UTC)
    task = create_task("Write report", status="inbox")

    assert task["title"] == "Write report"
    assert task["status"] == "inbox"

    created_dt = parse_iso_utc(task["created"])
    modified_dt = parse_iso_utc(task["modified"])

    assert created_dt is not None
    assert modified_dt is not None

    # Verify timezone is UTC
    assert created_dt.tzinfo == UTC
    assert modified_dt.tzinfo == UTC

    # Verify timestamp is close to current time
    assert abs((created_dt - now).total_seconds()) < 5
    assert task["modified"] == task["created"]
    assert task["updated_at"] == task["created_at"]


def test_create_task_with_custom_timestamp():
    """Verify create_task accepts an explicit datetime or date object."""
    custom_dt = datetime(2026, 8, 1, 10, 30, 0, tzinfo=UTC)
    task = create_task("Historical task", created_at=custom_dt)

    assert task["created"] == "2026-08-01T10:30:00.000000+00:00"
    assert task["modified"] == "2026-08-01T10:30:00.000000+00:00"


def test_update_task_bumps_modified_timestamp():
    """Verify update_task updates task attributes and bumps modified timestamp."""
    initial_dt = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    task = create_task("Task to update", created_at=initial_dt)

    update_dt = datetime(2026, 8, 5, 14, 20, 0, tzinfo=UTC)
    updated = update_task(task, updates={"status": "in_progress"}, modified_at=update_dt)

    assert updated["status"] == "in_progress"
    assert updated["created"] == "2026-08-01T10:00:00.000000+00:00"
    assert updated["modified"] == "2026-08-05T14:20:00.000000+00:00"
    assert updated["updated_at"] == "2026-08-05T14:20:00.000000+00:00"


def test_validate_task_timestamps_eliminates_bogus_mtime_fallback():
    """Verify validate_task_timestamps normalizes valid timestamps and sets invalid ones to None."""
    # Valid ISO timestamp
    t_valid = {"id": "1", "modified": "2026-08-04T12:00:00Z"}
    val_valid = validate_task_timestamps(t_valid)
    assert val_valid["modified"] == "2026-08-04T12:00:00.000000+00:00"

    # Missing modified field - must set modified to None, NOT filesystem mtime
    t_missing = {"id": "2", "title": "No timestamp"}
    val_missing = validate_task_timestamps(t_missing)
    assert val_missing["modified"] is None
    assert val_missing["updated_at"] is None

    # Invalid timestamp string
    t_invalid = {"id": "3", "modified": "not-a-date-string"}
    val_invalid = validate_task_timestamps(t_invalid)
    assert val_invalid["modified"] is None


def test_list_tasks_returns_validated_timestamps():
    """Verify list_tasks includes accurate modified timestamps in output."""
    tasks = [
        create_task("T1", created_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC)),
        {"title": "T2", "status": "ready", "modified": "2026-08-02T12:00:00+00:00"},
        {"title": "T3", "status": "ready"},  # Missing modified timestamp
    ]

    res = list_tasks(tasks, include_done=True, format="json")
    assert isinstance(res, dict)
    listed_tasks = res["tasks"]
    assert len(listed_tasks) == 3

    assert listed_tasks[0]["modified"] == "2026-08-01T00:00:00.000000+00:00"
    assert listed_tasks[1]["modified"] == "2026-08-02T12:00:00.000000+00:00"
    assert listed_tasks[2]["modified"] is None


def test_list_tasks_since_filter():
    """Verify list_tasks since filter excludes tasks modified before the cutoff."""
    tasks = [
        {"title": "Old Task", "status": "ready", "modified": "2026-08-01T10:00:00+00:00"},
        {"title": "Mid Task", "status": "ready", "modified": "2026-08-05T10:00:00+00:00"},
        {"title": "New Task", "status": "ready", "modified": "2026-08-06T10:00:00+00:00"},
        {"title": "No Date Task", "status": "ready"},  # Should be excluded when date filter active
    ]

    # Filter since 2026-08-05
    res = list_tasks(tasks, since="2026-08-05", include_done=True)
    titles = [t["title"] for t in res["tasks"]]
    assert "Mid Task" in titles
    assert "New Task" in titles
    assert "Old Task" not in titles
    assert "No Date Task" not in titles


def test_list_tasks_before_filter():
    """Verify list_tasks before filter excludes tasks modified after the cutoff."""
    tasks = [
        {"title": "Old Task", "status": "ready", "modified": "2026-08-01T10:00:00+00:00"},
        {"title": "Mid Task", "status": "ready", "modified": "2026-08-05T10:00:00+00:00"},
        {"title": "New Task", "status": "ready", "modified": "2026-08-06T10:00:00+00:00"},
    ]

    # Filter before 2026-08-04
    res = list_tasks(tasks, before="2026-08-04", include_done=True)
    titles = [t["title"] for t in res["tasks"]]
    assert titles == ["Old Task"]


def test_list_tasks_since_and_before_range_filter():
    """Verify list_tasks with both since and before date range filtering."""
    tasks = [
        {"title": "T1", "status": "ready", "modified": "2026-08-01T00:00:00+00:00"},
        {"title": "T2", "status": "ready", "modified": "2026-08-03T12:00:00+00:00"},
        {"title": "T3", "status": "ready", "modified": "2026-08-05T18:00:00+00:00"},
        {"title": "T4", "status": "ready", "modified": "2026-08-07T00:00:00+00:00"},
    ]

    res = list_tasks(tasks, since="2026-08-02", before="2026-08-06", include_done=True)
    titles = [t["title"] for t in res["tasks"]]
    assert titles == ["T2", "T3"]


def test_list_tasks_markdown_format():
    """Verify markdown output format includes modified timestamp strings."""
    tasks = [
        {
            "title": "Refactor API",
            "status": "in_progress",
            "modified": "2026-08-06T12:00:00.000000+00:00",
        },
    ]

    md_output = list_tasks(tasks, include_done=True, format="markdown")
    assert isinstance(md_output, str)
    assert "# Task List" in md_output
    assert "Refactor API" in md_output
    assert "(modified: 2026-08-06T12:00:00.000000+00:00)" in md_output
