#!/usr/bin/env python3
"""Batch task processor with atomic locking for parallel execution.

This script processes items from a queue file with atomic locking to prevent
duplicate processing when multiple workers run in parallel.

Usage:
    # Create queue and directories
    find /path/to/files -name "*.md" > /tmp/batch/queue.txt
    mkdir -p /tmp/batch/locks /tmp/batch/results

    # Run workers (can run multiple in parallel)
    python batch_worker.py --batch 100
    python batch_worker.py --stats  # Check progress

The atomic locking pattern uses mkdir which is atomic on POSIX systems.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


# Configurable paths - override via environment or edit here
BATCH_DIR = Path("/tmp/task-batch")
QUEUE_FILE = BATCH_DIR / "queue.txt"
LOCKS_DIR = BATCH_DIR / "locks"
RESULTS_DIR = BATCH_DIR / "results"

# Project wikilink mappings for task triage
PROJECT_WIKILINKS = {
    "aops": "[[academicOps]]",
    "framework": "[[academicOps]]",
    "osb": "[[oversight-board]]",
    "academic": "[[academic-work]]",
    "hdr": "[[hdr-supervision]]",
    "buttermilk": "[[buttermilk]]",
    "mediamarkets": "[[media-markets]]",
    "reco": "[[reco-project]]",
}


def claim_item(item_id: str) -> bool:
    """Atomically claim an item using mkdir (atomic on POSIX).

    Returns True if claimed successfully, False if already claimed.
    """
    lock_dir = LOCKS_DIR / item_id
    try:
        lock_dir.mkdir(exist_ok=False)
        return True
    except FileExistsError:
        return False


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2].lstrip("\n")
        return fm, body
    except yaml.YAMLError:
        return {}, content


def serialize_frontmatter(fm: dict[str, Any], body: str) -> str:
    """Serialize frontmatter and body back to markdown."""
    fm_str = yaml.dump(
        fm, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    return f"---\n{fm_str}---\n{body}"


def is_closeable(body: str, fm: dict[str, Any]) -> tuple[bool, str]:
    """Check if task can be closed."""
    if "## Close Reason" in body or "## Closed" in body:
        return True, "has_close_reason"

    if fm.get("status") == "done":
        return True, "status_done"

    if fm.get("close_reason"):
        return True, "has_close_reason_field"

    return False, ""


def determine_assignee(body: str, fm: dict[str, Any], title: str) -> str:
    """Determine if task should go to nic or bot."""
    title_lower = title.lower()
    body_lower = body.lower()
    tags = fm.get("tags", []) or []

    if fm.get("assignee"):
        return fm["assignee"]

    # Nic-required patterns (judgment, human interaction) - check first
    nic_patterns = [
        r"\breview\b",
        r"\brespond\b.*\b(email|to)\b",
        r"\bmeeting\b",
        r"\bdecision\b",
        r"\bdesign\b.*\b(decision|choice)\b",
        r"\bapprove\b",
        r"\bfinance\b",
        r"\breceipt\b",
        r"\bpeer.?review\b",
    ]
    nic_keywords = ["requires human", "underspecified", "needs clarification"]

    combined_text = f"{body_lower} {title_lower}"
    for pattern in nic_patterns:
        if re.search(pattern, combined_text):
            return "nic"
    for keyword in nic_keywords:
        if keyword in body_lower:
            return "nic"

    # Bot-friendly patterns (clear, automatable)
    if "bot-assigned" in tags:
        return "bot"

    bot_patterns = [
        r"\bimplement\b.*\b(function|method|class|script)\b",
        r"\bfix\b.*\b(bug|error|issue)\b",
        r"\btest\b.*\b(coverage|unit|integration)\b",
        r"\brefactor\b",
        r"\bupdate\b.*\b(config|schema|spec)\b",
        r"\badd\b.*\b(field|parameter|option)\b",
    ]
    for pattern in bot_patterns:
        if re.search(pattern, combined_text):
            return "bot"

    # Default: if task has clear structure, assign to bot
    if "## acceptance" in body_lower or "- [ ]" in body:
        return "bot"

    return "nic"


def ensure_wikilink(body: str, fm: dict[str, Any]) -> str:
    """Add project wikilink if missing."""
    project = fm.get("project")
    if not project:
        return body

    wikilink = PROJECT_WIKILINKS.get(project, f"[[{project}]]")

    if wikilink in body or f"[[{project}]]" in body:
        return body

    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(i + 1, f"\nProject: {wikilink}\n")
            return "\n".join(lines)

    return f"Project: {wikilink}\n\n{body}"


def process_task(task_path: str) -> dict[str, Any]:
    """Process a single task file (triage: close, assign, wikilink)."""
    path = Path(task_path)
    result: dict[str, Any] = {
        "path": str(path),
        "task_id": path.stem,
        "processed_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "action": None,
        "changes": [],
    }

    content = path.read_text()
    fm, body = parse_frontmatter(content)
    title = fm.get("title", path.stem)

    closeable, reason = is_closeable(body, fm)
    if closeable:
        result["action"] = "close"
        result["close_reason"] = reason
        if fm.get("status") != "done":
            fm["status"] = "done"
            result["changes"].append("status->done")
    else:
        assignee = determine_assignee(body, fm, title)
        if fm.get("assignee") != assignee:
            fm["assignee"] = assignee
            result["changes"].append(f"assignee->{assignee}")
        result["action"] = f"assign:{assignee}"

    new_body = ensure_wikilink(body, fm)
    if new_body != body:
        body = new_body
        result["changes"].append("added_wikilink")

    if result["changes"]:
        new_content = serialize_frontmatter(fm, body)
        path.write_text(new_content)

    return result


def claim_and_process_batch(batch_size: int = 10) -> list[dict[str, Any]]:
    """Claim and process a batch of items from the queue."""
    results: list[dict[str, Any]] = []

    if not QUEUE_FILE.exists():
        print(f"Queue file not found: {QUEUE_FILE}", file=sys.stderr)
        return results

    items = QUEUE_FILE.read_text().strip().split("\n")

    for item_path in items:
        if not item_path or not Path(item_path).exists():
            continue

        item_id = Path(item_path).stem
        if claim_item(item_id):
            try:
                result = process_task(item_path)
                results.append(result)

                result_file = RESULTS_DIR / f"{result['task_id']}.yaml"
                result_file.write_text(yaml.dump(result, default_flow_style=False))

            except Exception as e:
                results.append(
                    {
                        "path": item_path,
                        "task_id": item_id,
                        "error": str(e),
                    }
                )

        if len(results) >= batch_size:
            break

    return results


def get_stats() -> dict[str, int]:
    """Get processing statistics."""
    locks = list(LOCKS_DIR.glob("*")) if LOCKS_DIR.exists() else []
    results = list(RESULTS_DIR.glob("*.yaml")) if RESULTS_DIR.exists() else []
    queue_size = (
        len(QUEUE_FILE.read_text().strip().split("\n")) if QUEUE_FILE.exists() else 0
    )

    return {
        "queue_total": queue_size,
        "claimed": len(locks),
        "completed": len(results),
        "remaining": queue_size - len(locks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch processor with atomic locking for parallel execution"
    )
    parser.add_argument("--batch", type=int, default=10, help="Batch size to process")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    if args.stats:
        stats = get_stats()
        print(yaml.dump(stats))
    else:
        results = claim_and_process_batch(args.batch)
        for r in results:
            action = r.get("action", "error")
            changes = r.get("changes", [])
            print(f"{r['task_id']}: {action} [{', '.join(changes)}]")

        stats = get_stats()
        print(
            f"\n--- Stats: {stats['completed']}/{stats['queue_total']} completed, {stats['remaining']} remaining ---"
        )


if __name__ == "__main__":
    main()
