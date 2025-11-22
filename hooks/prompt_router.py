#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Analyzes prompt text for keywords and returns advisory context
suggesting relevant skills.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from typing import Any


# Keyword patterns for skill suggestion
SKILL_KEYWORDS = {
    "framework": {"hook", "automation", "framework", "skill", "settings", "axioms", "claude.md"},
    "python-dev": {"python", "code", "function", "class", "test", "implement", "debug", "refactor"},
    "analyst": {"data", "analysis", "dbt", "streamlit", "research", "dataset", "query"},
    "bmem": {"knowledge", "bmem", "memory", "note", "document", "context", "archive"},
}


def analyze_prompt(prompt: str) -> str:
    """Analyze prompt text and return skill suggestion.

    Args:
        prompt: The user's prompt text

    Returns:
        Advisory context string, or empty string if no keywords match
    """
    if not prompt:
        return ""

    prompt_lower = prompt.lower()
    matches = []

    # Check each skill's keywords
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(keyword in prompt_lower for keyword in keywords):
            matches.append(skill)

    if not matches:
        return ""

    if len(matches) == 1:
        skill = matches[0]
        return f"SKILL SUGGESTION: This prompt may benefit from the `{skill}` skill. Acknowledge this suggestion in your response."

    # Multiple matches
    skill_list = ", ".join(f"`{s}`" for s in matches)
    return f"SKILL SUGGESTION: This prompt may relate to multiple skills: {skill_list}. Consider which is most relevant."


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    prompt = input_data.get("prompt", "")

    # Analyze and get advisory context
    advisory = analyze_prompt(prompt)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": advisory
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
