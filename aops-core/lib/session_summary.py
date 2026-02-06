"""Session summary storage.

Simple storage for session summaries extracted by LLM (Claude skill or Gemini cron).
Uses session ID (not project hash) as key to avoid collisions across terminals.

See specs/unified-session-summary.md for architecture details.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict

from .session_paths import get_session_short_hash


class SessionSummary(TypedDict, total=False):
    """Full session summary structure."""

    session_id: str
    date: str
    project: str
    summary: str
    accomplishments: list[str]
    learning_observations: list[dict[str, Any]]
    skill_compliance: dict[str, Any]
    context_gaps: list[str]
    user_mood: float
    conversation_flow: list[list[str]]
    user_prompts: list[list[str]]
    tasks: list[dict[str, Any]]


def get_session_summary_dir() -> Path:
    """Get directory for session summary files.

    Returns:
        Path to $ACA_DATA/dashboard/sessions/

    Raises:
        ValueError: If ACA_DATA environment variable not set
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        raise ValueError("ACA_DATA environment variable not set")

    return Path(aca_data) / "dashboard" / "sessions"


def get_session_summary_path(session_id: str) -> Path:
    """Get path for session summary file.

    Args:
        session_id: Main session UUID (or short ID)

    Returns:
        Path to {short_hash}.json
    """
    short_hash = get_session_short_hash(session_id)
    return get_session_summary_dir() / f"{short_hash}.json"


def get_task_contributions_path(session_id: str) -> Path:
    """Get path for task contributions file.

    Args:
        session_id: Main session UUID

    Returns:
        Path to {short_hash}-tasks.json
    """
    short_hash = get_session_short_hash(session_id)
    return get_session_summary_dir() / f"{short_hash}-tasks.json"


def save_session_summary(session_id: str, summary: SessionSummary) -> None:
    """Save a session summary to disk.

    Args:
        session_id: Main session UUID
        summary: Session summary to save
    """
    summary_dir = get_session_summary_dir()
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = get_session_summary_path(session_id)
    summary_path.write_text(json.dumps(summary, indent=2))


def load_session_summary(session_id: str) -> SessionSummary | None:
    """Load a session summary from disk.

    Args:
        session_id: Main session UUID

    Returns:
        SessionSummary or None if not found
    """
    summary_path = get_session_summary_path(session_id)

    if not summary_path.exists():
        return None

    try:
        return json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_task_contributions(session_id: str) -> list[dict[str, Any]]:
    """Load task contributions for a session.

    Args:
        session_id: Main session UUID

    Returns:
        List of task contribution dicts
    """
    path = get_task_contributions_path(session_id)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
        return data.get("tasks", [])
    except (json.JSONDecodeError, OSError):
        return []


def append_task_contribution(session_id: str, task_data: dict[str, Any]) -> None:
    """Append a task contribution to the session's temporary task store.

    Args:
        session_id: Main session UUID
        task_data: Contribution data (request, outcome, accomplishment, etc.)

    Raises:
        ValueError: If mandatory fields are missing or invalid
    """
    if "request" not in task_data:
        raise ValueError("Task contribution must have 'request' field")

    outcome = task_data.get("outcome")
    if outcome and outcome not in ("success", "partial", "failure"):
        raise ValueError(f"Invalid outcome: {outcome}")

    summary_dir = get_session_summary_dir()
    summary_dir.mkdir(parents=True, exist_ok=True)

    path = get_task_contributions_path(session_id)
    import time

    from datetime import datetime

    ts = datetime.now().isoformat()

    if path.exists():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            data = {"session_id": session_id, "tasks": []}
    else:
        data = {"session_id": session_id, "tasks": []}

    # Add timestamp to task
    task_with_ts = dict(task_data)
    task_with_ts["timestamp"] = ts

    data["tasks"].append(task_with_ts)
    data["updated_at"] = time.time()

    path.write_text(json.dumps(data, indent=2))


def synthesize_session(
    session_id: str,
    project: str | None = None,
    date: str | None = None,
    **kwargs,
) -> SessionSummary:
    """Synthesize final session summary from task contributions and additional data.

    Args:
        session_id: Main session UUID
        project: Project name (optional override)
        date: Session date (optional override, YYYY-MM-DD)
        **kwargs: Additional fields to merge into summary

    Returns:
        Synthesized SessionSummary
    """
    from datetime import date as dt

    if date is None:
        date = dt.today().strftime("%Y-%m-%d")

    tasks = load_task_contributions(session_id)

    # Extract accomplishments from successful/partial tasks
    accomplishments = []
    for task in tasks:
        outcome = task.get("outcome")
        acc = task.get("accomplishment")
        if outcome in ("success", "partial") and acc:
            if acc not in accomplishments:
                accomplishments.append(acc)

    # Merge explicitly provided accomplishments
    extra_acc = kwargs.get("accomplishments", [])
    for acc in extra_acc:
        if acc not in accomplishments:
            accomplishments.append(acc)

    summary: SessionSummary = {
        "session_id": session_id,
        "date": date,
        "project": project or "",
        "accomplishments": accomplishments,
        "tasks": tasks,
    }

    # Merge remaining kwargs
    for k, v in kwargs.items():
        if k != "accomplishments":
            summary[k] = v

    # Ensure defaults for required fields if not provided
    if "summary" not in summary:
        summary["summary"] = ""
    if "learning_observations" not in summary:
        summary["learning_observations"] = []

    return summary
