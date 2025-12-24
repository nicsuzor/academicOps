#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Two-tier routing:
1. Explicit slash command → Direct route to command
2. Everything else → LLM classifier with full capabilities

Uses benefit-focused framing rather than imperative commands.
Tracks framingVersion for compliance measurement.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from hooks.hook_logger import log_hook_event


# Focus reminder - concise
FOCUS_REMINDER = "**CRITICAL**: Focus on the user's specific request. Do NOT over-elaborate or add unrequested features. Complete the task, then stop."

# Framing version for A/B measurement
FRAMING_VERSION = "v4-llm-first"

# Generic skill suggestion framing - high-level, appeals to agent's desire for quality
SKILL_FRAMING = (
    "You are operating in a sensitive academic environment that requires rigor. "
    "Before proceeding, invoke {skill_instruction} to load context that may not be immediately apparent."
)

# Only match explicit slash commands at start of prompt
SLASH_COMMAND_PATTERN = re.compile(r"^/(\w+)")

# Paths
TEMP_DIR = Path.home() / ".cache" / "aops" / "prompt-router"
INTENT_ROUTER_PROMPT = Path(__file__).parent / "prompts" / "intent-router.md"
CAPABILITIES_FILE = Path(__file__).parent.parent / "config" / "capabilities.md"

# Cache for capabilities content
_capabilities_cache: str | None = None


def load_capabilities_text() -> str:
    """Load capabilities markdown content (stripped of frontmatter)."""
    global _capabilities_cache
    if _capabilities_cache is not None:
        return _capabilities_cache

    content = CAPABILITIES_FILE.read_text()
    # Strip frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    _capabilities_cache = content
    return content


def get_command_names() -> set[str]:
    """Extract command names from capabilities file for slash command matching."""
    content = CAPABILITIES_FILE.read_text()
    commands = set()
    in_commands = False
    for line in content.split("\n"):
        if line.startswith("## Commands"):
            in_commands = True
        elif line.startswith("## ") and in_commands:
            break
        elif in_commands and line.startswith("|") and " | " in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if parts and parts[0] and parts[0].lower() != "name" and not parts[0].startswith("-"):
                commands.add(parts[0])
    return commands


def write_classifier_prompt(prompt: str) -> Path:
    """Write full classifier prompt to temp file.

    Loads the intent-router prompt template and fills in capabilities + user prompt.

    Args:
        prompt: The user's prompt text

    Returns:
        Path to the prompt file
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Load template
    template = INTENT_ROUTER_PROMPT.read_text()
    # Strip frontmatter
    if template.startswith("---"):
        parts = template.split("---", 2)
        if len(parts) >= 3:
            template = parts[2].strip()

    # Load capabilities as raw text
    capabilities_text = load_capabilities_text()

    # Fill template
    full_prompt = template.format(capabilities=capabilities_text, prompt=prompt)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = TEMP_DIR / f"{timestamp}.md"
    filepath.write_text(full_prompt)
    return filepath


def analyze_prompt(prompt: str) -> tuple[str, list[str]]:
    """Analyze prompt and route to appropriate capability.

    Two-tier routing:
    1. Explicit slash command → direct route
    2. Everything else → LLM classifier

    Args:
        prompt: The user's prompt text

    Returns:
        Tuple of (suggestion text, list of matched capability names)
    """
    if not prompt:
        return "", []

    # Tier 1: Explicit slash command at start of prompt → direct route
    match = SLASH_COMMAND_PATTERN.match(prompt)
    if match:
        cmd = match.group(1)
        if cmd in get_command_names():
            skill_instruction = f"Skill(skill=\"{cmd}\")"
            return SKILL_FRAMING.format(skill_instruction=skill_instruction), [f"/{cmd}"]

    # Tier 2: Everything else → LLM classifier with full capabilities
    filepath = write_classifier_prompt(prompt)
    classifier_instruction = (
        f"Task(subagent_type=\"intent-router\", prompt=\"Read {filepath}\")"
    )
    return SKILL_FRAMING.format(skill_instruction=classifier_instruction), []


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
