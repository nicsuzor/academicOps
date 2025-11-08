#!/usr/bin/env python3
"""Search tasks using filesystem text matching.

Usage:
    uv run python scripts/task_search.py "search query" [options]

    Examples:
        uv run python scripts/task_search.py "automod"
        uv run python scripts/task_search.py "demo" --priority 1
        uv run python scripts/task_search.py "meeting" --status inbox --limit 5

Options:
    --priority INT        Filter by priority (1-3)
    --status TEXT         Filter by status (inbox/queue/archived)
    --type TEXT           Filter by task type
    --project TEXT        Filter by project
    --limit INT           Max results (default: 10)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import yaml
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


def load_task(path: Path) -> dict | None:
    """Load a task from markdown file with YAML frontmatter.

    Args:
        path: Path to task file

    Returns:
        Task dictionary or None if load failed
    """
    try:
        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return None

        if not isinstance(frontmatter, dict):
            return None

        # Add filename and body
        frontmatter["_filename"] = path.name
        frontmatter["_path"] = str(path.relative_to(DATA_DIR))
        frontmatter["_body"] = parts[2].strip()

        # Extract priority from tags if not in frontmatter
        if "priority" not in frontmatter or frontmatter["priority"] is None:
            tags = frontmatter.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag.startswith("priority-p"):
                        try:
                            frontmatter["priority"] = int(tag.replace("priority-p", ""))
                            break
                        except (ValueError, IndexError):
                            pass

        return frontmatter
    except Exception:
        return None


def matches_filters(
    task: dict,
    priority: int | None = None,
    status: str | None = None,
    task_type: str | None = None,
    project: str | None = None,
) -> bool:
    """Check if task matches filter criteria.

    Args:
        task: Task dictionary
        priority: Filter by priority
        status: Filter by status
        task_type: Filter by task type
        project: Filter by project

    Returns:
        True if task matches all filters
    """
    if priority is not None:
        if task.get("priority") != priority:
            return False

    if status is not None:
        if task.get("status") != status:
            return False

    if task_type is not None:
        if task.get("type") != task_type:
            return False

    if project is not None:
        task_project = task.get("project", "")
        # Check if project matches or if project tag exists
        if task_project != project:
            tags = task.get("tags", [])
            if f"project:{project}" not in tags:
                return False

    return True


def text_match_score(task: dict, query: str) -> float:
    """Calculate simple text match score for task.

    Args:
        task: Task dictionary
        query: Search query

    Returns:
        Match score (0.0 to 1.0)
    """
    query_lower = query.lower()
    score = 0.0

    # Title match (highest weight)
    title = task.get("title", "").lower()
    if query_lower in title:
        score += 0.5
        # Bonus for exact match
        if title == query_lower:
            score += 0.3

    # Body match
    body = task.get("_body", "").lower()
    if query_lower in body:
        score += 0.2

    # Tags match
    tags = task.get("tags", [])
    for tag in tags:
        if isinstance(tag, str) and query_lower in tag.lower():
            score += 0.1
            break

    # Project match
    project = task.get("project", "").lower()
    if query_lower in project:
        score += 0.1

    return min(score, 1.0)


def search_tasks(
    query: str,
    priority: int | None = None,
    status: str | None = None,
    task_type: str | None = None,
    project: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search tasks using filesystem text matching.

    Args:
        query: Search query
        priority: Filter by priority (1-3)
        status: Filter by status
        task_type: Filter by task type
        project: Filter by project
        limit: Max results

    Returns:
        List of matching tasks sorted by relevance
    """
    # Collect all task files
    task_paths = []

    # Default to searching inbox and queue only, unless status specified
    if status == "archived":
        dirs = [ARCHIVED_DIR]
    elif status in ("inbox", "queue"):
        dirs = [INBOX_DIR if status == "inbox" else QUEUE_DIR]
    else:
        # Search inbox and queue by default
        dirs = [d for d in [INBOX_DIR, QUEUE_DIR] if d.exists()]

    for directory in dirs:
        if directory.exists():
            task_paths.extend(directory.glob("*.md"))

    # Load and filter tasks
    results = []
    for path in task_paths:
        task = load_task(path)
        if not task:
            continue

        # Skip archived tasks unless explicitly searching archived
        if status != "archived" and task.get("archived_at"):
            continue

        # Apply filters
        if not matches_filters(task, priority, status, task_type, project):
            continue

        # Calculate match score
        score = text_match_score(task, query)
        if score > 0:
            results.append({"task": task, "score": score})

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Limit results
    return [r["task"] for r in results[:limit]]


def format_results(results: list[dict]) -> str:
    """Format search results for display.

    Args:
        results: List of task dictionaries

    Returns:
        Formatted string
    """
    if not results:
        return "No tasks found."

    lines = [f"Found {len(results)} task(s):\n"]

    for i, task in enumerate(results, 1):
        title = task.get("title", "Untitled")
        priority = task.get("priority")
        status_val = task.get("status", "unknown")
        project = task.get("project", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   File: {task['_filename']}")

        if priority:
            lines.append(f"   Priority: P{priority}")
        lines.append(f"   Status: {status_val}")

        if project:
            lines.append(f"   Project: {project}")

        # Show first line of body as preview
        body = task.get("_body", "")
        if body:
            preview = body.split("\n")[0][:80]
            if len(body.split("\n")[0]) > 80:
                preview += "..."
            lines.append(f"   Preview: {preview}")

        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Search tasks using text matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--priority", type=int, choices=[1, 2, 3], help="Filter by priority"
    )
    parser.add_argument(
        "--status", choices=["inbox", "queue", "archived"], help="Filter by status"
    )
    parser.add_argument("--type", dest="task_type", help="Filter by task type")
    parser.add_argument("--project", help="Filter by project")
    parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)"
    )

    args = parser.parse_args()

    # Search tasks
    results = search_tasks(
        query=args.query,
        priority=args.priority,
        status=args.status,
        task_type=args.task_type,
        project=args.project,
        limit=args.limit,
    )

    # Format and print results
    output = format_results(results)
    print(output)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
