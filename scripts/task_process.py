#!/usr/bin/env python3
"""
Task modification script for modifying local task JSON files.
Handles priority changes, due date updates, and archiving.
"""

import contextlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# Configuration
# Use current working directory for data (matches task_view.py and task_add.py)
DATA_DIR = Path.cwd() / "data"
TASKS_INBOX = DATA_DIR / "tasks" / "inbox"
TASKS_QUEUE = DATA_DIR / "tasks" / "queue"
TASKS_ARCHIVED = DATA_DIR / "tasks" / "archived"


def _validate_data_directory():
    """Validate that data directory exists.

    Fail-fast principle: Fail immediately with clear error if data directory
    doesn't exist, rather than silently searching wrong locations.

    Raises:
        SystemExit: If data directory doesn't exist
    """
    if not DATA_DIR.exists():
        print(
            f"Error: Data directory not found: {DATA_DIR}\n"
            f"Current working directory: {Path.cwd()}\n"
            f"Expected data/ subdirectory to exist in current directory.\n"
            f"Please run this script from a directory containing data/tasks/",
            file=sys.stderr,
        )
        sys.exit(1)


def print_json(obj):
    print(json.dumps(obj))


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_task_files():
    files = []
    for d in [TASKS_INBOX, TASKS_QUEUE, TASKS_ARCHIVED]:
        if d.exists():
            files.extend(sorted(d.glob("*.json")))
    return files


def _find_task_by_id(task_id: str):
    if not task_id:
        return None
    for p in _iter_task_files():
        if p.stem == task_id:
            t = _load_json(p)
            if isinstance(t, dict):
                return (p, t)
    return None


def _archive_local_task(task_path: Path, task: dict):
    TASKS_ARCHIVED.mkdir(parents=True, exist_ok=True)
    task["archived_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    dest = TASKS_ARCHIVED / task_path.name
    dest.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    if task_path.exists():
        with contextlib.suppress(Exception):
            task_path.unlink()
    return dest


def modify_task(
    task_id,
    archive=False,
    priority=None,
    due=None,
):
    """Modify a local task (priority, due date, archive).

    Args:
        task_id: The local task ID (YYYYMMDD-XXXXXXXX format)
        archive: Whether to archive the task
        priority: New priority for the task (1-3)
        due: New due date for the task (YYYY-MM-DD format)
    """

    # Check if we have any actions
    has_actions = archive or priority is not None or due is not None
    if not has_actions:
        print_json(
            {
                "success": False,
                "error": "no_actions",
                "message": "No actions specified.",
            }
        )
        return {}

    # Find the local task
    task_id_pattern = re.compile(r"^\d{8}-[0-9a-fA-F]{8}$")
    local_task = _find_task_by_id(task_id)

    if not local_task and not task_id_pattern.match(str(task_id) or ""):
        print_json(
            {
                "success": False,
                "error": "invalid_task_id",
                "message": f"Invalid task ID format: {task_id}. Expected YYYYMMDD-XXXXXXXX",
            }
        )
        return {}

    if not local_task:
        print_json(
            {
                "success": False,
                "error": "task_not_found",
                "message": f"No local task with ID: {task_id}",
            }
        )
        return {}

    task_path, task = local_task
    result = {"success": True, "local": True, "taskId": task_id}
    modified_fields = []

    if priority is not None:
        try:
            task["priority"] = int(priority)
            modified_fields.append("priority")
        except (ValueError, TypeError):
            print_json(
                {
                    "success": False,
                    "error": "invalid_priority",
                    "message": "Priority must be an integer.",
                }
            )
            return {}

    if due is not None:
        task["due"] = due
        modified_fields.append("due")

    if modified_fields:
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2))
        result["modified"] = modified_fields

    if archive:
        dest = _archive_local_task(task_path, task)
        result.update({"archived": True, "taskPath": str(dest.relative_to(DATA_DIR))})

    return result


def main():
    # Validate data directory exists (fail-fast)
    _validate_data_directory()

    if len(sys.argv) < 2:
        print(
            "Usage: task_process.py modify <task_id> [--archive] [--priority N] [--due YYYY-MM-DD]"
        )
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "modify":
        if len(sys.argv) < 3:
            print(
                "Usage: task_process.py modify <task_id> [--archive] [--priority 1] [--due YYYY-MM-DD]"
            )
            sys.exit(1)
        task_id = sys.argv[2]
        archive = False
        priority = None
        due = None
        i = 3
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--archive":
                archive = True
                i += 1
            elif arg == "--priority" and i + 1 < len(sys.argv):
                priority = sys.argv[i + 1]
                i += 2
            elif arg == "--due" and i + 1 < len(sys.argv):
                due = sys.argv[i + 1]
                i += 2
            else:
                print(f"Unknown or incomplete modify argument: {arg}")
                sys.exit(1)
        result = modify_task(task_id, archive=archive, priority=priority, due=due)
        print_json(result)

    else:
        print(f"Unknown command: {cmd}")
        print("Available commands: modify")
        sys.exit(1)


if __name__ == "__main__":
    main()
