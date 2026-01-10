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
        Path to {session_id}.json
    """
    return get_session_summary_dir() / f"{session_id}.json"


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
