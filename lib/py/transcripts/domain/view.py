"""Selection function for the recent interactive-only view."""

from __future__ import annotations

from transcripts.domain.context import has_user_context
from transcripts.domain.time import get_event_timestamps
from transcripts.model import NormalizedSession


def select_recent_interactive(sessions: list[NormalizedSession]) -> list[NormalizedSession]:
    """Select interactive sessions only and sort them most-recent-first."""
    interactive_sessions = [s for s in sessions if has_user_context(s)]

    def get_start_time(s: NormalizedSession) -> str:
        started_at, _, _ = get_event_timestamps(s.events)
        return started_at

    interactive_sessions.sort(key=get_start_time, reverse=True)
    return interactive_sessions
