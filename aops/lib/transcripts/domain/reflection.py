from typing import Any

from transcripts.model import NormalizedSession


def extract_insights(session: NormalizedSession) -> dict[str, Any]:
    """Extract key insights (accomplishments, decisions, tool counts, errors) from session events."""
    accomplishments: list[str] = []
    decisions: list[str] = []
    tool_counts: dict[str, int] = {}
    errors: list[str] = []

    for event in session.events:
        # Trace tool calls
        if event.tool_calls:
            for tc in event.tool_calls:
                tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1

        # Look for explicit accomplishments or decisions in user/model messages
        if event.source in {"user", "model"}:
            content = event.content
            if "Accomplishments:" in content:
                for line in content.splitlines():
                    if "Accomplishments:" in line:
                        acc = line.split("Accomplishments:", 1)[1].strip()
                        if acc and acc.lower() != "none":
                            accomplishments.append(acc)
            # Look for decisions in ask_question or ask_permission tool calls
            if event.tool_calls:
                for tc in event.tool_calls:
                    if tc.name in {"ask_question", "ask_permission"}:
                        decisions.append(f"Asked user for permission/clarification: {tc.args}")

        # Check for errors in tool outputs or system messages
        if event.source == "system" and "error" in event.content.lower():
            errors.append(event.content.strip())
        elif event.type == "tool_output" and "error" in event.content.lower():
            errors.append(event.content.strip())

    return {
        "accomplishments": accomplishments,
        "decisions": decisions,
        "tool_counts": tool_counts,
        "errors": errors[:5],
    }
