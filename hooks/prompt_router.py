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
from datetime import datetime
from pathlib import Path
from typing import Any


# Keyword patterns for skill suggestion
SKILL_KEYWORDS = {
    "framework": {"hook", "automation", "framework", "skill", "settings", "axioms", "claude.md"},
    "python-dev": {"python", "code", "function", "class", "test", "implement", "debug", "refactor"},
    "analyst": {"data", "analysis", "dbt", "streamlit", "research", "dataset", "query"},
    "bmem": {"knowledge", "bmem", "memory", "note", "document", "context", "archive"},
    "tasks": {"task", "tasks", "todo", "todos", "action items"},
}

TEMP_DIR = Path("/tmp/prompt-router")


def write_prompt_to_temp(prompt: str, keyword_matches: list[str]) -> Path:
    """Write prompt and matches to temp JSON file.

    Args:
        prompt: The user's prompt text
        keyword_matches: List of skills that matched keywords

    Returns:
        Path to the created temp file

    Raises:
        OSError: If directory creation or file write fails
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = TEMP_DIR / f"{timestamp}.json"

    data = {
        "prompt": prompt,
        "keyword_matches": keyword_matches,
    }

    filepath.write_text(json.dumps(data, indent=2))
    return filepath


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

    # Write prompt to temp file for classifier (fail-fast: let OSError propagate)
    filepath = write_prompt_to_temp(prompt, matches)

    # Build keyword suggestion
    if len(matches) == 1:
        skill = matches[0]
        keyword_suggestion = f"MANDATORY: You MUST invoke the `{skill}` skill using Skill(skill: '{skill}') BEFORE answering. Do NOT use MCP tools or other tools directly - invoke the skill first to load proper guidance."
    else:
        skill_list = ", ".join(f"`{s}`" for s in matches)
        keyword_suggestion = f"MANDATORY: This prompt requires one of these skills: {skill_list}. You MUST invoke the most relevant skill using Skill(skill: 'X') BEFORE proceeding. Do NOT bypass skill invocation."

    # Build classifier spawn instruction
    classifier_instruction = f"""
CLASSIFIER AVAILABLE: For semantic analysis, invoke Task tool with:
- subagent_type: "general-purpose"
- model: "haiku"
- prompt: "Read {filepath} and classify intent. Return JSON with intent, confidence, skills."
"""

    return f"{keyword_suggestion}\n{classifier_instruction}"


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
