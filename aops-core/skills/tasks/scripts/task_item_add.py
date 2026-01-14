#!/usr/bin/env python3
"""Add a checklist item to an existing task.

Adds Obsidian Tasks-compatible checklist items to task files.
Items are appended to a ## Checklist section (created if needed).

Usage:
    uv run python $AOPS/skills/tasks/scripts/task_item_add.py TASK_ID --item "Description"

Examples:
    uv run python $AOPS/skills/tasks/scripts/task_item_add.py 20251215-abc123 --item "Review draft"
    uv run python $AOPS/skills/tasks/scripts/task_item_add.py 20251215-abc123.md --item "Send email" --due 2025-01-15
    uv run python $AOPS/skills/tasks/scripts/task_item_add.py "#3" --item "Follow up" --priority high
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Bootstrap: Add AOPS root to path for lib imports
_script_path = Path(__file__).resolve()
_aops_root = _script_path.parents[3]  # scripts/ -> tasks/ -> skills/ -> AOPS
if str(_aops_root) not in sys.path:
    sys.path.insert(0, str(_aops_root))
os.environ.setdefault("AOPS", str(_aops_root))

from lib.paths import get_data_root
from skills.tasks import task_ops


def format_checklist_item(
    description: str,
    done: bool = False,
    due: str | None = None,
    priority: str | None = None,
) -> str:
    """Format a checklist item in Dataview/Obsidian Tasks format.

    Uses Dataview inline fields: [due:: DATE], [priority:: VALUE], [completion:: DATE]

    Args:
        description: Item description text
        done: Whether item is completed
        due: Optional due date (YYYY-MM-DD)
        priority: Optional priority (high, medium, low)

    Returns:
        Formatted checklist line
    """
    checkbox = "[x]" if done else "[ ]"
    parts = [f"- {checkbox} {description}"]

    # Add priority as Dataview field
    if priority:
        parts.append(f"[priority:: {priority.lower()}]")

    # Add due date as Dataview field
    if due:
        parts.append(f"[due:: {due}]")

    # Add completion date if done
    if done:
        parts.append(f"[completion:: {datetime.now().strftime('%Y-%m-%d')}]")

    return " ".join(parts)


def add_checklist_item(file_path: Path, item_line: str) -> dict:
    """Add a checklist item to a task file.

    Finds or creates a ## Checklist section and appends the item.

    Args:
        file_path: Path to task markdown file
        item_line: Formatted checklist item line

    Returns:
        Result dict with success status and message
    """
    if not file_path.exists():
        return {"success": False, "message": f"Task file not found: {file_path}"}

    content = file_path.read_text(encoding="utf-8")

    # Check if ## Checklist section exists
    checklist_pattern = r"(## Checklist\n)(.*?)(?=\n## |\Z)"
    match = re.search(checklist_pattern, content, re.DOTALL)

    if match:
        # Append to existing Checklist section
        section_header = match.group(1)
        section_content = match.group(2).rstrip()

        # Add item with proper spacing
        if section_content:
            new_section = f"{section_header}{section_content}\n{item_line}\n"
        else:
            new_section = f"{section_header}\n{item_line}\n"

        content = content[: match.start()] + new_section + content[match.end() :]
    else:
        # Create new Checklist section before ## Relations (or at end)
        relations_match = re.search(r"\n## Relations", content)
        if relations_match:
            insert_pos = relations_match.start()
            content = (
                content[:insert_pos]
                + f"\n## Checklist\n\n{item_line}\n"
                + content[insert_pos:]
            )
        else:
            # Append at end
            content = content.rstrip() + f"\n\n## Checklist\n\n{item_line}\n"

    # Write updated content
    file_path.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "message": f"Added checklist item to {file_path.name}",
        "item": item_line,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Add a checklist item to an existing task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "task_id",
        help="Task identifier (filename, task ID, or #index from current view)",
    )
    parser.add_argument(
        "--item",
        required=True,
        help="Checklist item description (required)",
    )
    parser.add_argument(
        "--due",
        help="Due date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Item priority (high, medium, low)",
    )
    parser.add_argument(
        "--done",
        action="store_true",
        help="Mark item as already completed",
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

    # Resolve task identifier to filename
    try:
        filename = task_ops.resolve_identifier(args.task_id, data_dir)
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1

    # Find task file
    task_path = task_ops.find_task_file(filename, data_dir)
    if not task_path:
        print(f"✗ Task not found: {filename}", file=sys.stderr)
        return 1

    # Format checklist item
    item_line = format_checklist_item(
        description=args.item,
        done=args.done,
        due=args.due,
        priority=args.priority,
    )

    # Add item to task
    result = add_checklist_item(task_path, item_line)

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  {result['item']}")
        return 0
    else:
        print(f"✗ {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
