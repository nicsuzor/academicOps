#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Two-tier routing:
1. Keyword match → Motivational skill suggestion (v2 framing)
2. No match → Offers Haiku classifier spawn for semantic analysis

Uses benefit-focused framing rather than imperative commands.
Tracks framingVersion for compliance measurement.

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


# Focus reminder - concise
FOCUS_REMINDER = "**CRITICAL**: Focus on the user's specific request. Do NOT over-elaborate or add unrequested features. Complete the task, then stop."

# Framing version for A/B measurement
FRAMING_VERSION = "v3-academic-rigor"

# Generic skill suggestion framing - high-level, appeals to agent's desire for quality
SKILL_FRAMING = (
    "You are operating in a sensitive academic environment that requires rigor. "
    "Before proceeding, invoke {skill_instruction} to load context that may not be immediately apparent."
)

# Skills - just names for keyword matching, descriptions for classifier
SKILLS: dict[str, str] = {
    "framework": "Categorical conventions and framework patterns",
    "python-dev": "Production Python: fail-fast, type safety, TDD",
    "analyst": "Research data analysis: dbt, Streamlit, statistics",
    "bmem": "Knowledge base operations and format requirements",
    "tasks": "Task scripts and workflow patterns",
    "pdf": "Markdown to professional PDF conversion",
    "osb-drafting": "IRAC analysis and precedent citation for Oversight Board",
    "learning-log": "Thematic pattern logging to learning files",
    "transcript": "Session JSONL to markdown conversion",
    "skill-creator": "Skill packaging following anti-bloat principles",
    "training-set-builder": "Training data extraction from document sets",
    "extractor": "Email archive processing and extraction",
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


def analyze_prompt(prompt: str) -> tuple[str, list[str]]:
    """Analyze prompt and return motivational skill suggestion.

    Uses benefit-focused framing rather than imperative commands.

    Args:
        prompt: The user's prompt text

    Returns:
        Tuple of (suggestion text, list of matched skill names)
    """
    if not prompt:
        return "", []

    prompt_lower = prompt.lower()

    # Keyword triggers for each skill (expanded coverage)
    triggers = {
        "framework": [
            "framework", "hook", "skill", "axioms", "claude.md", "settings.json",
            "readme.md", "aops", "academicops", "convention", "pattern",
            "infrastructure", "how do we", "what's the rule",
        ],
        "python-dev": [
            "python", "pytest", "uv run", "type hint", "mypy", ".py",
            "function", "class", "import", "async", "typing",
        ],
        "tasks": [
            "archive task", "view task", "create task", "task list", "tasks",
            "what's urgent", "show my tasks", "to-do", "todo", "priorities",
            "what needs doing", "what should i work on", "email", "inbox",
        ],
        "bmem": [
            "bmem", "knowledge base", "write note", "search notes",
            "remember this", "save this", "what do we know about",
            "context about", "background on", "prior work on",
            "have we done", "did we already", "memory", "capture",
        ],
        "pdf": ["pdf", "generate pdf", "create pdf", "markdown to pdf", "document"],
        "osb-drafting": ["osb", "oversight board", "case decision", "irac", "precedent"],
        "learning-log": ["log failure", "log success", "agent pattern", "learning log", "lesson"],
        "transcript": ["transcript", "session transcript", "conversation log", "session history"],
        "extractor": ["extract email", "email archive", "process archive", "mbox"],
        "analyst": ["analysis", "statistics", "dbt", "streamlit", "data", "model", "regression"],
    }

    matched_skills = []
    for skill, keywords in triggers.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_skills.append(skill)

    if not matched_skills:
        # No keyword match - offer semantic classification via Haiku
        filepath = write_prompt_context(prompt)
        classifier_instruction = (
            f"Task(subagent_type=\"general-purpose\", model=\"haiku\", "
            f"prompt=\"Read {filepath} and classify intent. Return the single best "
            f"skill from available_skills, or 'none' if no skill applies.\")"
        )
        return SKILL_FRAMING.format(skill_instruction=classifier_instruction), []

    # Build suggestion using generic academic rigor framing (v3)
    if len(matched_skills) == 1:
        skill_instruction = f"Skill(skill=\"{matched_skills[0]}\")"
    else:
        options = " or ".join(f"Skill(skill=\"{s}\")" for s in matched_skills)
        skill_instruction = f"one of: {options}"

    return SKILL_FRAMING.format(skill_instruction=skill_instruction), matched_skills


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    prompt = input_data.get("prompt", "")

    # Get motivational skill suggestion (v2 framing)
    advisory, matched_skills = analyze_prompt(prompt)

    # Build output - always include focus reminder, add skill routing if matched
    context_parts = [FOCUS_REMINDER]
    if advisory:
        context_parts.append(advisory)

    hook_specific_output: dict[str, Any] = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "\n".join(context_parts),
        "framingVersion": FRAMING_VERSION,  # For A/B measurement
    }
    if matched_skills:
        hook_specific_output["skillsMatched"] = matched_skills

    output: dict[str, Any] = {
        "hookSpecificOutput": hook_specific_output
    }

    # Log with output data (so transcript can show it)
    session_id = input_data.get("session_id", "unknown")
    log_hook_event(
        session_id=session_id,
        hook_event="UserPromptSubmit",
        input_data=input_data,
        output_data={"hookSpecificOutput": hook_specific_output},
        exit_code=0,
    )

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
