#!/usr/bin/env python3
"""Modify tasks using filesystem operations.

Usage:
    uv run python scripts/task_modify.py <filename> [options]

    Examples:
        uv run python scripts/task_modify.py "Implement Owl.md" --priority 1
        uv run python scripts/task_modify.py "task.md" --status queue --due 2025-11-15

Options:
    --priority INT        Update priority (1-3)
    --status TEXT         Update status (inbox/queue/active/archived)
    --type TEXT           Update task type
    --project TEXT        Update project
    --due DATE            Update due date (ISO 8601)
    --add-note TEXT       Append note to task body
"""

from __future__ import annotations

import argparse
import os
import sys
import yaml
from datetime import UTC, datetime
from pathlib import Path

# Base data directory: ${ACA}/data or fallback to ./data
AO = os.environ.get("ACA")
if AO:
    DATA_DIR = Path(AO) / "data"
else:
    DATA_DIR = Path().cwd() / "data"

INBOX_DIR = DATA_DIR / "tasks/inbox"
QUEUE_DIR = DATA_DIR / "tasks/queue"
ARCHIVED_DIR = DATA_DIR / "tasks/archived"


def find_task_file(filename: str) -> Path | None:
    """Find task file in inbox, queue, or archived directories.

    Args:
        filename: Task filename (with or without .md extension)

    Returns:
        Path to task file or None if not found
    """
    if not filename.endswith(".md"):
        filename = filename + ".md"

    # Check inbox first
    inbox_path = INBOX_DIR / filename
    if inbox_path.exists():
        return inbox_path

    # Check queue
    queue_path = QUEUE_DIR / filename
    if queue_path.exists():
        return queue_path

    # Check archived
    archived_path = ARCHIVED_DIR / filename
    if archived_path.exists():
        return archived_path

    return None


def update_priority_tag(tags: list, new_priority: int) -> list:
    """Update priority tag in tags list.

    Args:
        tags: Current tags list
        new_priority: New priority value (1-3)

    Returns:
        Updated tags list
    """
    # Remove any existing priority tags
    tags = [t for t in tags if not (isinstance(t, str) and t.startswith("priority-p"))]

    # Add new priority tag
    tags.append(f"priority-p{new_priority}")

    return tags


def update_frontmatter_fields(
    content: str,
    priority: int | None = None,
    status: str | None = None,
    task_type: str | None = None,
    project: str | None = None,
    due: str | None = None,
) -> tuple[str, list[str]]:
    """Update fields in YAML frontmatter.

    Args:
        content: Full markdown content with YAML frontmatter
        priority: New priority value
        status: New status value
        task_type: New task type
        project: New project
        due: New due date

    Returns:
        Tuple of (updated_content, list of modified fields)
    """
    if not content.startswith("---"):
        raise ValueError("Invalid task format: missing frontmatter")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid task format: malformed frontmatter")

    # Parse frontmatter
    frontmatter = yaml.safe_load(parts[1])
    if not isinstance(frontmatter, dict):
        raise ValueError("Invalid frontmatter: not a dictionary")

    modified_fields = []

    # Update fields
    if priority is not None:
        frontmatter["priority"] = priority
        # Update priority tag
        tags = frontmatter.get("tags", [])
        frontmatter["tags"] = update_priority_tag(tags, priority)
        modified_fields.append("priority")

    if status is not None:
        frontmatter["status"] = status
        modified_fields.append("status")

    if task_type is not None:
        frontmatter["type"] = task_type
        modified_fields.append("type")

    if project is not None:
        frontmatter["project"] = project
        # Also update project tag
        tags = frontmatter.get("tags", [])
        # Remove old project tags
        tags = [
            t for t in tags if not (isinstance(t, str) and t.startswith("project:"))
        ]
        # Add new project tag
        tags.append(f"project:{project}")
        frontmatter["tags"] = tags
        modified_fields.append("project")

    if due is not None:
        frontmatter["due"] = due
        modified_fields.append("due")

    # Update modified timestamp
    if modified_fields:
        frontmatter["modified"] = datetime.now(UTC).isoformat()

    # Rebuild content
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    body = parts[2]

    return f"---\n{yaml_str}---{body}", modified_fields


def append_note(content: str, note: str) -> str:
    """Append a note to the task body.

    Args:
        content: Full markdown content
        note: Note to append

    Returns:
        Updated content
    """
    # Add timestamp to note
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    formatted_note = f"\n## Note ({timestamp})\n\n{note}\n"

    return content + formatted_note


def modify_task(
    filename: str,
    priority: int | None = None,
    status: str | None = None,
    task_type: str | None = None,
    project: str | None = None,
    due: str | None = None,
    add_note: str | None = None,
) -> dict:
    """Modify a task's fields.

    Args:
        filename: Task filename
        priority: New priority (1-3)
        status: New status
        task_type: New task type
        project: New project
        due: New due date (ISO 8601)
        add_note: Note to append

    Returns:
        Result dictionary with success status and message
    """
    # Find task file
    task_path = find_task_file(filename)
    if not task_path:
        return {"success": False, "message": f"Task not found: {filename}"}

    # Read current content
    try:
        content = task_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "message": f"Failed to read task: {e}"}

    # Update frontmatter fields
    try:
        content, modified_fields = update_frontmatter_fields(
            content,
            priority=priority,
            status=status,
            task_type=task_type,
            project=project,
            due=due,
        )
    except Exception as e:
        return {"success": False, "message": f"Failed to update frontmatter: {e}"}

    # Append note if provided
    if add_note:
        content = append_note(content, add_note)
        modified_fields.append("notes")

    # Check if anything was modified
    if not modified_fields:
        return {"success": False, "message": "No modifications specified"}

    # Write updated content
    try:
        task_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "message": f"Modified {', '.join(modified_fields)}",
            "path": str(task_path.relative_to(DATA_DIR)),
            "modified_fields": modified_fields,
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to write task: {e}"}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Modify a task's fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "filename", help="Task filename (with or without .md extension)"
    )
    parser.add_argument(
        "--priority", type=int, choices=[1, 2, 3], help="Update priority"
    )
    parser.add_argument(
        "--status",
        choices=["inbox", "queue", "active", "archived"],
        help="Update status",
    )
    parser.add_argument("--type", dest="task_type", help="Update task type")
    parser.add_argument("--project", help="Update project")
    parser.add_argument("--due", help="Update due date (ISO 8601)")
    parser.add_argument("--add-note", help="Append note to task")

    args = parser.parse_args()

    # Modify task
    result = modify_task(
        filename=args.filename,
        priority=args.priority,
        status=args.status,
        task_type=args.task_type,
        project=args.project,
        due=args.due,
        add_note=args.add_note,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        if "path" in result:
            print(f"  Path: {result['path']}")
        return 0
    else:
        print(f"✗ {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
