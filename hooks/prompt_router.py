#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Captures prompt, writes to temp file, returns instruction to spawn
a Haiku subagent for intent classification.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from pathlib import Path
from typing import Any


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    prompt = input_data.get("prompt", "")
    session_id = input_data.get("session_id", "unknown")

    if not prompt:
        print("{}")
        sys.exit(0)

    # Write prompt to temp file for subagent to read
    temp_file = Path(f"/tmp/prompt_router_{session_id}.json")
    temp_file.write_text(json.dumps({"prompt": prompt}))

    # Return instruction to spawn classifier subagent
    instruction = f"""ROUTER_ACTIVE: Before responding, consider which skill would help most with this prompt.

Available skills: framework (hook/automation work), python-dev (Python code), analyst (data analysis), bmem (knowledge base).

Prompt saved to: {temp_file}

If this prompt clearly matches a skill domain, mention it in your response."""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": instruction
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
