"""Unified session summary architecture.

Provides tiered capture for session summaries:
1. Task contributions - written after each task reflection
2. Session synthesis - written at session end
3. Recovery fallback - Gemini mining for sessions without contributions

Uses session ID (not project hash) as key to avoid collisions across terminals.

See specs/unified-session-summary.md for architecture details.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast


class TaskContribution(TypedDict, total=False):
    """A single task contribution from framework reflection."""

    request: str  # Required: Original user request
    guidance: str  # What hydrator/custodiet advised
    followed: str  # yes/no/partial
    outcome: str  # success/partial/failure
    accomplishment: str  # What was accomplished (if success/partial)
    project: str  # Project name
    timestamp: str  # ISO timestamp


class TaskContributionsFile(TypedDict):
    """Structure of {session_id}-tasks.json file."""

    session_id: str
    updated_at: str
    tasks: list[TaskContribution]


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
    tasks: list[TaskContribution]
    conversation_flow: list[list[str]]
    user_prompts: list[list[str]]


VALID_OUTCOMES = {"success", "partial", "failure"}


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


def get_task_contributions_path(session_id: str) -> Path:
    """Get path for task contributions file.

    Args:
        session_id: Main session UUID

    Returns:
        Path to {session_id}-tasks.json
    """
    return get_session_summary_dir() / f"{session_id}-tasks.json"


def get_session_summary_path(session_id: str) -> Path:
    """Get path for session summary file.

    Args:
        session_id: Main session UUID

    Returns:
        Path to {session_id}.json
    """
    return get_session_summary_dir() / f"{session_id}.json"


def _validate_task_contribution(task_data: dict[str, Any]) -> None:
    """Validate task contribution data.

    Args:
        task_data: Task data to validate

    Raises:
        ValueError: If required fields missing or invalid values
    """
    if "request" not in task_data:
        raise ValueError("Task contribution must have 'request' field")

    if "outcome" in task_data:
        outcome = task_data["outcome"]
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Invalid outcome '{outcome}'. Must be one of: {VALID_OUTCOMES}"
            )


def append_task_contribution(session_id: str, task_data: dict[str, Any]) -> None:
    """Append a task contribution to the session's task file.

    Creates the file if it doesn't exist. Appends to existing tasks.

    Args:
        session_id: Main session UUID
        task_data: Task contribution data

    Raises:
        ValueError: If task_data fails validation
    """
    _validate_task_contribution(task_data)

    # Ensure directory exists
    summary_dir = get_session_summary_dir()
    summary_dir.mkdir(parents=True, exist_ok=True)

    tasks_path = get_task_contributions_path(session_id)
    now = datetime.now(timezone.utc).isoformat()

    # Load existing or create new
    if tasks_path.exists():
        data: TaskContributionsFile = json.loads(tasks_path.read_text())
    else:
        data = {
            "session_id": session_id,
            "updated_at": now,
            "tasks": [],
        }

    # Add timestamp to task
    task_with_timestamp = dict(task_data)
    task_with_timestamp["timestamp"] = now

    # Append task
    data["tasks"].append(cast(TaskContribution, task_with_timestamp))
    data["updated_at"] = now

    # Write atomically
    tasks_path.write_text(json.dumps(data, indent=2))


def load_task_contributions(session_id: str) -> list[TaskContribution]:
    """Load task contributions for a session.

    Args:
        session_id: Main session UUID

    Returns:
        List of task contributions, empty if file doesn't exist
    """
    tasks_path = get_task_contributions_path(session_id)

    if not tasks_path.exists():
        return []

    try:
        data = json.loads(tasks_path.read_text())
        return data.get("tasks", [])
    except (json.JSONDecodeError, OSError):
        return []


def synthesize_session(
    session_id: str,
    *,
    project: str | None = None,
    date: str | None = None,
    summary: str | None = None,
    accomplishments: list[str] | None = None,
    learning_observations: list[dict[str, Any]] | None = None,
    skill_compliance: dict[str, Any] | None = None,
    context_gaps: list[str] | None = None,
    user_mood: float | None = None,
    conversation_flow: list[list[str]] | None = None,
    user_prompts: list[list[str]] | None = None,
) -> SessionSummary:
    """Synthesize a session summary from task contributions and additional data.

    Merges task contributions with any additional data provided (from Gemini mining
    or other sources).

    Args:
        session_id: Main session UUID
        project: Project name
        date: Date string (YYYY-MM-DD)
        summary: One-sentence session summary
        accomplishments: Additional accomplishments (merged with task-derived)
        learning_observations: Learning observations from mining
        skill_compliance: Skill compliance data
        context_gaps: Context gaps identified
        user_mood: User mood score (-1.0 to 1.0)
        conversation_flow: Conversation flow tuples
        user_prompts: User prompts with context

    Returns:
        SessionSummary with merged data
    """
    # Load task contributions
    tasks = load_task_contributions(session_id)

    # Extract accomplishments from successful tasks
    task_accomplishments: list[str] = []
    for task in tasks:
        if task.get("outcome") in ("success", "partial"):
            if acc := task.get("accomplishment"):
                if acc not in task_accomplishments:
                    task_accomplishments.append(acc)

    # Merge accomplishments (task-derived first, then additional)
    merged_accomplishments = list(task_accomplishments)
    if accomplishments:
        for acc in accomplishments:
            if acc not in merged_accomplishments:
                merged_accomplishments.append(acc)

    # Build summary
    result: SessionSummary = {
        "session_id": session_id,
        "tasks": tasks,
        "accomplishments": merged_accomplishments,
    }

    # Add optional fields
    if project:
        result["project"] = project
    if date:
        result["date"] = date
    if summary:
        result["summary"] = summary
    if learning_observations:
        result["learning_observations"] = learning_observations
    if skill_compliance:
        result["skill_compliance"] = skill_compliance
    if context_gaps:
        result["context_gaps"] = context_gaps
    if user_mood is not None:
        result["user_mood"] = user_mood
    if conversation_flow:
        result["conversation_flow"] = conversation_flow
    if user_prompts:
        result["user_prompts"] = user_prompts

    return result


def save_session_summary(session_id: str, summary: SessionSummary) -> None:
    """Save a session summary to disk.

    Args:
        session_id: Main session UUID
        summary: Session summary to save
    """
    # Ensure directory exists
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
