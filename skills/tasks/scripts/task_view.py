#!/usr/bin/env python3
"""Pretty task viewer: paginated, color, minimal fields.

Usage:
    uv run python skills/tasks/scripts/task_view.py [page] [--sort=priority|date|due] [--per-page=N] [--compact]

Defaults:
    page=1, sort=priority (ascending int), per-page=10 (or 20 in compact mode)
    --sort=date uses created desc
    --sort=due uses due asc (None last)
    --compact: One-line-per-task view for quick triage
"""

from __future__ import annotations

import contextlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from lib.paths import get_tasks_dir
from skills.tasks import task_ops

# -------- args --------
page = 1
sort = "priority"
per_page = None  # Will set default based on compact mode
compact = False
data_dir_override = None

for arg in sys.argv[1:]:
    if arg.startswith("--sort="):
        sort = arg.split("=", 1)[1].strip()
    elif arg.startswith("--per-page="):
        with contextlib.suppress(Exception):
            per_page = max(1, int(arg.split("=", 1)[1]))
    elif arg.startswith("--data-dir="):
        data_dir_override = arg.split("=", 1)[1].strip()
    elif arg == "--compact":
        compact = True
    else:
        with contextlib.suppress(Exception):
            page = max(1, int(arg))

# Base data directory: --data-dir flag or $ACA_DATA/tasks
if data_dir_override:
    DATA_DIR = Path(data_dir_override)
else:
    DATA_DIR = get_tasks_dir()

print(f"Using data_dir: {DATA_DIR}")

# Set default per_page based on mode
if per_page is None:
    per_page = 20 if compact else 10


# -------- load tasks using shared library --------
def task_to_dict(task):
    """Convert Task model to dict for display and JSON serialization."""
    return {
        "title": task.title,
        "priority": task.priority,
        "type": task.type,
        "project": task.project,
        "classification": task.classification,
        "created": task.created.isoformat() if task.created else None,
        "due": task.due.isoformat() if task.due else None,
        "status": task.status,
        "archived_at": task.archived_at.isoformat() if task.archived_at else None,
        "tags": task.tags,
        "_filename": task.filename,
        "_body": task.body or "",
    }


tasks = task_ops.load_tasks(DATA_DIR / "inbox")
tasks_list = [task_to_dict(t) for t in tasks]

# -------- sort logic --------
if sort == "priority":
    # ascending numeric
    tasks_list.sort(key=lambda t: (t["priority"] or 999, t["created"] or ""))
elif sort == "date":
    # descending date
    tasks_list.sort(key=lambda t: t["created"] or "", reverse=True)
elif sort == "due":
    # ascending due, None last
    tasks_list.sort(
        key=lambda t: (
            t["due"] is None,
            t["due"] or "",
            t["priority"] or 999,
        )
    )

# -------- pagination --------
total = len(tasks_list)
total_pages = (total + per_page - 1) // per_page if total > 0 else 1
page = max(1, min(page, total_pages))
start_idx = (page - 1) * per_page
end_idx = start_idx + per_page
page_tasks = tasks_list[start_idx:end_idx]

# -------- colors --------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"
BLUE = "\033[34m"

P_COLORS = {
    0: f"{BOLD}{RED}P0{RESET}",
    1: f"{BOLD}{YELLOW}P1{RESET}",
    2: f"{CYAN}P2{RESET}",
    3: f"{DIM}P3{RESET}",
}

# -------- terminal width --------
term_width, _ = shutil.get_terminal_size((80, 24))

# -------- compact mode --------
if compact:
    print(f"\n{BOLD}Tasks (page {page}/{total_pages}, {total} total){RESET}\n")
    for t in page_tasks:
        p = t["priority"]
        p_str = P_COLORS.get(p, f"P{p}" if p is not None else "P?")
        title_str = t["title"]
        proj_str = f" [{t['project']}]" if t["project"] else ""
        # Truncate to fit terminal
        max_len = term_width - 10
        if len(title_str + proj_str) > max_len:
            overflow = len(title_str + proj_str) - max_len + 3
            title_str = title_str[: len(title_str) - overflow] + "..."
        print(f"{p_str}  {title_str}{DIM}{proj_str}{RESET}")
    print(f"\n{DIM}Sort: {sort} | Per page: {per_page}{RESET}\n")
    sys.exit(0)

# -------- pretty mode --------
print(f"\n{BOLD}Tasks (page {page}/{total_pages}, {total} total){RESET}\n")
for i, t in enumerate(page_tasks, start=start_idx + 1):
    p = t["priority"]
    p_str = P_COLORS.get(p, f"P{p}" if p is not None else "P?")
    print(f"{BOLD}#{i}{RESET} {p_str}  {BOLD}{t['title']}{RESET}")

    # Project
    if t["project"]:
        print(f"  {DIM}Project:{RESET} {t['project']}")

    # Classification
    if t["classification"]:
        print(f"  {DIM}Type:{RESET} {t['classification']}")

    # Created
    if t["created"]:
        created_dt = datetime.fromisoformat(t["created"])
        created_str = created_dt.strftime("%Y-%m-%d %H:%M")
        print(f"  {DIM}Created:{RESET} {created_str}")

    # Due
    if t["due"]:
        due_dt = datetime.fromisoformat(t["due"])
        due_str = due_dt.strftime("%Y-%m-%d")
        now = datetime.now(UTC)
        is_overdue = due_dt.replace(tzinfo=UTC) < now
        color = RED if is_overdue else YELLOW
        print(f"  {DIM}Due:{RESET} {color}{due_str}{RESET}")

    # Body preview (first line)
    if t["_body"]:
        preview = t["_body"].split("\n")[0][:80]
        print(f"  {DIM}{preview}{RESET}")

    # Tags
    if t["tags"]:
        tags_str = " ".join(f"#{tag}" for tag in t["tags"])
        print(f"  {BLUE}{tags_str}{RESET}")

    print()

print(f"{DIM}Sort: {sort} | Per page: {per_page}{RESET}\n")
