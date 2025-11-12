#!/usr/bin/env python3
"""
Session Stop hook for logging session activity.

This hook captures session information and logs it to daily JSONL files in
./data/sessions/<date>-<shorthash>.jsonl

Exit codes:
    0: Success (always allows stop)
"""

import json
import sys
from pathlib import Path

from lib.paths import get_data_root
from hooks.session_logger import write_session_log


def get_project_dir() -> Path:
    """Get the data directory for session logs.

    In the new architecture, sessions are stored in $ACA_DATA regardless of cwd.
    """
    return get_data_root()


def main() -> int:
    """Main hook entry point."""

    try:
        # Read input from stdin
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            # If no valid input, just allow stop
            print("{}")
            return 0

        # Extract session info
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path")

        # Get project directory
        project_dir = get_project_dir()

        # Write session log
        log_path = write_session_log(
            project_dir=project_dir,
            session_id=session_id,
            transcript_path=transcript_path,
        )

        # Always allow stop (return empty JSON)
        print("{}")

        # Optionally print to stderr for user visibility
        # Uncomment if you want to see session logging confirmations
        # print(f"✓ Session logged to {log_path}", file=sys.stderr)

        return 0

    except Exception as e:
        # Always return success to prevent blocking stop
        print("{}")
        print(f"Warning: Session logging hook error: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Ultimate safeguard - never block stop
        print("{}")
        sys.exit(0)
