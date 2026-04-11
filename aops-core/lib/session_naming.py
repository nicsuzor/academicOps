"""Unified naming for session-related files.

This module provides a single source of truth for session filename generation
to ensure consistency across transcripts, insights, hook logs, and status files.
"""

from __future__ import annotations

import hashlib
from datetime import datetime


def get_session_short_hash(session_id: str) -> str:
    """Get 8-character identifier from session ID.

    Standardizes on the first 8 characters of the session ID (UUID prefix)
    to match Gemini CLI transcript naming. Falls back to SHA-256 hash for
    brevity if the session ID is short or non-standard.

    Args:
        session_id: Full session identifier

    Returns:
        8-character string
    """
    if not session_id or session_id == "unknown":
        raise ValueError(f"Invalid session_id: {session_id!r}. Callers must guard before calling.")

    # 1. If it's a standard UUID or long enough, use the prefix (matches transcript)
    if len(session_id) >= 8:
        # Check if first 8 are valid hex or alphanumeric
        prefix = session_id[:8].lower()
        if all(c in "0123456789abcdefghijklmnopqrstuvwxyz" for c in prefix):
            return prefix

    # 2. Fallback to SHA-256 for short/complex IDs
    return hashlib.sha256(session_id.encode()).hexdigest()[:8]


def get_session_filename(
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
    project: str | None = None,
    slug: str | None = None,
    suffix: str = ".json",
) -> str:
    """Generate a unified filename for session-related files.

    Format: YYYYMMDD-HH-[project-][shorthash][-slug][suffix]

    Args:
        session_id: Session identifier
        date: Date in YYYY-MM-DD format or ISO 8601 (defaults to now)
        hour: 2-digit hour (defaults to extraction from date or now)
        project: Optional project name to include
        slug: Optional descriptive slug
        suffix: File extension/suffix (including dot)

    Returns:
        Formatted filename string
    """
    # 1. Extract date and hour components
    if date is None:
        now = datetime.now().astimezone()
        date_compact = now.strftime("%Y%m%d")
        if hour is None:
            hour = now.strftime("%H")
    elif "T" in date:
        # ISO 8601 format: 2026-01-24T17:30:00+10:00
        dt = datetime.fromisoformat(date)
        date_compact = dt.strftime("%Y%m%d")
        if hour is None:
            hour = dt.strftime("%H")
    else:
        # Simple YYYY-MM-DD format
        date_compact = date.replace("-", "")
        if hour is None:
            hour = datetime.now().astimezone().strftime("%H")

    # 2. Get short hash
    short_hash = get_session_short_hash(session_id)

    # 3. Build parts list
    parts = [date_compact, hour]
    if project:
        parts.append(project)
    parts.append(short_hash)
    if slug:
        parts.append(slug)

    # 4. Join and append suffix
    base = "-".join(parts)
    return f"{base}{suffix}"


def get_hook_log_filename(
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
) -> str:
    """Generate a unified filename for hook logs.

    Format: YYYYMMDD-HH-shorthash-hooks.jsonl
    """
    return get_session_filename(
        session_id=session_id,
        date=date,
        hour=hour,
        suffix="-hooks.jsonl",
    )


def get_gate_filename(
    gate: str,
    session_id: str,
    date: str | None = None,
    hour: str | None = None,
) -> str:
    """Generate a unified filename for gate context files.

    Format: YYYYMMDD-HH-shorthash-gate.md
    """
    return get_session_filename(
        session_id=session_id,
        date=date,
        hour=hour,
        suffix=f"-{gate}.md",
    )
