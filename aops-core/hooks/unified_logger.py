#!/usr/bin/env python3
"""
Unified hook logger for Claude Code.

Handles ALL hook events with pure logging - no context injection, no policy enforcement.
Uses hook_logger.log_hook_event() for centralized logging.

Exit codes:
    0: Success (always continues with noop response)
"""

import contextlib
import json
import sys
from typing import Any

from hooks.hook_logger import log_hook_event


def main():
    """Main hook entry point - logs event and returns noop."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")
    hook_event = input_data.get("hook_event_name", "Unknown")

    # Log the event
    log_hook_event(session_id, hook_event, input_data, output_data=None, exit_code=0)

    # Noop response - continue without modification
    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    main()
