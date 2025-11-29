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
    """Analyze prompt and return skill suggestion only when clearly needed.

    Conservative approach: only suggest skills for prompts that clearly
    benefit from specialized workflows. Most prompts need no routing.

    Args:
        prompt: The user's prompt text

    Returns:
        Soft suggestion string, or empty string (most cases)
    """
    if not prompt or len(prompt) < 20:
        return ""

    prompt_lower = prompt.lower()

    # Only trigger for explicit skill-domain keywords
    # These are prompts that CLEARLY benefit from skill invocation
    triggers = {
        "framework": ["hook", "skill", "axioms", "claude.md", "settings.json"],
        "tasks": ["archive task", "view task", "create task", "task list"],
        "bmem": ["bmem", "knowledge base", "write note", "search notes"],
    }

    matched_skill = None
    for skill, keywords in triggers.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_skill = skill
            break

    if not matched_skill:
        return ""  # Most prompts - no suggestion

    # Soft suggestion, not demand
    return f"Consider: The `{matched_skill}` skill may help with this request."


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
