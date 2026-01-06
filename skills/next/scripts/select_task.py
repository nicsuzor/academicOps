#!/usr/bin/env python3
"""
Task selector for ADHD-friendly recommendations.

Returns 3 task options:
1. SHOULD - deadline pressure (overdue > today > this week > P0)
2. ENJOY - variety from recent work (different project, substantive)
3. QUICK - momentum builder (<15 min, actionable)
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# Resolve paths
ACA_DATA = Path.home() / "writing" / "data"
TASK_INDEX = ACA_DATA / "tasks" / "index.json"
DAILY_DIR = ACA_DATA / "sessions"
SYNTHESIS = ACA_DATA / "dashboard" / "synthesis.json"


def load_json(path: Path) -> dict:
    """Load JSON file or return empty dict."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def get_today_str() -> str:
    """Get today's date as YYYYMMDD."""
    return datetime.now().strftime("%Y%m%d")


def parse_due_date(due_str: str | None) -> datetime | None:
    """Parse various due date formats."""
    if not due_str:
        return None

    # Try ISO format first
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
    ]:
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
        # Check both status field and file path
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


def score_deadline(task: dict, now: datetime) -> tuple[int, str]:
    """
    Score task by deadline urgency.
    Returns (score, reason) where higher score = more urgent.
    """
    due = parse_due_date(task.get("due"))
    priority = task.get("priority", 3)

    if due:
        days_until = (due.date() - now.date()).days
        if days_until < 0:
            return (100 - days_until, f"OVERDUE by {-days_until} days")
        elif days_until == 0:
            return (90, "Due TODAY")
        elif days_until == 1:
            return (80, "Due tomorrow")
        elif days_until <= 7:
            return (70, f"Due in {days_until} days")
        else:
            return (50, f"Due {due.strftime('%b %d')}")

    # No due date - use priority
    priority_scores = {0: 60, 1: 40, 2: 20, 3: 10}
    return (priority_scores.get(priority, 10), f"P{priority} priority")


def is_quick_win(task: dict) -> bool:
    """Detect quick-win tasks."""
    title = task.get("title", "").lower()
    quick_keywords = ["respond", "reply", "approve", "confirm", "send", "check", "review"]

    # Title heuristics
    if any(kw in title for kw in quick_keywords):
        return True

    # Subtask heuristics - mostly done or no subtasks
    total = task.get("subtasks_total", 0)
    done = task.get("subtasks_done", 0)
    if total == 0 or (total > 0 and total - done <= 1):
        return True

    return False


def is_deep_work(task: dict) -> bool:
    """Detect substantive/creative tasks."""
    title = task.get("title", "").lower()
    tags = task.get("tags", [])

    deep_keywords = ["write", "paper", "research", "review", "design", "implement", "create"]
    deep_tags = ["paper", "writing", "research", "thesis", "phd"]

    if any(kw in title for kw in deep_keywords):
        return True
    if any(t in deep_tags for t in tags):
        return True

    return False


def select_should(tasks: list[dict], now: datetime) -> dict | None:
    """Select most urgent task by deadline."""
    scored = [(score_deadline(t, now), t) for t in tasks]
    scored.sort(key=lambda x: x[0][0], reverse=True)

    if scored:
        (score, reason), task = scored[0]
        return {
            "task": task,
            "reason": reason,
            "category": "should"
        }
    return None


def normalize_project(name: str) -> str:
    """Normalize project names for comparison."""
    aliases = {
        "academicops": "aops",
        "academicOps": "aops",
        "writing": "writing",
    }
    return aliases.get(name, name.lower() if name else "")


def select_enjoy(tasks: list[dict], todays_work: Counter) -> dict | None:
    """Select task from underrepresented project, preferring deep work."""
    if not tasks:
        return None

    # Normalize today's work projects
    normalized_work = Counter()
    for proj, count in todays_work.items():
        normalized_work[normalize_project(proj)] += count

    # Find dominant project today
    if normalized_work:
        dominant = normalized_work.most_common(1)[0][0]
        dominant_count = normalized_work[dominant]
    else:
        dominant = None
        dominant_count = 0

    # Filter to different projects if we've done 3+ in one project
    candidates = tasks
    if dominant_count >= 3:
        other_project = [t for t in tasks if normalize_project(t.get("project", "")) != dominant]
        if other_project:
            candidates = other_project

    # Prefer deep work
    deep = [t for t in candidates if is_deep_work(t)]
    if deep:
        candidates = deep

    # Pick one with no immediate deadline
    now = datetime.now()
    relaxed = [t for t in candidates if not parse_due_date(t.get("due")) or
               (parse_due_date(t.get("due")).date() - now.date()).days > 7]

    if relaxed:
        task = relaxed[0]
    elif candidates:
        task = candidates[0]
    else:
        return None

    reason = "Different domain from recent work"
    if dominant_count >= 3:
        reason = f"Counterweight to {dominant_count}+ {dominant} items today"
    if is_deep_work(task):
        reason += ", substantive work"

    return {
        "task": task,
        "reason": reason,
        "category": "enjoy"
    }


