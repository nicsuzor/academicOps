#!/usr/bin/env python3
"""Create a new task in bmem-compliant markdown format.

Usage:
    uv run python scripts/task_add.py --title "Task title" [options]

Examples:
    uv run python scripts/task_add.py --title "Review paper"
    uv run python scripts/task_add.py --title "Submit grant" --priority P1 --due 2025-11-20T17:00:00Z
    uv run python scripts/task_add.py --title "Research task" --project grants --classification Research
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bots.skills.tasks import task_ops


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
        description="Create a new task in bmem-compliant markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--title",
        required=True,
        help="Task title (required)",
    )
    parser.add_argument(
        "--priority",
        type=parse_priority,
        help="Priority level: 0-3 or P0-P3 (0/P0=urgent, 1/P1=high, 2/P2=medium, 3/P3=low)",
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
        "--tags",
        help="Comma-separated list of tags",
    )

    # Body content options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--body",
        help="Task body/description content",
    )
    group.add_argument(
        "--body-from-file",
        help="Path to a file containing the task body",
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory path (default: $ACA/data or ./data)",
    )

    args = parser.parse_args()

    # Get data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        ACA = os.environ.get("ACA")
        data_dir = Path(ACA) / "data" if ACA else Path().cwd() / "data"

    # Read body from file if specified
    body = args.body or ""
    if args.body_from_file:
        try:
            body = Path(args.body_from_file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(
                f"Error: File not found: {args.body_from_file}",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

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
            sys.exit(1)

    # Parse tags if provided
    tags = []
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    # Create task using shared library
    # Note: We'll create with all fields we can, then modify to add classification if needed
    try:
        result = task_ops.create_task(
            title=args.title,
            data_dir=data_dir,
            priority=args.priority,
            task_type="task",  # Always "task" for bmem compliance
            project=args.project,
            due=due_datetime,
            body=body,
            tags=tags,
        )

        if not result["success"]:
            print(f"✗ Failed to create task: {result['message']}", file=sys.stderr)
            return 1

        print(f"✓ Created task: {result['filename']}")
        print(f"  Path: {result['path']}")
        print(f"  Task ID: {result['task_id']}")

        # If classification was provided, modify the task to add it in ONE call
        # (create_task doesn't support classification parameter)
        if args.classification:
            modify_result = task_ops.modify_task(
                identifier=result["filename"],
                data_dir=data_dir,
                classification=args.classification,
            )
            if modify_result["success"]:
                print(f"  Classification: {args.classification}")
            else:
                print(
                    f"  Warning: Could not set classification: {modify_result['message']}",
                    file=sys.stderr,
                )

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
