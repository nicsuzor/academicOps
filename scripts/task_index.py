#!/usr/bin/env python3
"""Compact task index generator for background context.

Produces a minimal, LLM-friendly index of all active tasks suitable for
inclusion in agent context without overwhelming token budgets.

Usage:
    python3 scripts/task_index.py [--format=text|json]

Output format (text):
    P1  20251007-b5a73631  [Due: 2025-10-11] Read Rhyle's thesis abstract before Friday meeting
    P1  20250817-c515931e  Email: Re: Truth book and AI slop paper
    P2  20251007-82470850  [Due: 2025-10-12] Respond to Bond Law Review manuscript invitation
    ...

Output format (json):
    [
      {"id": "...", "priority": 1, "title": "...", "project": "...", "due": "..."},
      ...
    ]

The index includes:
- Task ID (filename without .json) - for archiving operations
- Priority - for understanding urgency
- Due date (if set) - for time-sensitive matching
- Title - for accomplishment matching
- Project (if set) - for context

Sorted by priority (ascending), then due date (ascending).
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Base data directory (relative to this script): ../../data
ROOT = Path(__file__).resolve().parents[2]  # parent repo root
DATA_DIR = ROOT / "data"

# Parse arguments
output_format = "text"
for arg in sys.argv[1:]:
    if arg.startswith("--format="):
        fmt = arg.split("=", 1)[1].strip().lower()
        if fmt in ("text", "json"):
            output_format = fmt


def load_task(path: Path):
    """Load a task file and extract minimal index fields."""
    try:
        with path.open() as f:
            t = json.load(f)
            # Skip archived tasks
            if t.get('archived_at'):
                return None

            # Extract filename without extension for ID
            task_id = path.stem

            return {
                "id": task_id,
                "priority": t.get("priority"),
                "title": t.get("title", ""),
                "project": t.get("project", ""),
                "due": t.get("due"),
            }
    except Exception:
        return None


def parse_iso(ts: str):
    """Parse ISO timestamp."""
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        s = str(ts)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def sort_key(task):
    """Sort by priority (asc), then due date (asc), then created (asc)."""
    p = task.get("priority")
    if not isinstance(p, int):
        p = 9999

    # Due date sorting: None goes last
    d = parse_iso(task.get("due"))
    if d is None:
        d = datetime.max.replace(tzinfo=timezone.utc)

    return (p, d)


def load_all_tasks():
    """Load all active tasks from inbox and queue."""
    inbox = DATA_DIR / 'tasks/inbox'
    queue = DATA_DIR / 'tasks/queue'
    archived = DATA_DIR / 'tasks/archived'

    cand_paths = []
    if inbox.exists():
        cand_paths.extend(inbox.glob('*.json'))
    if queue.exists():
        cand_paths.extend(queue.glob('*.json'))

    tasks = []
    for p in cand_paths:
        # Skip archived folder for safety
        if archived.exists() and p.parent.resolve() == archived.resolve():
            continue

        t = load_task(p)
        if t:
            tasks.append(t)

    # Sort by priority, then due date
    tasks.sort(key=sort_key)
    return tasks


def format_text(tasks):
    """Format tasks as compact text lines."""
    lines = []
    for t in tasks:
        # Priority
        p = t.get("priority")
        p_str = f"P{p}" if isinstance(p, int) else "P–"

        # Task ID
        task_id = t.get("id", "")

        # Due date (optional)
        due = t.get("due")
        due_str = ""
        if due:
            due_dt = parse_iso(due)
            if due_dt:
                due_str = f" [Due: {due_dt.strftime('%Y-%m-%d')}]"

        # Project (optional prefix)
        project = t.get("project", "")
        proj_str = f"[{project}] " if project else ""

        # Title
        title = t.get("title", "").replace("\n", " ").strip()

        # Format: P1  task-id  [Due: date] [project] Title
        line = f"{p_str:3s}  {task_id:30s} {due_str:18s} {proj_str}{title}"
        lines.append(line)

    return "\n".join(lines)


def format_json(tasks):
    """Format tasks as JSON array."""
    return json.dumps(tasks, indent=2, default=str)


# Main execution
tasks = load_all_tasks()

if output_format == "json":
    print(format_json(tasks))
else:
    print(format_text(tasks))
