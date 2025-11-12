#!/usr/bin/env python3
"""
Session Stop hook for logging session activity.

This hook captures session information and logs it to daily JSONL files in
./data/sessions/<date>-<shorthash>.jsonl

Exit codes:
    0: Success (always allows stop)
"""

import json
import os
import sys
from pathlib import Path

# Import the session logger module
sys.path.insert(0, str(Path(__file__).parent))
from session_logger import write_session_log


def get_project_dir() -> Path:
    """Get the project directory from environment or git root."""
    # Try environment variable first
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)

    # Fall back to git root (find .git directory)
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    # Last resort: use current directory
    return Path.cwd()


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
