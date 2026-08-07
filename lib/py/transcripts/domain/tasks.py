"""Task management domain module with standardized ISO-8601 UTC timestamps.

Provides task mutation logic, timestamp tracking, and `list_tasks` staleness query
filtering with explicit ISO-8601 UTC timestamps (YYYY-MM-DDTHH:MM:SS.ffffff+00:00).
Eliminates bogus fallback timestamps (mtime).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from transcripts.domain.time import format_iso_utc, parse_iso_utc


def create_task(
    title: str,
    status: str = "inbox",
    created_at: str | datetime | date | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a task record with explicit ISO-8601 UTC timestamps.

    Never falls back to filesystem mtime. Ensures created and modified fields
    are explicitly recorded in ISO-8601 UTC format (YYYY-MM-DDTHH:MM:SS.ffffff+00:00).
    """
    ts_str = format_iso_utc(created_at)
    task: dict[str, Any] = {
        "title": title,
        "status": status,
        "created": ts_str,
        "created_at": ts_str,
        "modified": ts_str,
        "updated_at": ts_str,
    }
    task.update(kwargs)
    return task


def update_task(
    task: dict[str, Any],
    updates: dict[str, Any] | None = None,
    modified_at: str | datetime | date | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update a task record and bump its modified timestamp explicitly.

    Applies updates and sets `modified` and `updated_at` to an explicit ISO-8601 UTC string.
    Never relies on filesystem mtime.
    """
    updated_task = task.copy()
    if updates:
        updated_task.update(updates)
    if kwargs:
        updated_task.update(kwargs)

    mod_ts = format_iso_utc(modified_at)
    updated_task["modified"] = mod_ts
    updated_task["updated_at"] = mod_ts
    return updated_task


def validate_task_timestamps(task: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize task modification timestamps.

    If modified timestamp is valid ISO string or datetime, standardizes it to UTC ISO string.
    If missing or invalid, eliminates bogus mtime fallbacks.
    """
    validated = task.copy()
    raw_mod = task.get("modified") or task.get("updated_at") or task.get("last_modified")
    parsed = parse_iso_utc(raw_mod)
    if parsed is not None:
        formatted = format_iso_utc(parsed)
        validated["modified"] = formatted
        validated["updated_at"] = formatted
    else:
        validated["modified"] = None
        validated["updated_at"] = None
    return validated


def list_tasks(
    tasks: list[dict[str, Any]],
    since: str | date | datetime | None = None,
    before: str | date | datetime | None = None,
    status: str | None = None,
    include_done: bool = False,
    format: str = "json",
    limit: int = 50,
    **filters: Any,
) -> dict[str, Any] | str:
    """List tasks with smart filtering and validated ISO-8601 UTC modified timestamps.

    Filters:
    - `since`: return only tasks modified on or after YYYY-MM-DD or ISO timestamp (inclusive).
    - `before`: return only tasks modified on or before YYYY-MM-DD or ISO timestamp (inclusive).
    - `status`: filter by task status (e.g. 'ready', 'blocked', 'inbox', 'queued', 'in_progress').
    - `include_done`: if False and no status specified, hide done and cancelled tasks.

    Eliminates bogus fallback timestamps (mtime). Tasks with no explicit modified metadata
    are excluded when since/before date range filtering is active.
    """
    since_dt = parse_iso_utc(since) if since is not None else None

    before_dt: datetime | None = None
    if before is not None:
        if isinstance(before, str) and "T" not in before and " " not in before:
            d = parse_iso_utc(before)
            if d is not None:
                before_dt = datetime.combine(d.date(), datetime.max.time(), tzinfo=UTC)
        elif isinstance(before, date) and not isinstance(before, datetime):
            before_dt = datetime.combine(before, datetime.max.time(), tzinfo=UTC)
        else:
            before_dt = parse_iso_utc(before)

    filtered: list[dict[str, Any]] = []

    for item in tasks:
        # Check done/cancelled status filter default
        item_status = str(item.get("status", "")).lower()
        if not include_done and status is None:
            if item_status in ("done", "cancelled", "completed"):
                continue

        # Check explicit status filter
        if status is not None:
            if item_status != status.lower():
                continue

        # Check additional attribute filters if passed
        match_filters = True
        for fk, fv in filters.items():
            if fv is not None and item.get(fk) != fv:
                match_filters = False
                break
        if not match_filters:
            continue

        # Parse task modified timestamp — MUST NOT fall back to file mtime
        raw_modified = item.get("modified") or item.get("updated_at") or item.get("last_modified")
        task_mod_dt = parse_iso_utc(raw_modified)

        # Date filtering (since / before)
        if since_dt is not None:
            if task_mod_dt is None or task_mod_dt < since_dt:
                continue

        if before_dt is not None:
            if task_mod_dt is None or task_mod_dt > before_dt:
                continue

        # Construct validated output item
        task_out = item.copy()
        if task_mod_dt is not None:
            task_out["modified"] = format_iso_utc(task_mod_dt)
            task_out["updated_at"] = format_iso_utc(task_mod_dt)
        else:
            task_out["modified"] = None
            task_out["updated_at"] = None

        filtered.append(task_out)

    limited = filtered[:limit]

    if format.lower() == "markdown":
        lines = [f"# Task List (Showing {len(limited)} of {len(filtered)})"]
        for t in limited:
            mod_str = t.get("modified") or "No modified date"
            lines.append(
                f"- [{t.get('status', 'unknown')}] {t.get('title', 'Untitled')} (modified: {mod_str})"
            )
        return "\n".join(lines)

    return {
        "total": len(filtered),
        "showing": len(limited),
        "tasks": limited,
    }
