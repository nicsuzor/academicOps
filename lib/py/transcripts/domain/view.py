"""Selection function for the recent interactive-only view."""

from __future__ import annotations

from typing import Any

from transcripts.domain.context import has_user_context
from transcripts.domain.time import get_event_timestamps
from transcripts.model import NormalizedEvent, NormalizedSession


def select_recent_interactive(sessions: list[NormalizedSession]) -> list[NormalizedSession]:
    """Select interactive sessions only and sort them most-recent-first."""
    interactive_sessions = [s for s in sessions if has_user_context(s)]

    def get_start_time(s: NormalizedSession) -> str:
        started_at, _, _ = get_event_timestamps(s.events)
        return started_at

    interactive_sessions.sort(key=get_start_time, reverse=True)
    return interactive_sessions


def filter_controller_events(session: NormalizedSession) -> list[NormalizedEvent]:
    """Extract events belonging strictly to the main controlling thread."""
    return list(session.events)


def get_subagent_summaries(session: NormalizedSession) -> list[dict[str, Any]]:
    """Build lightweight summary index objects for all subagents in a session."""
    summaries = []
    for idx, sub in enumerate(session.subagents, start=1):
        summaries.append(
            {
                "index": idx,
                "agent_id": sub.agent_id,
                "label": sub.label,
                "agent_type": sub.agent_type or "",
                "spawn_depth": sub.spawn_depth,
                "is_fork": sub.is_fork,
                "event_count": len(sub.events),
                "tokens_used": sub.tokens_used,
                "cost_usd": sub.cost_usd,
                "description": sub.description or "",
            }
        )
    return summaries

