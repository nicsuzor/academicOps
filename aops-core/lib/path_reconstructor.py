"""Path reconstruction from session summary JSONs.

Reads enriched session summaries (with timeline_events) and assembles
a cross-session view showing what path was taken, what deviated, and
what was dropped. Designed for ADHD-friendly context recovery.

No JSONL or markdown parsing — reads only pre-computed summary JSONs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path


class EventType(Enum):
    SESSION_START = "session_start"
    TASK_CREATE = "task_create"
    TASK_CLAIM = "task_claim"
    TASK_COMPLETE = "task_complete"
    TASK_UPDATE = "task_update"
    TASK_ABANDON = "task_abandon"
    USER_PROMPT = "user_prompt"


@dataclass
class TimelineEvent:
    timestamp: datetime | None
    event_type: EventType
    session_id: str
    project: str
    description: str
    task_id: str | None = None
    is_deviation: bool = False


@dataclass
class SessionThread:
    session_id: str
    project: str
    start_time: datetime | None
    initial_goal: str  # first user_prompt event
    events: list[TimelineEvent] = field(default_factory=list)
    abandoned_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)


@dataclass
class ReconstructedPath:
    threads: list[SessionThread] = field(default_factory=list)
    abandoned_work: list[TimelineEvent] = field(default_factory=list)
    time_range: tuple[datetime | None, datetime | None] = (None, None)


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse ISO 8601 timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def _build_thread_from_summary(summary: dict) -> SessionThread | None:
    """Build a SessionThread from a summary JSON dict.

    Reads timeline_events array from summary. For summaries without
    timeline_events (pre-enrichment), builds minimal thread from
    date + accomplishments.

    Args:
        summary: Parsed summary JSON dict

    Returns:
        SessionThread or None if insufficient data
    """
    session_id = summary.get("session_id", "")
    project = summary.get("project", "unknown")
    date_str = summary.get("date", "")

    start_time = _parse_timestamp(date_str)

    timeline_raw = summary.get("timeline_events", [])
    events: list[TimelineEvent] = []
    initial_goal = ""
    created_task_ids: set[str] = set()
    completed_task_ids: set[str] = set()

    if timeline_raw:
        # Build events from timeline_events array
        for raw in timeline_raw:
            ts = _parse_timestamp(raw.get("timestamp"))
            event_type_str = raw.get("type", "")

            try:
                event_type = EventType(event_type_str)
            except ValueError:
                continue

            desc = raw.get("description", "")
            task_id = raw.get("task_id") or raw.get("task_title")

            event = TimelineEvent(
                timestamp=ts,
                event_type=event_type,
                session_id=session_id,
                project=project,
                description=desc,
                task_id=task_id,
            )
            events.append(event)

            # Track first user prompt as initial goal
            if event_type == EventType.USER_PROMPT and not initial_goal:
                initial_goal = desc

            # Track task lifecycle
            if event_type == EventType.TASK_CREATE and task_id:
                created_task_ids.add(task_id)
            elif event_type == EventType.TASK_COMPLETE and task_id:
                completed_task_ids.add(task_id)
            elif event_type == EventType.TASK_CLAIM and task_id:
                created_task_ids.add(task_id)

    else:
        # Pre-enrichment fallback: build minimal thread from accomplishments
        accomplishments = summary.get("accomplishments", [])
        summary_text = summary.get("summary")

        if summary_text:
            initial_goal = summary_text
        elif accomplishments:
            initial_goal = accomplishments[0] if accomplishments else ""

        # Add a synthetic session_start event
        if start_time:
            events.append(TimelineEvent(
                timestamp=start_time,
                event_type=EventType.SESSION_START,
                session_id=session_id,
                project=project,
                description=initial_goal or "Session started",
            ))

        # Add accomplishments as synthetic completion events
        for acc in accomplishments:
            events.append(TimelineEvent(
                timestamp=start_time,
                event_type=EventType.TASK_COMPLETE,
                session_id=session_id,
                project=project,
                description=acc,
            ))

    if not events and not initial_goal:
        return None

    # Determine start_time from first event if not from date
    if not start_time and events:
        for e in events:
            if e.timestamp:
                start_time = e.timestamp
                break

    # Abandoned = created but not completed
    abandoned = list(created_task_ids - completed_task_ids)

    return SessionThread(
        session_id=session_id,
        project=project,
        start_time=start_time,
        initial_goal=initial_goal,
        events=events,
        abandoned_tasks=abandoned,
        completed_tasks=list(completed_task_ids),
    )


def _detect_abandoned_work(threads: list[SessionThread]) -> list[TimelineEvent]:
    """Detect tasks created/claimed but never completed across all threads.

    Args:
        threads: List of all session threads

    Returns:
        List of TimelineEvents for abandoned work
    """
    all_created: dict[str, TimelineEvent] = {}
    all_completed: set[str] = set()

    for thread in threads:
        for event in thread.events:
            if event.event_type in (EventType.TASK_CREATE, EventType.TASK_CLAIM):
                if event.task_id and event.task_id not in all_created:
                    all_created[event.task_id] = event
            elif event.event_type == EventType.TASK_COMPLETE:
                if event.task_id:
                    all_completed.add(event.task_id)

    abandoned = []
    for task_id, event in all_created.items():
        if task_id not in all_completed:
            abandoned.append(TimelineEvent(
                timestamp=event.timestamp,
                event_type=EventType.TASK_ABANDON,
                session_id=event.session_id,
                project=event.project,
                description=event.description,
                task_id=task_id,
            ))

    return abandoned


def reconstruct_path(hours: int = 24) -> ReconstructedPath:
    """Reconstruct the path taken across recent sessions.

    Main entry point. Reads summary JSONs, builds session threads,
    detects abandoned work, and returns an assembled path.

    Args:
        hours: Look back window in hours (default: 24)

    Returns:
        ReconstructedPath with threads and abandoned work
    """
    summaries_dir = Path.home() / "writing" / "sessions" / "summaries"
    if not summaries_dir.exists():
        return ReconstructedPath()

    cutoff = datetime.now().astimezone() - timedelta(hours=hours)

    # Collect recent summaries
    threads: list[SessionThread] = []
    seen_sessions: set[str] = set()

    for json_path in sorted(summaries_dir.glob("*.json"), reverse=True):
        # Quick date filter from filename (YYYYMMDD-HH-...)
        try:
            name = json_path.stem
            date_part = name[:8]
            hour_part = name[9:11] if len(name) > 10 and name[8] == "-" else "00"
            file_dt = datetime.strptime(f"{date_part}{hour_part}", "%Y%m%d%H")
            file_dt = file_dt.astimezone()
            if file_dt < cutoff:
                continue
        except (ValueError, IndexError):
            continue

        try:
            with open(json_path, encoding="utf-8") as f:
                summary = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        session_id = summary.get("session_id", "")
        if not session_id or session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)

        thread = _build_thread_from_summary(summary)
        if thread:
            threads.append(thread)

    # Sort by start_time
    threads.sort(key=lambda t: t.start_time or datetime.min.replace(tzinfo=cutoff.tzinfo))

    # Detect abandoned work across all threads
    abandoned = _detect_abandoned_work(threads)

    # Compute time range
    start = None
    end = None
    for t in threads:
        if t.start_time:
            if start is None or t.start_time < start:
                start = t.start_time
            if end is None or t.start_time > end:
                end = t.start_time

    return ReconstructedPath(
        threads=threads,
        abandoned_work=abandoned,
        time_range=(start, end),
    )
