#!/usr/bin/env python3
"""Create tasks using filesystem operations.

Usage:
    uv run python scripts/task_create.py --title "Task Title" --description "Description" [options]

Options:
    --title TEXT          Task title (required)
    --description TEXT    Task description (required)
    --priority INT        Priority 1-3 (default: 2)
    --type TEXT           Task type (default: task)
    --classification TEXT Task classification (optional)
    --due DATE            Due date in ISO 8601 format (optional)
    --project TEXT        Project identifier (optional)
    --tags TEXT           Comma-separated additional tags (optional)
"""

from __future__ import annotations

import argparse
import hashlib
import json
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


def generate_task_id() -> str:
    """Generate a unique task ID in format: YYYYMMDD-HHMMSS-USER-HASH

    Returns:
        Task ID like "20251106-235959-nicwin-a1b2c3d4"
    """
    now = datetime.now(UTC)
    date_prefix = now.strftime("%Y%m%d-%H%M%S")
    user = os.environ.get("USER", "user")

    # Generate short hash from timestamp + random component
    unique_str = f"{now.isoformat()}-{id(object())}"
    short_hash = hashlib.sha256(unique_str.encode()).hexdigest()[:8]

    return f"{date_prefix}-{user}-{short_hash}"


def slugify(text: str) -> str:
    """Convert text to filename-safe slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    import re

    # Convert to lowercase, replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:80]  # Limit length


def generate_tags(task_data: dict) -> list:
    """Generate tags from task metadata.

    Args:
        task_data: Task data dictionary

    Returns:
        List of tag strings
    """
    tags = []

    # Add priority as tag (this is what task_view.py expects)
    priority = task_data.get("priority", 2)
    tags.append(f"priority-p{priority}")

    # Add type as tag if not default
    if task_data.get("type") and task_data["type"] != "task":
        tags.append(task_data["type"])

    # Add classification as tag
    if task_data.get("classification"):
        tags.append(task_data["classification"].lower())

    # Add project as tag
    if task_data.get("project"):
        tags.append(f"project:{task_data['project']}")

    # Add any additional tags
    if task_data.get("extra_tags"):
        tags.extend(task_data["extra_tags"])

    return tags


def build_frontmatter(task_data: dict, task_id: str) -> dict:
    """Build YAML frontmatter for task.

    Args:
        task_data: Task data dictionary
        task_id: Generated task ID

    Returns:
        Dictionary for frontmatter
    """
    now = datetime.now(UTC).isoformat()

    # Generate slug for permalink
    slug = slugify(task_data["title"])

    frontmatter = {
        "title": task_data["title"],
        "type": "task",
        "permalink": f"tasks/inbox/{slug}",
        "tags": generate_tags(task_data),
        "created": now,
        "modified": now,
        "status": "inbox",  # New tasks always start in inbox
    }

    # Add optional fields
    if task_data.get("due"):
        frontmatter["due"] = task_data["due"]

    if task_data.get("project"):
        frontmatter["project"] = task_data["project"]

    if task_data.get("classification"):
        frontmatter["classification"] = task_data["classification"]

    return frontmatter


def build_markdown_body(task_data: dict) -> str:
    """Build markdown body for task.

    Args:
        task_data: Task data dictionary

    Returns:
        Markdown body content
    """
    parts = [task_data["description"], ""]

    # Add observations section with task details
    parts.extend(
        [
            "## Observations",
            "",
            f"- [task] {task_data['description']} #status-inbox",
        ]
    )

    if task_data.get("due"):
        parts.append(f"- [requirement] Due date: {task_data['due']} #deadline")

    parts.append("")

    # Add relations section
    if task_data.get("project"):
        parts.extend(["## Relations", "", f"- part_of [[{task_data['project']}]]", ""])

    return "\n".join(parts)


def create_task(task_data: dict) -> dict:
    """Create a new task file.

    Args:
        task_data: Task data dictionary with at minimum:
            - title: str (required)
            - description: str (required)
            - priority: int (optional, default 2)
            - type: str (optional, default "task")
            - classification: str (optional)
            - due: str (optional, ISO 8601 format)
            - project: str (optional)
            - extra_tags: list (optional)

    Returns:
        Dictionary with success status and file path
    """
    # Validate required fields
    if "title" not in task_data:
        return {"success": False, "message": "Task title is required"}
    if "description" not in task_data:
        return {"success": False, "message": "Task description is required"}

    # Generate task ID
    task_id = generate_task_id()

    # Build frontmatter
    frontmatter = build_frontmatter(task_data, task_id)

    # Build markdown content
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    body = build_markdown_body(task_data)
    content = f"---\n{yaml_str}---\n\n{body}"

    # Generate filename from title slug
    slug = slugify(task_data["title"])
    filename = f"{slug}.md"

    # Ensure inbox directory exists
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Write file
    file_path = INBOX_DIR / filename
    try:
        file_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "message": f"Task created: {filename}",
            "path": str(file_path.relative_to(DATA_DIR)),
            "filename": filename,
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to write task file: {e}"}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create a new task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--description", required=True, help="Task description")
    parser.add_argument(
        "--priority",
        type=int,
        default=2,
        choices=[1, 2, 3],
        help="Priority: 1=high, 2=medium, 3=low (default: 2)",
    )
    parser.add_argument("--type", default="task", help="Task type (default: task)")
    parser.add_argument("--classification", help="Task classification (optional)")
    parser.add_argument("--due", help="Due date in ISO 8601 format (optional)")
    parser.add_argument("--project", help="Project identifier (optional)")
    parser.add_argument("--tags", help="Comma-separated additional tags (optional)")

    args = parser.parse_args()

    # Build task data
    task_data = {
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
        "type": args.type,
    }

    if args.classification:
        task_data["classification"] = args.classification

    if args.due:
        task_data["due"] = args.due

    if args.project:
        task_data["project"] = args.project

    if args.tags:
        task_data["extra_tags"] = [tag.strip() for tag in args.tags.split(",")]

    # Create task
    result = create_task(task_data)

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  Path: {result['path']}")
        return 0
    else:
        print(f"✗ {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