def select_quick(tasks: list[dict]) -> dict | None:
    """Select quick-win task."""
    quick = [t for t in tasks if is_quick_win(t)]

    if quick:
        task = quick[0]
        return {
            "task": task,
            "reason": "Clear the deck, build momentum",
            "category": "quick"
        }
    return None


def get_next_subtasks(task_file: str, limit: int = 3) -> list[str]:
    """Extract next unchecked subtasks from task file."""
    file_path = ACA_DATA / task_file.replace("tasks/", "tasks/")
    if not file_path.exists():
        return []

    content = file_path.read_text()
    # Find unchecked items: - [ ] text
    unchecked = re.findall(r'^- \[ \] (.+)$', content, re.MULTILINE)
    return unchecked[:limit]


def format_recommendation(rec: dict) -> dict:
    """Format recommendation for output."""
    task = rec["task"]
    due = parse_due_date(task.get("due"))

    result = {
        "category": rec["category"],
        "title": task.get("title", "Untitled"),
        "reason": rec["reason"],
        "project": task.get("project", "uncategorized"),
        "due": due.strftime("%Y-%m-%d") if due else None,
        "slug": task.get("slug", ""),
        "file": task.get("file", "")
    }

    # Include next subtasks for any task with multiple steps
    subtasks = get_next_subtasks(task.get("file", ""))
    if subtasks:
        result["next_subtasks"] = subtasks

    return result


def detect_stale_tasks(tasks: list[dict], now: datetime) -> list[dict]:
    """Find tasks that are probably stale and should be archived."""
    stale = []

    for task in tasks:
        title = task.get("title", "").lower()
        tags = task.get("tags", [])
        due = parse_due_date(task.get("due"))
        classification = task.get("classification", "").lower()

        reason = None

        # Past events (due date passed + looks like an event)
        if due:
            days_overdue = (now.date() - due.date()).days

            # Events more than 7 days past
            event_keywords = ["attend", "event", "meeting", "conference", "seminar", "workshop", "rsvp"]
            is_event = (
                classification in ("event", "decision") or
                "event" in tags or
                any(kw in title for kw in event_keywords)
            )
            if is_event and days_overdue > 7:
                reason = f"Past event ({days_overdue} days ago)"

            # Non-events overdue 60+ days with no recent activity
            elif days_overdue > 60:
                reason = f"Overdue {days_overdue} days - likely stale"

        if reason:
            stale.append({
                "slug": task.get("slug", ""),
                "title": task.get("title", ""),
                "reason": reason,
                "file": task.get("file", "")
            })

    return stale[:5]  # Limit to 5 suggestions


def main():
    # Load data
    index = load_json(TASK_INDEX)
    synthesis = load_json(SYNTHESIS)

    if not index:
        print(json.dumps({"error": "No task index found", "path": str(TASK_INDEX)}))
        sys.exit(1)

    # Get active tasks and today's work
    tasks = get_active_tasks(index)
    todays_work = get_todays_work(synthesis)
    now = datetime.now()

    # Build recommendations
    recommendations = []
    used_slugs = set()

    # 1. SHOULD - deadline pressure
    should = select_should(tasks, now)
    if should:
        recommendations.append(format_recommendation(should))
        used_slugs.add(should["task"].get("slug"))

    # 2. ENJOY - variety (exclude already recommended)
    remaining = [t for t in tasks if t.get("slug") not in used_slugs]
    enjoy = select_enjoy(remaining, todays_work)
    if enjoy:
        recommendations.append(format_recommendation(enjoy))
        used_slugs.add(enjoy["task"].get("slug"))

    # 3. QUICK - momentum (exclude already recommended)
    remaining = [t for t in tasks if t.get("slug") not in used_slugs]
    quick = select_quick(remaining)
    if quick:
        recommendations.append(format_recommendation(quick))

    # Detect stale tasks
    stale_candidates = detect_stale_tasks(tasks, now)

    # Output
    output = {
        "generated": datetime.now().isoformat(),
        "todays_work": dict(todays_work),
        "active_tasks": len(tasks),
        "recommendations": recommendations,
        "stale_candidates": stale_candidates
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
