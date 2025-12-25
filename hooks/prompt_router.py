#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Combines intent classifier prompt + user prompt into temp file.
Tells main agent to invoke intent-router subagent with that file path.

The intent-router (Haiku) enforces framework rules by providing
focused, task-specific guidance to the main agent.

Slash commands are handled by Claude Code directly - we skip them.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from hooks.hook_logger import log_hook_event

# Framing version for measurement
FRAMING_VERSION = "v7-subagent-router"

# Slash command pattern
SLASH_COMMAND_PATTERN = re.compile(r"^/(\w+)")

# Path to intent router prompt
AOPS = Path(os.environ.get("AOPS", Path(__file__).parent.parent))
INTENT_ROUTER_PROMPT = AOPS / "hooks" / "prompts" / "intent-router.md"


def load_router_prompt() -> str:
    """Load intent router prompt, stripped of frontmatter."""
    if not INTENT_ROUTER_PROMPT.exists():
        return ""

    content = INTENT_ROUTER_PROMPT.read_text()

    # Strip frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    return content


def build_router_context(user_prompt: str) -> str:
    """Build context for intent router: prompt template + user's prompt."""
    router_prompt = load_router_prompt()

    # Replace {prompt} placeholder with actual user prompt
    if "{prompt}" in router_prompt:
        return router_prompt.replace("{prompt}", user_prompt)

    # Fallback: append user prompt
    return f"{router_prompt}\n\n## User Prompt\n\n{user_prompt}"


def write_temp_file(content: str) -> str:
    """Write content to temp file, return path."""
    fd, path = tempfile.mkstemp(prefix="intent_router_", suffix=".md")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def analyze_prompt(prompt: str) -> tuple[str, list[str]]:
    """Analyze prompt and determine routing. Exported for testing."""
    if not prompt:
        return "", []

    if SLASH_COMMAND_PATTERN.match(prompt):
        return "", []

    return "ROUTE_REQUIRED", []


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    prompt = input_data.get("prompt", "")

    # Slash commands - Claude Code handles, we skip
    if prompt and SLASH_COMMAND_PATTERN.match(prompt):
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",
                "framingVersion": FRAMING_VERSION,
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Build context and write to temp file
    context = build_router_context(prompt)
    temp_path = write_temp_file(context)

    # Instruct main agent to invoke router with file path
    additional_context = f"""**ROUTE FIRST**: Invoke the intent router before proceeding:

Task(subagent_type="intent-router", model="haiku", prompt="Read {temp_path} and return guidance")

Follow the router's output."""

    hook_output: dict[str, Any] = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": additional_context,
        "framingVersion": FRAMING_VERSION,
        "routerContextFile": temp_path,
    }

    output = {"hookSpecificOutput": hook_output}

    # Log
    session_id = input_data.get("session_id", "unknown")
    log_hook_event(
        session_id=session_id,
        hook_event="UserPromptSubmit",
        input_data=input_data,
        output_data=output,
        exit_code=0,
    )

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
