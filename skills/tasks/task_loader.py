"""Task loader for dashboard displays.

Provides filtered task loading focused on high-priority tasks.
"""

from __future__ import annotations

from pathlib import Path

from skills.tasks.models import Task
from skills.tasks.task_ops import get_data_dir, load_all_tasks


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
