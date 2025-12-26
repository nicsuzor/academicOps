#!/usr/bin/env python3
"""Regenerate task index from task files.

Builds $ACA_DATA/tasks/index.json from all task markdown files.
Designed to run via cron every 5 minutes.

Usage:
    uv run python scripts/regenerate_task_index.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml


def get_data_dir() -> Path:
    """Get data directory from ACA_DATA env var."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("ERROR: ACA_DATA environment variable not set", file=sys.stderr)
        sys.exit(1)

    path = Path(aca_data)
    if not path.exists():
        print(f"ERROR: ACA_DATA path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    return path


def parse_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def count_subtasks(content: str) -> tuple[int, int]:
    """Count completed and total subtasks from markdown checkboxes.

    Returns:
        (completed, total) tuple
    """
    # Match markdown checkboxes: - [ ] or - [x] or - [X]
    completed = len(re.findall(r"^\s*-\s*\[x\]", content, re.MULTILINE | re.IGNORECASE))
    incomplete = len(re.findall(r"^\s*-\s*\[\s*\]", content, re.MULTILINE))
    return completed, completed + incomplete


def get_task_status_folder(file_path: Path) -> str:
    """Determine task status from folder location."""
    parent = file_path.parent.name
    if parent == "archived":
        return "archived"
    elif parent == "waiting":
        return "waiting"
    elif parent == "inbox":
        return "inbox"
    elif parent == "active":
        return "active"
    else:
        return "inbox"  # Default


def parse_task_file(file_path: Path) -> dict | None:
    """Parse a task file into index entry."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"WARNING: Could not read {file_path}: {e}", file=sys.stderr)
        return None

    frontmatter = parse_frontmatter(content)
    if not frontmatter:
        print(f"WARNING: No valid frontmatter in {file_path}", file=sys.stderr)
        return None

    # Required field
    title = frontmatter.get("title")
    if not title:
        print(f"WARNING: No title in {file_path}", file=sys.stderr)
        return None

    # Parse priority (P0, P1, etc. or integer)
    priority_raw = frontmatter.get("priority")
    priority = None
    if priority_raw is not None:
        if isinstance(priority_raw, int):
            priority = priority_raw
        elif isinstance(priority_raw, str) and priority_raw.upper().startswith("P"):
            try:
                priority = int(priority_raw[1:])
            except ValueError:
                pass

    # Count subtasks
    subtasks_done, subtasks_total = count_subtasks(content)

    # Get file modification time as last_activity
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
        last_activity = mtime.strftime("%Y-%m-%d")
    except Exception:
        last_activity = None

    # Build relative path from tasks/
    data_dir = get_data_dir()
    tasks_dir = data_dir / "tasks"
    try:
        relative_path = str(file_path.relative_to(tasks_dir))
    except ValueError:
        relative_path = file_path.name

    # Parse due date
    due = frontmatter.get("due")
    if due and isinstance(due, datetime):
        due = due.strftime("%Y-%m-%d")
    elif due and not isinstance(due, str):
        due = str(due)

    return {
        "slug": file_path.stem,
        "title": title,
        "status": frontmatter.get("status", get_task_status_folder(file_path)),
        "priority": priority,
        "project": frontmatter.get("project", "uncategorized"),
        "due": due,
        "source": frontmatter.get("source", "manual"),
        "subtasks_total": subtasks_total,
        "subtasks_done": subtasks_done,
        "last_activity": last_activity,
        "file": relative_path,
    }


def categorize_by_due(tasks: list[dict]) -> dict[str, list[str]]:
    """Categorize tasks by due date."""
    today = datetime.now(UTC).date()

    categories: dict[str, list[str]] = {
        "overdue": [],
        "today": [],
        "this_week": [],
        "next_week": [],
        "later": [],
        "no_date": [],
    }

    for task in tasks:
        slug = task["slug"]
        due = task.get("due")

        if not due:
            categories["no_date"].append(slug)
            continue

        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            categories["no_date"].append(slug)
            continue

        delta = (due_date - today).days

        if delta < 0:
            categories["overdue"].append(slug)
        elif delta == 0:
            categories["today"].append(slug)
        elif delta <= 7:
            categories["this_week"].append(slug)
        elif delta <= 14:
            categories["next_week"].append(slug)
        else:
            categories["later"].append(slug)

    return categories


def categorize_by_project(tasks: list[dict]) -> dict[str, list[str]]:
    """Categorize tasks by project."""
    by_project: dict[str, list[str]] = {}

    for task in tasks:
        project = task.get("project") or "uncategorized"
        slug = task["slug"]

        if project not in by_project:
            by_project[project] = []
        by_project[project].append(slug)

    return by_project


def generate_index_md(index: dict, output_path: Path) -> None:
    """Generate human-readable INDEX.md from JSON index."""
    lines = [
        "---",
        "title: Task Index",
        "type: index",
        f"generated: {index['generated']}",
        "---",
        "",
        "# Task Index",
        "",
        f"*Auto-generated from task files. {index['total_tasks']} tasks.*",
        "",
    ]

    # Group by status
    by_status: dict[str, list[dict]] = {}
    for task in index["tasks"]:
        status = task.get("status", "inbox")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(task)

    status_order = ["active", "inbox", "waiting", "archived"]
    for status in status_order:
        tasks = by_status.get(status, [])
        if not tasks:
            continue

        lines.append(f"## {status.title()} ({len(tasks)})")
        lines.append("")

        # Sort by priority then title
        tasks.sort(key=lambda t: (t.get("priority") or 999, t.get("title", "")))

        for task in tasks:
            priority = f"P{task['priority']}" if task.get("priority") is not None else ""
            progress = ""
            if task.get("subtasks_total", 0) > 0:
                progress = f" [{task['subtasks_done']}/{task['subtasks_total']}]"

            line = f"- [[{task['file']}|{task['title']}]]"
            if priority:
                line += f" ({priority})"
            if progress:
                line += progress
            if task.get("project") and task["project"] != "uncategorized":
                line += f" #{task['project']}"

            lines.append(line)

        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Main entry point."""
    data_dir = get_data_dir()
    tasks_dir = data_dir / "tasks"

    if not tasks_dir.exists():
        print(f"ERROR: Tasks directory not found: {tasks_dir}", file=sys.stderr)
        sys.exit(1)

    # Find all task files (exclude INDEX.md, tasks.md)
    task_files = [
        f for f in tasks_dir.rglob("*.md")
        if f.name not in ("INDEX.md", "tasks.md")
    ]

    print(f"Found {len(task_files)} task files")

    # Parse all tasks
    tasks: list[dict] = []
    errors = 0

    for file_path in task_files:
        task = parse_task_file(file_path)
        if task:
            tasks.append(task)
        else:
            errors += 1

    print(f"Parsed {len(tasks)} tasks ({errors} errors)")

    # Sort tasks by priority, then by title
    tasks.sort(key=lambda t: (t.get("priority") or 999, t.get("title", "")))

    # Build index
    index = {
        "generated": datetime.now(UTC).isoformat(),
        "total_tasks": len(tasks),
        "tasks": tasks,
        "priority_by_project": categorize_by_project(tasks),
        "priority_by_due": categorize_by_due(tasks),
    }

    # Write JSON index
    index_json_path = tasks_dir / "index.json"
    with open(index_json_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"Wrote {index_json_path}")

    # Write INDEX.md
    index_md_path = tasks_dir / "INDEX.md"
    generate_index_md(index, index_md_path)
    print(f"Wrote {index_md_path}")

    # Summary
    active = len([t for t in tasks if t.get("status") == "active"])
    inbox = len([t for t in tasks if t.get("status") == "inbox"])
    waiting = len([t for t in tasks if t.get("status") == "waiting"])

    print(f"\nSummary: {active} active, {inbox} inbox, {waiting} waiting")


if __name__ == "__main__":
    main()
