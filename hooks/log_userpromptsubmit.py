#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code: Minimal logging.

Logs UserPromptSubmit events to data/sessions/<date>-<hash>-hooks.jsonl
Also loads additional context from prompts/user-prompt-submit.md

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lib.paths import get_hooks_dir
from hooks.hook_logger import log_hook_event

# Paths
HOOK_DIR = get_hooks_dir()
PROMPT_FILE = HOOK_DIR / "prompts" / "user-prompt-submit.md"


def load_prompt_from_markdown() -> str:
    """Load prompt content from markdown file."""
    if not PROMPT_FILE.exists():
        return ""

    content = PROMPT_FILE.read_text().strip()
    if not content:
        return ""

    # Remove markdown header if present
    lines = content.split("\n")
    if lines and lines[0].startswith("#"):
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
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")

    # Clear end-of-session documentation request flag for new turn
    state_file = Path.home() / ".cache" / "aops" / f"session_end_{session_id}.flag"
    if state_file.exists():
        state_file.unlink()

    # Load additional context
    additional_context = load_prompt_from_markdown()
    output_data: dict[str, Any] = {}
    log_output: dict[str, Any] = {}
    if additional_context:
        # Output sent to Claude (no file metadata)
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context
            }
        }
        # Log output includes file metadata
        log_output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context,
                "filesLoaded": [str(PROMPT_FILE)]
            }
        }

    # Log hook event with both input and output (includes file metadata)
    log_hook_event(session_id, "UserPromptSubmit", input_data, log_output, exit_code=0)

    # Output JSON (continue execution) - without file metadata
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
