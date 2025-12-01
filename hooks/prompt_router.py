#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Writes prompt to temp file and instructs main agent to spawn a Haiku
classifier subagent for semantic skill recommendation.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from hooks.hook_logger import log_hook_event


# All available skills with descriptions
SKILLS = {
    "framework": "Maintain automation framework, design experiments, work on hooks/skills/commands infrastructure",
    "python-dev": "Write production-quality Python code with fail-fast philosophy, type safety, TDD",
    "analyst": "Academic research data analysis using dbt, Streamlit, statistical analysis",
    "bmem": "Knowledge base management, search notes, create documentation, session mining",
    "tasks": "Task management - view, archive, create tasks using task scripts",
}

TEMP_DIR = Path.home() / ".cache" / "aops" / "prompt-router"


def write_prompt_context(prompt: str) -> Path:
    """Write prompt and skill context to temp file for classifier.

    Args:
        prompt: The user's prompt text

    Returns:
        Path to the context file
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = TEMP_DIR / f"{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "prompt": prompt,
        "available_skills": SKILLS,
    }

    filepath.write_text(json.dumps(data, indent=2))
    return filepath


def analyze_prompt(prompt: str) -> str:
    """Analyze prompt and return skill invocation instruction when keywords match.

    Args:
        prompt: The user's prompt text

    Returns:
        Skill invocation instruction string, or empty string if no match
    """
    if not prompt:
        return ""

    prompt_lower = prompt.lower()

    # Keyword triggers for each skill
    triggers = {
        "framework": ["framework", "hook", "skill", "axioms", "claude.md", "settings.json"],
        "python-dev": ["python", "pytest", "uv run", "type hint", "mypy"],
        "tasks": ["archive task", "view task", "create task", "task list", "tasks"],
        "bmem": ["bmem", "knowledge base", "write note", "search notes"],
    }

    matched_skills = []
    for skill, keywords in triggers.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_skills.append(skill)

    if not matched_skills:
        return ""

    # Build response based on number of matches
    if len(matched_skills) == 1:
        skill = matched_skills[0]
        return f"MANDATORY: Invoke the `{skill}` skill before proceeding with this request."
    else:
        skills_list = ", ".join(f"`{s}`" for s in matched_skills)
        return f"MANDATORY: Invoke one of these skills before proceeding: {skills_list}"


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")
    prompt = input_data.get("prompt", "")

    # Get classifier spawn instruction
    advisory = analyze_prompt(prompt)

    # Build output
    output: dict[str, Any] = {}

    if advisory:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": advisory
            }
        }

    # Log hook event
    log_hook_event(session_id, "PromptRouter", input_data, output, exit_code=0)

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
