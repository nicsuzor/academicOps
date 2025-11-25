#!/usr/bin/env python3
"""
PostToolUse hook for Claude Code: Minimal logging.

Logs PostToolUse events to data/sessions/<date>-<hash>-hooks.jsonl

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import UTC, datetime
from typing import Any

from hooks.hook_logger import log_hook_event


def main():
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")

    # Noop output - just continue
    output_data: dict[str, Any] = {}

    # Log to hooks session file (includes both input and output)
    log_hook_event(session_id, "PostToolUse", input_data, output_data)

    # Output empty JSON (continue execution)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
