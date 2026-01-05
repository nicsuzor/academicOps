"""Tests for dashboard task loader functionality.

Tests the task_loader module which provides filtered task loading
for dashboard displays. Uses existing test infrastructure from conftest.py.
"""

from pathlib import Path


from skills.tasks.task_loader import load_focus_tasks


def test_load_focus_tasks_filters_p0_p1_only(test_data_dir: Path) -> None:
    """Test that load_focus_tasks returns only P0 and P1 tasks.

    Uses real task data from test_data_dir fixture which creates:
    - sample-task-1: priority 1 (P1)
    - sample-task-2: priority 2 (P2)
    - sample-task-3: priority 3 (P3)

    Expected behavior:
    - Should return only tasks with priority 0 or 1
    - Should exclude priority 2 and 3 tasks
    - Results should be sorted by priority ascending (P0 before P1)

    Args:
        test_data_dir: pytest fixture providing temp task directory with sample tasks
    """
    # Load focus tasks (P0 and P1 only)
    tasks = load_focus_tasks()

    # Should only have P1 task (no P0 in test data)
    assert len(tasks) == 1, f"Expected 1 task (P1 only), got {len(tasks)}"

    # Verify it's the P1 task
    assert tasks[0].priority == 1
    assert tasks[0].title == "High Priority Task"


def test_load_focus_tasks_sorts_by_priority_ascending(test_data_dir: Path) -> None:
    """Test that load_focus_tasks sorts results by priority ascending.

    Creates additional P0 task to verify sorting (P0 before P1).

    Args:
        test_data_dir: pytest fixture providing temp task directory
    """
    # Create a P0 task in addition to existing P1 task
    inbox_dir = test_data_dir / "inbox"
    p0_task_path = inbox_dir / "urgent-task.md"

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    created = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()

    p0_content = f"""---
title: Urgent P0 Task
permalink: tasks/urgent-task
type: task
task_id: urgent-task
aliases: []
status: inbox
priority: 0
project: critical
tags: [test, urgent]
created: {created}
updated: {now}
---

# Urgent P0 Task

## Context
Critical priority 0 task for testing sort order.

## Relations
- Project: critical
- Status: inbox
"""
    p0_task_path.write_text(p0_content, encoding="utf-8")

    # Load focus tasks
    tasks = load_focus_tasks()

    # Should have 2 tasks: P0 and P1
    assert len(tasks) == 2, f"Expected 2 tasks (P0 and P1), got {len(tasks)}"

    # Verify sort order: P0 first, then P1
    assert tasks[0].priority == 0, "First task should be P0"
    assert tasks[0].title == "Urgent P0 Task"

    assert tasks[1].priority == 1, "Second task should be P1"
    assert tasks[1].title == "High Priority Task"


def test_load_focus_tasks_handles_empty_inbox(test_data_dir: Path) -> None:
    """Test that load_focus_tasks handles empty inbox gracefully.

    Args:
        test_data_dir: pytest fixture providing temp task directory
    """
    # Remove all tasks from inbox
    inbox_dir = test_data_dir / "inbox"
    for task_file in inbox_dir.glob("*.md"):
        task_file.unlink()

    # Load focus tasks - should return empty list, not error
    tasks = load_focus_tasks()

    assert tasks == [], "Expected empty list for empty inbox"
