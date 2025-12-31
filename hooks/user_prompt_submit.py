#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Injects prompt-hydrator instruction to enrich every prompt with context
and workflow guidance.

Exit codes:
    0: Success (always continues)
"""

import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file

# Paths (absolute, fail-fast if missing)
HOOK_DIR = Path(__file__).parent


def build_hydration_instruction(prompt: str) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Args:
        prompt: The user's original prompt

    Returns:
        Instruction string to inject into agent context
    """
    # Truncate prompt for description (avoid huge strings)
    prompt_preview = prompt[:80].replace("\n", " ").strip()
    if len(prompt) > 80:
        prompt_preview += "..."

    # Escape quotes in prompt for embedding
    escaped_prompt = prompt.replace('"', '\\"').replace("\n", "\\n")

    instruction = f"""**FIRST**: Before responding to this prompt, invoke the prompt-hydrator agent to get workflow guidance:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Analyze and hydrate this user prompt:\\n\\n{escaped_prompt}")
```

Wait for hydrator output, then follow the workflow guidance it returns. The hydrator will tell you:
- Which workflow dimensions apply (gate, pre-work, approach)
- Which skill(s) to invoke
- Which guardrails are active
- Relevant context from memory and codebase

**Do NOT skip this step.** The hydrator ensures you have the right context and approach before starting work."""

    return instruction


def main():
    """Main hook entry point - injects hydration instruction."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Extract user prompt
    prompt = input_data.get("prompt", "")

    # Build hydration instruction
    if prompt:
        hydration_instruction = build_hydration_instruction(prompt)
    else:
        hydration_instruction = ""

    # Build output with hydration context
    output_data: dict[str, Any] = {}
    if hydration_instruction:
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": hydration_instruction,
            }
        }

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output JSON
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
