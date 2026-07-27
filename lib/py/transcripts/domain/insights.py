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

    # Post-hoc fallback summary to ensure insights are reliably populated for every session
    tool_counts: dict[str, int] = {}
    for event in session.events:
        if event.source == "model" and event.tool_calls:
            for tc in event.tool_calls:
                tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1
        elif event.source == "tool" and event.meta and event.meta.get("tool_name"):
            name = event.meta["tool_name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

    last_assistant_msg = ""
    for event in reversed(session.events):
        if event.source == "model" and event.content:
            last_assistant_msg = event.content.strip()
            break

    if last_assistant_msg:
        summary_msg = last_assistant_msg
        if len(summary_msg) > 300:
            summary_msg = summary_msg[:297] + "..."
    else:
        summary_msg = "No assistant messages recorded."

    tools_str = ", ".join(f"{k} (x{v})" for k, v in sorted(tool_counts.items()))
    if tools_str:
        fallback_text = (
            f"Session summary: Executed tools: {tools_str}. Final response: {summary_msg}"
        )
    else:
        fallback_text = f"Session summary: No tools executed. Final response: {summary_msg}"

    return fallback_text
