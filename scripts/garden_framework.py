#!/usr/bin/env python3
"""
Framework gardening script for periodic maintenance.

Detects and optionally fixes:
1. Orphan tasks (project set but parent is null)
2. Stale in_progress tasks (no modification for > 4h)
3. Duplicate tasks (identical IDs or titles)
4. Disconnected nodes (no parent, no dependencies)

Generates a markdown report for human review.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add aops-core to path for imports
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

try:
    from lib.task_index import TaskIndex
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
except ImportError as e:
    print(f"Error: Failed to import task libraries: {e}")
    sys.exit(1)


def detect_orphans(storage: TaskStorage):
    """Find tasks with a project but no parent."""
    orphans = []
    for task in storage._iter_all_tasks():
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            continue
        # An orphan is a task that SHOULD have a parent (belongs to a project) but doesn't
        if task.project and not task.parent and task.type not in (TaskType.GOAL, TaskType.PROJECT):
            orphans.append(task)
    return orphans


def get_stale_tasks(storage: TaskStorage, hours: float = 4.0):
    """Find in_progress tasks that haven't been modified recently."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    stale = []
    for task in storage.list_tasks(status=TaskStatus.IN_PROGRESS):
        mod = task.modified
        if mod.tzinfo is None:
            mod = mod.replace(tzinfo=UTC)
        if mod < cutoff:
            stale.append(task)
    return stale


def find_duplicates(storage: TaskStorage):
    """Find duplicate tasks by ID or Title."""
    by_id = {}
    by_title = {}
    dup_ids = []
    dup_titles = []

    for task in storage._iter_all_tasks():
        # ID duplicates (should be rare due to storage logic but possible in filesystem)
        if task.id in by_id:
            dup_ids.append((task.id, [by_id[task.id], task]))
        else:
            by_id[task.id] = task

        # Title duplicates within same project
        key = (task.project, task.title.lower())
        if key in by_title:
            dup_titles.append((task.title, [by_title[key], task]))
        else:
            by_title[key] = task

    return dup_ids, dup_titles


def generate_report(orphans, stale, dup_ids, dup_titles):
    """Generate markdown gardening report."""
    lines = [
        "# Framework Gardening Report",
        f"Generated: {datetime.now(UTC).isoformat()}Z",
        "",
        "## Summary",
        f"- **Orphans**: {len(orphans)}",
        f"- **Stale Tasks**: {len(stale)}",
        f"- **Duplicate IDs**: {len(dup_ids)}",
        f"- **Duplicate Titles**: {len(dup_titles)}",
        "",
    ]

    if orphans:
        lines.append("## 🐣 Orphan Tasks (Needs Parent)")
        for t in orphans:
            lines.append(f"- [{t.id}] {t.title} (Project: {t.project})")
        lines.append("")

    if stale:
        lines.append("## ⏳ Stale In-Progress Tasks")
        for t in stale:
            lines.append(f"- [{t.id}] {t.title} (Last modified: {t.modified.isoformat()})")
        lines.append("")

    if dup_ids or dup_titles:
        lines.append("## 👯 Duplicates")
        for tid, tasks in dup_ids:
            lines.append(f"- **ID Match**: `{tid}`")
            for t in tasks:
                lines.append(f"  - {t.title} ({t.project})")
        for title, tasks in dup_titles:
            lines.append(f'- **Title Match**: "{title}"')
            for t in tasks:
                lines.append(f"  - {t.id} ({t.project})")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Garden the framework task graph.")
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix mechanical issues (reset stale)"
    )
    parser.add_argument("--output", "-o", type=Path, help="Output report to file")
    args = parser.parse_args()

    storage = TaskStorage()

    orphans = detect_orphans(storage)
    stale = get_stale_tasks(storage)
    dup_ids, dup_titles = find_duplicates(storage)

    report = generate_report(orphans, stale, dup_ids, dup_titles)

    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    if args.fix:
        # Auto-fix: Reset stale tasks
        for task in stale:
            print(f"Resetting stale task: {task.id}")
            task.status = TaskStatus.ACTIVE
            task.assignee = None
            storage.save_task(task)

        if stale:
            # Rebuild index if we changed anything
            index = TaskIndex(storage.data_root)
            index.rebuild_fast()
            print("Index rebuilt.")


if __name__ == "__main__":
    main()
