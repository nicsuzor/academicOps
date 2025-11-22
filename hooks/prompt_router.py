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
    instruction = f"""BEFORE responding to the user's prompt, spawn a Haiku subagent to classify intent:

Use Task tool with:
- subagent_type: "haiku"
- model: "haiku"
- prompt: Read {temp_file} and classify the user's intent. Return JSON with:
  - intent: one of framework/python/analysis/knowledge/task/other
  - recommended_skills: list of skill names that would help
  - reasoning: brief explanation

Then incorporate the skill recommendations into your response approach."""

    output = {"additionalContext": instruction}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
