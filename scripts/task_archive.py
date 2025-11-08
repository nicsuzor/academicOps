#!/usr/bin/env python3
"""Archive/unarchive tasks using filesystem operations.

Usage:
    uv run python scripts/task_archive.py <task_filename> [options]

    Examples:
        uv run python scripts/task_archive.py "Implement Owl.md"
        uv run python scripts/task_archive.py "20251106-abc123.md" --unarchive

Options:
    --unarchive     Move task back to inbox (unarchive)
"""

from __future__ import annotations

import argparse
import os
import shutil
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
    """Find task file in inbox or queue directories.

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

    return None


def find_archived_task(filename: str) -> Path | None:
    """Find task file in archived directory.

    Args:
        filename: Task filename (with or without .md extension)

    Returns:
        Path to archived task file or None if not found
    """
    if not filename.endswith(".md"):
        filename = filename + ".md"

    archived_path = ARCHIVED_DIR / filename
    if archived_path.exists():
        return archived_path

    return None


def update_task_frontmatter(
    content: str, new_status: str, add_archived_at: bool = False
) -> str:
    """Update task frontmatter status and archived_at.

    Args:
        content: Full markdown content with YAML frontmatter
        new_status: New status value
        add_archived_at: Whether to add archived_at timestamp

    Returns:
        Updated content
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

    # Update status
    frontmatter["status"] = new_status
    frontmatter["modified"] = datetime.now(UTC).isoformat()

    # Add archived_at if archiving
    if add_archived_at:
        frontmatter["archived_at"] = frontmatter["modified"]

    # Remove archived_at if unarchiving
    if not add_archived_at and "archived_at" in frontmatter:
        del frontmatter["archived_at"]

    # Rebuild content
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    body = parts[2]

    return f"---\n{yaml_str}---{body}"


def archive_task(filename: str) -> dict[str, str]:
    """Archive a task by moving it to archived folder.

    Args:
        filename: Task filename

    Returns:
        Result dictionary with success status and message
    """
    # Find task in inbox or queue
    task_path = find_task_file(filename)
    if not task_path:
        return {"success": False, "message": f"Task not found: {filename}"}

    # Read and update content
    try:
        content = task_path.read_text(encoding="utf-8")
        updated_content = update_task_frontmatter(
            content, new_status="archived", add_archived_at=True
        )
    except Exception as e:
        return {"success": False, "message": f"Failed to update task frontmatter: {e}"}

    # Ensure archived directory exists
    ARCHIVED_DIR.mkdir(parents=True, exist_ok=True)

    # Write to archived location
    archived_path = ARCHIVED_DIR / task_path.name
    try:
        archived_path.write_text(updated_content, encoding="utf-8")
        # Remove original
        task_path.unlink()

        return {
            "success": True,
            "message": f"Archived: {task_path.name}",
            "from": str(task_path.relative_to(DATA_DIR)),
            "to": str(archived_path.relative_to(DATA_DIR)),
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to move task: {e}"}


def unarchive_task(filename: str) -> dict[str, str]:
    """Unarchive a task by moving it back to inbox.

    Args:
        filename: Task filename

    Returns:
        Result dictionary with success status and message
    """
    # Find task in archived
    task_path = find_archived_task(filename)
    if not task_path:
        return {"success": False, "message": f"Archived task not found: {filename}"}

    # Read and update content
    try:
        content = task_path.read_text(encoding="utf-8")
        updated_content = update_task_frontmatter(
            content, new_status="inbox", add_archived_at=False
        )
    except Exception as e:
        return {"success": False, "message": f"Failed to update task frontmatter: {e}"}

    # Ensure inbox directory exists
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Write to inbox location
    inbox_path = INBOX_DIR / task_path.name
    try:
        inbox_path.write_text(updated_content, encoding="utf-8")
        # Remove from archived
        task_path.unlink()

        return {
            "success": True,
            "message": f"Unarchived: {task_path.name}",
            "from": str(task_path.relative_to(DATA_DIR)),
            "to": str(inbox_path.relative_to(DATA_DIR)),
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to move task: {e}"}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Archive or unarchive a task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "filename", help="Task filename (with or without .md extension)"
    )
    parser.add_argument(
        "--unarchive", action="store_true", help="Move task back to inbox (unarchive)"
    )

    args = parser.parse_args()

    # Archive or unarchive
    if args.unarchive:
        result = unarchive_task(args.filename)
    else:
        result = archive_task(args.filename)

    if result["success"]:
        print(f"✓ {result['message']}")
        if "from" in result and "to" in result:
            print(f"  {result['from']} → {result['to']}")
        return 0
    else:
        print(f"✗ {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
