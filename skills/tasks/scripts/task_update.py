#!/usr/bin/env python3
"""Update an existing task's fields.

Usage:
    uv run python $AOPS/skills/tasks/scripts/task_update.py <task_identifier> [options]

Examples:
    uv run python $AOPS/skills/tasks/scripts/task_update.py "20251124-016d335c.md" --priority 0
    uv run python $AOPS/skills/tasks/scripts/task_update.py "task.md" --priority P1 --project "new-project"
    uv run python $AOPS/skills/tasks/scripts/task_update.py "3" --title "Updated title" --due 2025-12-15T17:00:00Z
    uv run python $AOPS/skills/tasks/scripts/task_update.py "task.md" --add-tags "urgent,review" --remove-tags "low-priority"

Options:
    --priority=N          Set priority (0-3 or P0-P3)
    --title=TEXT          Update title
    --project=SLUG        Update project slug
    --classification=TYPE Update classification (e.g., Action, Research, Review)
    --due=ISO_DATE        Update due date (ISO8601 format)
    --status=STATUS       Update status
    --add-tags=TAGS       Add tags (comma-separated)
    --remove-tags=TAGS    Remove tags (comma-separated)
    --data-dir=PATH       Use custom data directory
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Bootstrap: Add AOPS root to path for lib imports (works from any directory)
_script_path = Path(__file__).resolve()
_aops_root = _script_path.parents[3]  # scripts/ -> tasks/ -> skills/ -> AOPS
if str(_aops_root) not in sys.path:
    sys.path.insert(0, str(_aops_root))
os.environ.setdefault("AOPS", str(_aops_root))

from lib.paths import get_data_root
from skills.tasks import task_ops


def parse_priority(value: str) -> int:
    """Parse priority value accepting both numeric (0-3) and prefixed (P0-P3) formats.

    Args:
        value: Priority as string - either '0'/'1'/'2'/'3' or 'P0'/'P1'/'P2'/'P3'

    Returns:
        int: Normalized priority value (0-3)

    Raises:
        argparse.ArgumentTypeError: If value is not a valid priority format
    """
    # Handle P-prefixed format (P0, P1, P2, P3)
    if value.upper().startswith("P"):
        try:
            priority_num = int(value[1:])
            if 0 <= priority_num <= 3:
                return priority_num
        except (ValueError, IndexError):
            pass

    # Handle numeric format (0, 1, 2, 3)
    try:
        priority_num = int(value)
        if 0 <= priority_num <= 3:
            return priority_num
    except ValueError:
        pass

    # Invalid format
    msg = (
        f"Invalid priority '{value}'. Valid formats: 0-3 or P0-P3 "
        f"(e.g., '0' or 'P0' for urgent, '1' or 'P1' for high priority)"
    )
    raise argparse.ArgumentTypeError(msg)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Update an existing task's fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "identifier",
        help="Task identifier (filename, task ID, or index from view)",
    )

    # Field update options
    parser.add_argument(
        "--priority",
        type=parse_priority,
        help="Priority level: 0-3 or P0-P3 (0/P0=urgent, 1/P1=high, 2/P2=medium, 3/P3=low)",
    )
    parser.add_argument(
        "--title",
        help="New title",
    )
    parser.add_argument(
        "--project",
        help="Project slug for categorization",
    )
    parser.add_argument(
        "--classification",
        help="Task classification (e.g., Action, Research, Review)",
    )
    parser.add_argument(
        "--due",
        help="Due date in ISO8601 format (e.g., 2025-11-20T17:00:00Z)",
    )
    parser.add_argument(
        "--status",
        help="Task status (e.g., inbox, in_progress, blocked)",
    )
    parser.add_argument(
        "--add-tags",
        help="Comma-separated list of tags to add",
    )
    parser.add_argument(
        "--remove-tags",
        help="Comma-separated list of tags to remove",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory path (default: $ACA_DATA)",
    )

    args = parser.parse_args()

    # Get data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = get_data_root()

    # Validate that at least one update field is provided
    has_updates = any(
        [
            args.priority is not None,
            args.title,
            args.project,
            args.classification,
            args.due,
            args.status,
            args.add_tags,
            args.remove_tags,
        ]
    )

    if not has_updates:
        print(
            "Error: No updates specified. Provide at least one update option.",
            file=sys.stderr,
        )
        print("Use --help for available options.", file=sys.stderr)
        return 1

    # Parse due date if provided
    due_datetime = None
    if args.due:
        try:
            # Handle both Z and +00:00 formats
            due_str = (
                args.due.replace("Z", "+00:00") if args.due.endswith("Z") else args.due
            )
            due_datetime = datetime.fromisoformat(due_str)
        except ValueError as e:
            print(f"Error: Invalid due date format: {e}", file=sys.stderr)
            print("Expected format: YYYY-MM-DDTHH:MM:SSZ", file=sys.stderr)
            return 1

    # Parse tags if provided
    add_tags = []
    if args.add_tags:
        add_tags = [tag.strip() for tag in args.add_tags.split(",") if tag.strip()]

    remove_tags = []
    if args.remove_tags:
        remove_tags = [
            tag.strip() for tag in args.remove_tags.split(",") if tag.strip()
        ]

    # Update task using shared library
    try:
        result = task_ops.modify_task(
            identifier=args.identifier,
            data_dir=data_dir,
            title=args.title,
            priority=args.priority,
            project=args.project,
            classification=args.classification,
            due=due_datetime,
            status=args.status,
            add_tags=add_tags if add_tags else None,
            remove_tags=remove_tags if remove_tags else None,
        )

        if not result["success"]:
            print(f"✗ Failed to update task: {result['message']}", file=sys.stderr)
            return 1

        print(f"✓ {result['message']}")
        if result.get("modified_fields"):
            fields_str = ", ".join(result["modified_fields"])
            print(f"  Modified fields: {fields_str}")
        print(f"  Task ID: {result['task_id']}")

        return 0

    except task_ops.TaskDirectoryNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        print(f"  Data directory must exist: {data_dir}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
