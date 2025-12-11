#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Two-tier routing:
1. Keyword match → MANDATORY skill invocation instruction
2. No match → Offers Haiku classifier spawn for semantic analysis

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


# All available skills with descriptions for routing
SKILLS = {
    "framework": "Maintain automation framework, design experiments, work on hooks/skills/commands infrastructure",
    "python-dev": "Write production-quality Python code with fail-fast philosophy, type safety, TDD",
    "analyst": "Support academic research data analysis using dbt and Streamlit",
    "bmem": "Knowledge base management, search notes, create documentation",
    "tasks": "Task management - view, archive, create tasks using task scripts",
    "pdf": "Convert markdown documents to professionally formatted PDFs",
    "osb-drafting": "Generate draft OSB case decisions with IRAC analysis and precedent support",
    "learning-log": "Log agent performance patterns to thematic learning files",
    "transcript": "Generate markdown transcripts from Claude Code session files",
    "skill-creator": "Create and maintain skills following anti-bloat principles",
    "training-set-builder": "Extract structured training examples from document sets",
    "extractor": "Process email archive files, extract high-value information",
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
        "framework": [
            "framework", "hook", "skill", "axioms", "claude.md", "settings.json",
            "readme.md", "aops", "academicops",
        ],
        "python-dev": ["python", "pytest", "uv run", "type hint", "mypy"],
        "tasks": [
            "archive task", "view task", "create task", "task list", "tasks",
            "what's urgent", "show my tasks", "to-do", "todo", "priorities",
            "what needs doing", "what should i work on",
        ],
        "bmem": [
            "bmem", "knowledge base", "write note", "search notes",
            "remember this", "save this", "what do we know about",
            "context about", "background on", "prior work on",
            "have we done", "did we already",
        ],
        "pdf": ["pdf", "generate pdf", "create pdf", "markdown to pdf"],
        "osb-drafting": ["osb", "oversight board", "case decision", "irac"],
        "learning-log": ["log failure", "log success", "agent pattern", "learning log"],
        "transcript": ["transcript", "session transcript", "conversation log"],
        "extractor": ["extract email", "email archive", "process archive"],
    }

    matched_skills = []
    for skill, keywords in triggers.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_skills.append(skill)

    if not matched_skills:
        # No keyword match - offer semantic classification via Haiku
        filepath = write_prompt_context(prompt)
        return (
            f"CLASSIFIER AVAILABLE: No keyword match for skills. For semantic analysis, "
            f"invoke Task tool with:\n"
            f"- subagent_type: \"general-purpose\"\n"
            f"- model: \"haiku\"\n"
            f"- prompt: \"Read {filepath} and classify intent. Return the single best "
            f"skill from available_skills, or 'none' if no skill applies.\""
        )

    # Build response with explicit Skill tool syntax
    # Per learning log 2025-12-01: agents interpret "invoke X skill" as "read skill file"
    # Explicit Skill(skill="X") syntax is unambiguous
    if len(matched_skills) == 1:
        skill = matched_skills[0]
        desc = SKILLS.get(skill, "")
        return (
            f"MANDATORY: Call Skill(skill=\"{skill}\") before proceeding with this request.\n"
            f"Skill purpose: {desc}\n"
            f"DO NOT use raw MCP tools (mcp__bmem__*, mcp__task_manager__*) directly. "
            f"The skill provides context and quality control that raw tools lack."
        )
    else:
        skills_list = ", ".join(f"Skill(skill=\"{s}\")" for s in matched_skills)
        return (
            f"MANDATORY: Invoke one of these skills before proceeding: {skills_list}\n"
            f"DO NOT use raw MCP tools directly - skills provide context and quality control."
        )


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
