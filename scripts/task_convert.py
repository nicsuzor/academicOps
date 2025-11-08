#!/usr/bin/env python3
"""
Convert JSON tasks to Markdown format for Basic Memory integration.

Usage:
    python task_convert.py [--dry-run] [--limit N]

Options:
    --dry-run: Show what would be converted without actually converting
    --limit N: Only convert first N tasks (for testing)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Add writing repo to path for potential imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def determine_status(json_path: Path) -> str:
    """Determine task status from directory location or filename."""
    path_str = str(json_path)

    if "inbox" in json_path.parts:
        return "inbox"
    elif "queue" in json_path.parts:
        return "queue"
    elif "archived" in path_str or "archive" in path_str:
        return "archived"
    else:
        return "inbox"  # default


def generate_tags(task: Dict[str, Any]) -> List[str]:
    """Generate tags from task metadata."""
    tags = []

    # Add type as tag
    if task.get("type"):
        tags.append(task["type"])

    # Add classification as tag
    if task.get("classification"):
        tags.append(task["classification"].lower())

    # Add project as tag
    if task.get("project"):
        tags.append(f"project:{task['project']}")

    return tags


def format_markdown(task: Dict[str, Any], status: str) -> str:
    """Convert JSON task to Basic Memory compliant markdown format."""

    task_id = task["id"]
    title = task["title"]
    priority = task["priority"]
    project = task.get("project", "")

    # Build BM-compliant frontmatter
    frontmatter = {
        "title": title,
        "permalink": f"tasks/{task_id}",  # BM standard format
        "type": "task",  # Standard BM entity type
        "tags": generate_tags(task),
        "created": task["created"],
        "modified": task.get("archived_at")
        if status == "archived"
        else task["created"],
    }

    # Add custom task fields (BM allows custom fields)
    frontmatter["task_id"] = task_id
    frontmatter["priority"] = priority
    frontmatter["status"] = status

    if task.get("due"):
        frontmatter["due"] = task["due"]

    if project:
        frontmatter["project"] = project

    if task.get("classification"):
        frontmatter["classification"] = task["classification"]

    # Preserve source and metadata
    if task.get("source"):
        frontmatter["source"] = task["source"]
    if task.get("metadata"):
        frontmatter["metadata"] = task["metadata"]

    # Extract description for observations
    description = (
        task.get("description") or task.get("summary") or task.get("preview", "")
    )
    preview = task.get("preview", "")

    # Build markdown body with BM structure
    body_parts = [
        f"# {title}",
        "",
        "## Context",
        "",
        description if description else "(No description provided)",
        "",
        "## Observations",
        "",
    ]

    # Add observations from task data
    status_tag = f"#status-{status}"
    priority_tag = f"#priority-p{priority}"

    # Main task observation
    if description:
        body_parts.append(f"- [task] {description} {status_tag} {priority_tag}")

    # Due date as requirement
    if task.get("due"):
        due_date = task["due"]
        body_parts.append(f"- [requirement] Due date: {due_date} #deadline")

    # Classification as observation
    if task.get("classification"):
        classification = task["classification"]
        body_parts.append(
            f"- [classification] Type: {classification} #type-{classification.lower()}"
        )

    # Task type as observation
    task_type = task.get("type", "unknown")
    if task_type and task_type != "unknown":
        body_parts.append(f"- [fact] Task type: {task_type} #type-{task_type}")

    # Source as observation
    if task.get("source"):
        source = task["source"]
        body_parts.append(f"- [fact] Source: {source}")

    # Email metadata as observations
    if task.get("metadata"):
        metadata = task["metadata"]
        if metadata.get("sender_name"):
            body_parts.append(f"- [fact] From: {metadata['sender_name']}")
        if metadata.get("email_id"):
            body_parts.append(
                f"- [fact] Email ID: {metadata['email_id'][:20]}... #email"
            )

    # Add preview if different from description
    if preview and preview != description:
        body_parts.extend(["", "## Preview", "", preview])

    body_parts.extend(["", "## Relations", ""])

    # Add project relation if present
    if project:
        # Capitalize and format project name for BM entity reference
        project_title = project.replace("-", " ").title()
        body_parts.append(f"- part_of [[{project_title}]]")

    # Combine frontmatter and body
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    md_content = f"---\n{yaml_str}---\n\n" + "\n".join(body_parts)

    return md_content


def convert_task(json_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """Convert a single JSON task to markdown."""
    try:
        # Read JSON
        with open(json_path, "r", encoding="utf-8") as f:
            task = json.load(f)

        # Determine status and output location
        status = determine_status(json_path)
        status_dir = output_dir / status

        # Generate markdown
        md_content = format_markdown(task, status)

        # Determine output filename (preserve ID)
        task_id = task["id"]
        md_filename = f"{task_id}.md"
        md_path = status_dir / md_filename

        if dry_run:
            print(f"Would convert: {json_path} -> {md_path}")
            return True

        # Ensure output directory exists
        status_dir.mkdir(parents=True, exist_ok=True)

        # Write markdown file
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"✓ Converted: {task_id} ({status})")
        return True

    except Exception as e:
        print(f"✗ Error converting {json_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert JSON tasks to Markdown")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be converted"
    )
    parser.add_argument("--limit", type=int, help="Limit number of tasks to convert")
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data/tasks"), help="Input directory"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/tasks"), help="Output directory"
    )

    args = parser.parse_args()

    # Find all JSON files
    json_files = list(args.input_dir.rglob("*.json"))
    total = len(json_files)

    print(f"Found {total} JSON task files")

    if args.limit:
        json_files = json_files[: args.limit]
        print(f"Limiting to {args.limit} tasks")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be written\n")

    # Convert each file
    converted = 0
    failed = 0

    for json_path in json_files:
        if convert_task(json_path, args.output_dir, args.dry_run):
            converted += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Conversion {'simulation' if args.dry_run else 'complete'}:")
    print(f"  Total: {total}")
    print(f"  Converted: {converted}")
    print(f"  Failed: {failed}")
    print(f"{'=' * 60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
