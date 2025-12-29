#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Spawns the intent-router agent to transform user prompts into
structured work instructions with appropriate skills and steps.

The intent-router agent has its own tools (Read, Glob, memory search)
and uses judgment to determine what's needed for each situation.

Slash commands are handled by Claude Code directly - we skip them.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import re
import sys
from typing import Any

from hooks.hook_logger import log_hook_event

# Framing version for measurement
FRAMING_VERSION = "v8-smart-router"

# Slash command pattern
SLASH_COMMAND_PATTERN = re.compile(r"^/(\w+)")


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

    # Spawn intent-router agent with user prompt
    # The agent has tools and smarts to figure out what's needed
    escaped_prompt = prompt.replace('"', '\\"').replace("\n", "\\n")
    additional_context = f"""**ROUTE FIRST**: Spawn the intent-router to get structured guidance for this task.

Task(subagent_type="intent-router", model="haiku", prompt="{escaped_prompt}")

Follow the router's structured output - it provides tailored steps, skill to invoke, and DO NOTs."""

    hook_output: dict[str, Any] = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": additional_context,
        "framingVersion": FRAMING_VERSION,
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
