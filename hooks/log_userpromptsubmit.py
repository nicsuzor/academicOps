#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code: Debug logging and scribe state cleanup.

This hook logs all UserPromptSubmit events and cleans up the scribe invocation
state flag from the previous turn, allowing the Stop hook to request scribe
again on the next stop.

Exit codes:
    0: Success (always continues)
"""

import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file


def cleanup_scribe_state(session_id: str) -> None:
    """Remove scribe invocation flag at start of new user turn."""
    state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
    if state_file.exists():
        state_file.unlink()


def main():
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    session_id = input_data.get("session_id", "unknown")

    # Clean up scribe state from previous turn
    cleanup_scribe_state(session_id)

    # Add Axiom #1 reminder (Issue #145)
    output_data: dict[str, Any] = {
        "additionalContext": (
            "**AXIOM #1 REMINDER**: Do ONE thing in response to this prompt, then STOP and return. "
            "If user is correcting you: Is this steering (incorporate and continue) or course change "
            "(clear todo list, make new plan for the ONE new thing requested)?"
        )
    }

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output empty JSON (continue execution)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
