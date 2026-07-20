"""Reflection to insights extraction logic."""

from __future__ import annotations

from transcripts.model import NormalizedSession


def infer_insights(session: NormalizedSession) -> str | None:
    """Extract reflection/insights from session events."""
    insights: list[str] = []

    # Extract from model output containing VERDICT / MECHANISM or explicit summary
    for event in session.events:
        if event.source == "model" and event.type == "message" and event.content:
            content = event.content
            if "VERDICT:" in content or "MECHANISM:" in content:
                insights.append(content)
        elif event.type == "checkpoint" and event.content:
            if "USER Objective:" in event.content:
                insights.append(event.content)

    if insights:
        return "\n\n".join(insights)
    return None
