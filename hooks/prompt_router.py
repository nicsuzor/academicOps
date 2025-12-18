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


# Focus reminder - softer framing (v2)
FOCUS_REMINDER = "REMINDER: The user's request is specific. Addressing exactly what was asked (and stopping there) produces the most useful responses."

# Framing version for A/B measurement
FRAMING_VERSION = "v2-motivational"

# Skills with benefit/risk framing for motivational suggestions
SKILLS: dict[str, dict[str, str]] = {
    "framework": {
        "description": "Categorical conventions and framework patterns",
        "benefit": "You'll have access to exact patterns and conventions, ensuring changes fit existing architecture",
        "risk": "You may propose changes that violate conventions or conflict with existing patterns",
    },
    "python-dev": {
        "description": "Production Python: fail-fast, type safety, TDD",
        "benefit": "You'll write code matching strict standards on first try, avoiding rejection patterns",
        "risk": "Your code may use defaults or untyped patterns that violate fail-fast principles",
    },
    "analyst": {
        "description": "Research data analysis: dbt, Streamlit, statistics",
        "benefit": "You'll follow established patterns for data pipelines and statistical analysis",
        "risk": "You may use patterns that don't integrate with the existing dbt/Streamlit setup",
    },
    "bmem": {
        "description": "Knowledge base operations and format requirements",
        "benefit": "You'll write notes in exact format required, with correct categories and locations",
        "risk": "You may create files in wrong directories or break knowledge graph integrity",
    },
    "tasks": {
        "description": "Task scripts and workflow patterns",
        "benefit": "You'll use correct scripts and avoid creating duplicate tasks",
        "risk": "You may write task files directly (forbidden) or create duplicates",
    },
    "pdf": {
        "description": "Markdown to professional PDF conversion",
        "benefit": "You'll know exact style parameters and formatting requirements",
        "risk": "You may generate PDFs that don't match academic formatting standards",
    },
    "osb-drafting": {
        "description": "IRAC analysis and precedent citation for Oversight Board",
        "benefit": "You'll use correct legal analysis framework and citation format",
        "risk": "Your analysis may miss required IRAC sections or cite precedents incorrectly",
    },
    "learning-log": {
        "description": "Thematic pattern logging to learning files",
        "benefit": "You'll log to the correct thematic file with proper format",
        "risk": "Patterns may be logged incorrectly or to wrong files",
    },
    "transcript": {
        "description": "Session JSONL to markdown conversion",
        "benefit": "You'll generate transcripts in expected format with correct metadata",
        "risk": "Transcripts may be malformed or missing key session context",
    },
    "skill-creator": {
        "description": "Skill packaging following anti-bloat principles",
        "benefit": "You'll create skills that fit framework conventions and pass validation",
        "risk": "Your skill may violate size limits or structural requirements",
    },
    "training-set-builder": {
        "description": "Training data extraction from document sets",
        "benefit": "You'll extract examples in correct format for downstream training",
        "risk": "Training examples may be malformed or miss important patterns",
    },
    "extractor": {
        "description": "Email archive processing and extraction",
        "benefit": "You'll extract actionable information in correct format",
        "risk": "Important information may be missed or formatted incorrectly",
    },
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

    # Flatten skills to just descriptions for classifier
    skills_summary = {name: info["description"] for name, info in SKILLS.items()}
    data = {
        "timestamp": timestamp,
        "prompt": prompt,
        "available_skills": skills_summary,
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
        skill_list = "\n".join(
            f"   - {name}: {info['description']}"
            for name, info in SKILLS.items()
        )
        return (
            f"CLASSIFIER AVAILABLE: No keyword match for skills. For semantic analysis, "
            f"invoke Task tool with:\n"
            f"- subagent_type: \"general-purpose\"\n"
            f"- model: \"haiku\"\n"
            f"- prompt: \"Read {filepath} and classify intent. Return the single best "
            f"skill from available_skills, or 'none' if no skill applies.\""
        ), []

    # Build motivational response (v2 framing)
    if len(matched_skills) == 1:
        skill = matched_skills[0]
        info = SKILLS[skill]
        return (
            f"CONTEXT AVAILABLE: {skill} skill\n\n"
            f"WHY THIS HELPS:\n{info['benefit']}\n\n"
            f"WITHOUT THIS CONTEXT:\n{info['risk']}\n\n"
            f"TO LOAD: Skill(skill=\"{skill}\")"
        ), matched_skills
    else:
        skill_list = "\n".join(
            f"- {s}: {SKILLS[s]['benefit']}" for s in matched_skills
        )
        return (
            f"CONTEXT AVAILABLE: Multiple relevant skills\n\n"
            f"{skill_list}\n\n"
            f"RECOMMENDATION: Load the most relevant skill first.\n"
            f"TO LOAD: Skill(skill=\"[chosen-skill]\")"
        ), matched_skills


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
