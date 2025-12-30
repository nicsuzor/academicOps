#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Returns noop ({}) to allow hook chain to continue.

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
PROMPT_FILE = HOOK_DIR / "prompts" / "user-prompt-submit.md"


def load_prompt_from_markdown() -> str:
    """
    Load prompt content from markdown file.

    Returns:
        Prompt content as string (stripped of markdown formatting)

    Raises:
        FileNotFoundError: If prompt file doesn't exist (fail-fast, no defaults)
    """
    # Fail-fast: no defaults, no fallbacks
    if not PROMPT_FILE.exists():
        msg = (
            f"FATAL: Prompt file missing at {PROMPT_FILE}. "
            "UserPromptSubmit hook requires this file to exist. "
            "No defaults or fallbacks allowed (AXIOM #5: Fail-Fast)."
        )
        raise FileNotFoundError(msg)

    # Read markdown file
    content = PROMPT_FILE.read_text().strip()

    # Basic validation
    if not content:
        msg = f"FATAL: Prompt file at {PROMPT_FILE} is empty."
        raise ValueError(msg)

    # Remove markdown header if present (first line starting with #)
    lines = content.split("\n")
    if lines and lines[0].startswith("#"):
        # Skip header and any following blank lines
        content_lines = []
        skip_header = True
        for line in lines[1:]:
            if skip_header and line.strip() == "":
                continue
            skip_header = False
            content_lines.append(line)
        content = "\n".join(content_lines).strip()

    return content


def main():
    """Main hook entry point (noop return)."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Build output data (noop - no additional context)
    output_data: dict[str, Any] = {}

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output JSON (noop - allows hook chain to continue)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
