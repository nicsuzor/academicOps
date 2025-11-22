#!/usr/bin/env python3
"""Prompt intent router hook for Claude Code.

Routes prompts to appropriate skills by classifying intent and
providing skill recommendations via additionalContext.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from typing import Any

from hooks.intent_classifier import classify_prompt


def route_prompt(input_data: dict[str, Any]) -> dict[str, Any]:
    """Route a prompt based on intent classification.

    Args:
        input_data: Dict with session_id, prompt, etc.

    Returns:
        Dict with additionalContext containing skill recommendations.
    """
    prompt = input_data.get("prompt", "")
    if not prompt:
        return {}

    try:
        result = classify_prompt(prompt)
    except Exception:
        return {}

    skills = result.get("recommended_skills", [])
    intent = result.get("intent", "other")
    confidence = result.get("confidence", 0.0)
    reasoning = result.get("reasoning", "")

    if not skills:
        return {}

    context_lines = [
        f"Suggested skill(s): {', '.join(skills)}",
        f"Intent: {intent} (confidence: {confidence:.0%})",
        f"Reasoning: {reasoning}",
    ]

    return {"additionalContext": "\n".join(context_lines)}


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    output_data = route_prompt(input_data)
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
