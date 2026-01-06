#!/usr/bin/env python3
"""Regenerate task index from task files.

Scans ALL markdown files in $ACA_DATA with `type: task` in frontmatter.
Builds $ACA_DATA/tasks/index.json and INDEX.md (organized by project).
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


def find_task_files(data_dir: Path) -> list[Path]:
    """Find all markdown files with type: task in frontmatter.

    Scans entire $ACA_DATA recursively, filtering by frontmatter.
    Excludes INDEX.md and known non-task files.
    """
    task_files = []
    excluded_names = {"INDEX.md", "tasks.md", "index.md"}

    for md_file in data_dir.rglob("*.md"):
        # Skip excluded files
        if md_file.name in excluded_names:
            continue

        # Skip session transcripts (contain quoted task frontmatter)
        if "/sessions/" in str(md_file):
            continue

        # Check frontmatter for type: task
        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter = parse_frontmatter(content)
            if frontmatter and frontmatter.get("type") == "task":
                task_files.append(md_file)
        except Exception:
            # Skip files we can't read
            pass

    return task_files


def parse_task_file(file_path: Path, data_dir: Path) -> dict | None:
    """Parse a task file into index entry.

    Args:
        file_path: Path to the task markdown file.
        data_dir: Root data directory ($ACA_DATA) for computing relative paths.
    """
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

    # Build relative path from $ACA_DATA
    try:
        relative_path = str(file_path.relative_to(data_dir))
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


def format_task_line(task: dict) -> str:
    """Format a single task line with indicators.

    Format: - [[file|title]] (P0, due: 2025-01-15, status, [3/5])
    """
    # Base link
    line = f"- [[{task['file']}|{task['title']}]]"

    # Build indicators
    indicators = []

    # Priority
    if task.get("priority") is not None:
        indicators.append(f"P{task['priority']}")

    # Due date
    if task.get("due"):
        due_str = task["due"]
        if isinstance(due_str, str) and "T" in due_str:
            due_str = due_str.split("T")[0]
        indicators.append(f"due: {due_str}")

    # Status indicator
    status = task.get("status", "inbox")
    status_icons = {
        "active": "* active",
        "inbox": "inbox",
        "waiting": "~ waiting",
        "archived": "/ archived",
    }
    indicators.append(status_icons.get(status, status))

    # Subtask progress
    if task.get("subtasks_total", 0) > 0:
        indicators.append(f"[{task['subtasks_done']}/{task['subtasks_total']}]")

    if indicators:
        line += f" ({', '.join(indicators)})"

    return line


def generate_index_md(index: dict, output_path: Path) -> None:
    """Generate human-readable INDEX.md organized by project."""
    lines = [
        "---",
        "title: Task Index",
        "type: index",
        f"generated: {index['generated']}",
        "permalink: tasks/index",
        "---",
        "",
        "# Task Index",
        "",
        f"*Auto-generated from task files. {index['total_tasks']} tasks.*",
        "",
    ]

    # Group by project
    by_project: dict[str, list[dict]] = {}
    for task in index["tasks"]:
        project = task.get("project") or "uncategorized"
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(task)

    # Sort projects alphabetically (uncategorized last)
    project_order = sorted(
        by_project.keys(),
        key=lambda p: (p == "uncategorized", p.lower()),
    )

    for project in project_order:
        tasks = by_project[project]
        lines.append(f"## {project} ({len(tasks)})")
        lines.append("")

        # Sort by priority then due date then title
        tasks.sort(
            key=lambda t: (
                t.get("priority") or 999,
                t.get("due") or "9999-99-99",
                t.get("title", ""),
            )
        )

        for task in tasks:
            lines.append(format_task_line(task))

        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Main entry point."""
    data_dir = get_data_dir()
    tasks_dir = data_dir / "tasks"

    # Ensure output directory exists
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Find all task files across $ACA_DATA (files with type: task)
    task_files = find_task_files(data_dir)

    print(f"Found {len(task_files)} task files with type: task")

    # Parse all tasks
    tasks: list[dict] = []
    errors = 0

    for file_path in task_files:
        task = parse_task_file(file_path, data_dir)
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
