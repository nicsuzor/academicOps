#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Minimal logging.

Logs PreToolUse events to data/sessions/<date>-<hash>-hooks.jsonl

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import UTC, datetime
from typing import Any

from lib.paths import get_data_root
from hooks.session_logger import get_log_path


def log_to_session_file(
    session_id: str, hook_event: str, input_data: dict[str, Any]
) -> None:
    """
    Append hook event to hooks log file.

    Args:
        session_id: Session ID
        hook_event: Name of the hook event
        input_data: Input data from Claude Code (complete data passed through)
    """
    try:
        # Get data directory for session logs
        project_dir = get_data_root()

        # Get log path with -hooks suffix
        log_path = get_log_path(project_dir, session_id, suffix="-hooks")

        # Create log entry with ALL input data plus our own timestamp if missing
        log_entry = {
            "hook_event": hook_event,
            "logged_at": datetime.now(UTC).isoformat(),
            **input_data,  # Include ALL fields from input
        }

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(log_entry, f, separators=(",", ":"))
            f.write("\n")
    except Exception:
        # Never crash the hook
        pass


def main():
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")

    # Log to hooks session file
    log_to_session_file(session_id, "PreToolUse", input_data)

    # Noop output - just continue
    output_data: dict[str, Any] = {}

    # Output empty JSON (continue execution)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
