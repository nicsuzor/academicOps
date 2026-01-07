#!/usr/bin/env python3
"""
Task data preparation for LLM-driven selection.

Outputs ALL active tasks with metadata. Agent reasons about selection.
No algorithmic scoring or keyword matching (H12a compliance).
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Resolve paths
ACA_DATA = Path.home() / "writing" / "data"
TASK_INDEX = ACA_DATA / "tasks" / "index.json"
SYNTHESIS = ACA_DATA / "dashboard" / "synthesis.json"


def load_json(path: Path) -> dict:
    """Load JSON file. Fail fast if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text())


def parse_due_date(due_str: str | None) -> datetime | None:
    """Parse various due date formats."""
    if not due_str:
        return None

    try:
        return datetime.fromisoformat(due_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    try:
        return datetime.strptime(due_str.split("T")[0], "%Y-%m-%d")
    except (ValueError, AttributeError):
        pass

    return None


def get_active_tasks(index: dict) -> list[dict]:
    """Filter to non-archived tasks."""
    tasks = index.get("tasks", [])
    active = []
    for t in tasks:
        status = t.get("status", "")
        file_path = t.get("file", "")
        if status in ("archived", "done"):
            continue
        if "/archived/" in file_path or file_path.startswith("tasks/archived/"):
            continue
        active.append(t)
    return active


def get_todays_work(synthesis: dict) -> Counter:
    """Count accomplishments by project from synthesis.json."""
    items = synthesis.get("accomplishments", {}).get("items", [])
    return Counter(item.get("project", "unknown") for item in items)


def get_next_subtasks(task_file: str, limit: int = 3) -> list[str]:
    """Extract next unchecked subtasks from task file."""
    file_path = ACA_DATA / task_file
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text()
        unchecked = re.findall(r"^- \[ \] (.+)$", content, re.MULTILINE)
        return unchecked[:limit]
    except Exception:
        return []


def detect_stale_tasks(tasks: list[dict], now: datetime) -> list[dict]:
    """
    Find tasks that are probably stale and should be archived.
    Uses deterministic date-based rules only.
    """
    stale = []

    for task in tasks:
        tags = task.get("tags", [])
        due = parse_due_date(task.get("due"))
        classification = task.get("classification", "").lower()

        reason = None

        if due:
            days_overdue = (now.date() - due.date()).days

            # Events more than 7 days past
            event_indicators = ["event", "decision"]
            is_event = classification in event_indicators or "event" in tags
            if is_event and days_overdue > 7:
                reason = f"Past event ({days_overdue} days ago)"

            # Non-events overdue 60+ days
            elif days_overdue > 60:
                reason = f"Overdue {days_overdue} days - likely stale"

        if reason:
            stale.append(
                {
                    "slug": task.get("slug", ""),
                    "title": task.get("title", ""),
                    "reason": reason,
                    "file": task.get("file", ""),
                }
            )

    return stale[:5]


def calculate_priority_distribution(tasks: list[dict]) -> dict[str, int]:
    """Count tasks by priority level."""
    counts: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for t in tasks:
        priority = t.get("priority", 3)
        key = f"P{priority}"
        if key in counts:
            counts[key] += 1
        else:
            counts["P3"] += 1
    return counts


def enrich_task(task: dict) -> dict:
    """Add computed fields to task for LLM consumption."""
    enriched = task.copy()

    # Parse and normalize due date
    due = parse_due_date(task.get("due"))
    if due:
        enriched["due_parsed"] = due.strftime("%Y-%m-%d")
        days_until = (due.date() - datetime.now().date()).days
        enriched["days_until_due"] = days_until
    else:
        enriched["due_parsed"] = None
        enriched["days_until_due"] = None

    # Extract next subtasks
    enriched["next_subtasks"] = get_next_subtasks(task.get("file", ""))

    return enriched


def main():
    # Load data - fail fast if missing
    try:
        index = load_json(TASK_INDEX)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    # Synthesis is optional - empty if missing
    try:
        synthesis = load_json(SYNTHESIS)
    except FileNotFoundError:
        synthesis = {}

    now = datetime.now()

    # Get active tasks
    tasks = get_active_tasks(index)
    todays_work = get_todays_work(synthesis)

    # Detect stale tasks (separate from main pool)
    stale_candidates = detect_stale_tasks(tasks, now)
    stale_slugs = {s["slug"] for s in stale_candidates}

    # Enrich non-stale tasks with computed fields
    fresh_tasks = [enrich_task(t) for t in tasks if t.get("slug") not in stale_slugs]

    # Sort by priority (P0 first), then by due date (soonest first)
    def sort_key(t: dict) -> tuple:
        priority = t.get("priority")
        # Default to P3 if no priority set
        priority = priority if priority is not None else 3
        days = t.get("days_until_due")
        # None means no due date - sort to end
        due_sort = days if days is not None else 9999
        return (priority, due_sort)

    fresh_tasks.sort(key=sort_key)

    # Output everything for LLM reasoning
    output = {
        "generated": now.isoformat(),
        "active_task_count": len(fresh_tasks),
        "todays_work": dict(todays_work),
        "priority_distribution": calculate_priority_distribution(fresh_tasks),
        "stale_candidates": stale_candidates,
        "active_tasks": fresh_tasks,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
