"""Stable deterministic session_id-derived slug logic."""

from __future__ import annotations


def get_stable_slug(session_id: str) -> str:
    """Get a stable, deterministic slug from a session_id.

    This avoids content-derived churn or self-deletion.
    """
    if not session_id:
        return "unknown"
    # Take the first part if it's hyphenated (e.g. UUID), else take first 8 chars
    parts = session_id.split("-")
    if parts and parts[0]:
        return parts[0]
    return session_id[:8]
