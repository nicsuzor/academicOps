"""Task loader for dashboard displays.

Provides filtered task loading focused on high-priority tasks.
"""

from __future__ import annotations

from pathlib import Path

from skills.tasks.models import Task
from skills.tasks.task_ops import get_data_dir, load_all_tasks


def load_focus_tasks(data_dir: Path | None = None, count: int = 5) -> list[Task]:
    """Load high-priority focus tasks (P0/P1 only).

    Args:
        data_dir: Optional data directory path (uses ACA_DATA if not provided)
        count: Maximum number of tasks to return

    Returns:
        List of Task models filtered to P0/P1, sorted by priority ascending
    """
    # Get data directory (fail-fast if not available)
    if data_dir is None:
        data_dir = get_data_dir()

    # Load all non-archived tasks
    all_tasks = load_all_tasks(data_dir, include_archived=False)

    # Filter to P0 and P1 only
    focus_tasks = [t for t in all_tasks if t.priority is not None and t.priority <= 1]

    # Sort by priority ascending (P0 before P1)
    focus_tasks.sort(key=lambda t: t.priority if t.priority is not None else 999)

    # Return top N tasks
    return focus_tasks[:count]
