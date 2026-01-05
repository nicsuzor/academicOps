#!/usr/bin/env python3
"""Create a new task in properly formatted markdown.

Usage:
    uv run python $AOPS/skills/tasks/scripts/task_add.py --title "Task title" [options]

Examples:
    uv run python $AOPS/skills/tasks/scripts/task_add.py --title "Review paper"
    uv run python $AOPS/skills/tasks/scripts/task_add.py --title "Submit grant" --priority P1 --due 2025-11-20T17:00:00Z
    uv run python $AOPS/skills/tasks/scripts/task_add.py --title "Research task" --project grants --classification Research
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
        description="Create a new task in properly formatted markdown",
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
    parser.add_argument(
        "--slug",
        help="Optional slug for task ID (will be sanitized)",
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
        help="Data directory path (default: $ACA_DATA)",
    )
    parser.add_argument(
        "--source-email-id",
        type=str,
        help="Outlook entry_id for duplicate detection. If task with this ID exists, creation is blocked.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force creation even if duplicate source-email-id found",
    )

    args = parser.parse_args()

    # Get data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = get_data_root()

    # Check for duplicate source-email-id before creating
    if args.source_email_id and not args.force:
        tasks_dir = data_dir / "tasks"
        duplicate_found = None
        for subdir in ["inbox", "archived"]:
            search_dir = tasks_dir / subdir
            if search_dir.exists():
                for task_file in search_dir.glob("*.md"):
                    try:
                        content = task_file.read_text(encoding="utf-8")
                        if f"source_email_id: {args.source_email_id}" in content:
                            duplicate_found = task_file
                            break
                    except Exception:
                        continue
            if duplicate_found:
                break

        if duplicate_found:
            print(
                "✗ Duplicate: Email already processed as task",
                file=sys.stderr,
            )
            print(f"  Existing task: {duplicate_found.name}", file=sys.stderr)
            print("  Use --force to create anyway", file=sys.stderr)
            sys.exit(1)

    # Read body from file or argument
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

    # Prepend source email ID if provided (for future duplicate detection)
    if args.source_email_id:
        body = f"source_email_id: {args.source_email_id}\n\n{body}"

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
            task_type="task",  # Always "task" for consistency
            project=args.project,
            due=due_datetime,
            body=body,
            tags=tags,
            slug=args.slug,
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
