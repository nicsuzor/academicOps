"""Task loader for dashboard displays.

Provides filtered task loading focused on high-priority tasks.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from skills.tasks.models import Subtask, Task
from skills.tasks.task_ops import get_data_dir, load_all_tasks


def load_task_index() -> dict | None:
    """Load pre-computed task index from index.json.

    Returns:
        Parsed index dict or None if file doesn't exist.
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        return None

    index_path = Path(aca_data) / "tasks" / "index.json"
    if not index_path.exists():
        return None

    try:
        with open(index_path) as f:
            return json.load(f)
    except Exception:
        return None


def load_focus_tasks_from_index(
    task_index: dict | None = None, count: int = 20
) -> list[Task]:
    """Load high-priority focus tasks from pre-computed index.json.

    This is much faster than load_focus_tasks() as it reads from a single
    JSON file instead of parsing individual task files from disk.

    Args:
        task_index: Pre-loaded index dict (loads from disk if None)
        count: Maximum number of tasks to return

    Returns:
        List of Task models filtered to P0/P1, sorted by priority and progress.
    """
    if task_index is None:
        task_index = load_task_index()

    if not task_index:
        return []

    tasks = task_index.get("tasks", [])

    # Filter to P0/P1 non-archived tasks
    focus_entries = []
    for t in tasks:
        priority = t.get("priority")
        status = t.get("status", "")

        # Skip if no priority or P2+
        if priority is None or priority > 1:
            continue
        # Skip archived/done
        if status in ("archived", "done", "completed"):
            continue

        focus_entries.append(t)

    # Sort: incomplete subtasks first, then priority, then completion %
    def sort_key(t: dict) -> tuple[int, int, int, str]:
        priority = t.get("priority", 999)
        total = t.get("subtasks_total", 0)
        done = t.get("subtasks_done", 0)

        if total == 0:
            has_incomplete = 0
            completion_pct = 0
        else:
            has_incomplete = 0 if done < total else 1
            completion_pct = int((done / total) * 100)

        return (has_incomplete, priority, completion_pct, t.get("slug", ""))

    focus_entries.sort(key=sort_key)

    # Convert to Task models for API compatibility
    result = []
    for entry in focus_entries[:count]:
        # Build subtask list from counts (simplified - just for progress display)
        subtasks = []
        total = entry.get("subtasks_total", 0)
        done = entry.get("subtasks_done", 0)
        for i in range(total):
            subtasks.append(Subtask(text=f"Subtask {i+1}", completed=i < done))

        task = Task(
            title=entry.get("title", ""),
            priority=entry.get("priority"),
            project=entry.get("project"),
            status=entry.get("status", "inbox"),
            created=datetime.now(),  # Not stored in index, use placeholder
            subtasks=subtasks,
            filename=entry.get("file"),
        )
        result.append(task)

    return result


def _subtask_sort_key(task: Task) -> tuple[int, int, int, str]:
    """Generate sort key for tasks with subtask progress.

    Sort order:
    1. Tasks with incomplete subtasks first (has_incomplete=0 vs 1)
    2. Priority (P0 before P1)
    3. Completion ratio (less complete first)
    4. Created date (oldest first)
    """
    priority = task.priority if task.priority is not None else 999

    if not task.subtasks:
        # No subtasks = treat as incomplete, sort by priority/date
        return (0, priority, 0, str(task.created or ""))

    total = len(task.subtasks)
    completed = sum(1 for s in task.subtasks if s.completed)
    has_incomplete = 0 if completed < total else 1  # 0 = has work remaining
    completion_pct = int((completed / total) * 100) if total > 0 else 0

    return (has_incomplete, priority, completion_pct, str(task.created or ""))


def load_focus_tasks(data_dir: Path | None = None, count: int = 5) -> list[Task]:
    """Load high-priority focus tasks (P0/P1 only).

    Args:
        data_dir: Optional data directory path (uses ACA_DATA if not provided)
        count: Maximum number of tasks to return

    Returns:
        List of Task models filtered to P0/P1, sorted by:
        - Tasks with incomplete subtasks first
        - Priority (P0 before P1)
        - Completion progress (less complete first)
        - Creation date (oldest first)
    """
    # Get data directory (fail-fast if not available)
    if data_dir is None:
        data_dir = get_data_dir()

    # Load all non-archived tasks
    all_tasks = load_all_tasks(data_dir, include_archived=False)

    # Filter to P0 and P1 only
    focus_tasks = [t for t in all_tasks if t.priority is not None and t.priority <= 1]

    # Sort with subtask progress awareness
    focus_tasks.sort(key=_subtask_sort_key)

    # Return top N tasks
    return focus_tasks[:count]
