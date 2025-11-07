#!/usr/bin/env python3
"""
Stop/SubagentStop hook for logging (reminder disabled per issue #188).

This hook logs stop events for debugging but does not block or show reminders.

Previously blocked to request end-of-session subagent, but the conditional reminder
"(not during interactive conversation with user)" caused agents to misinterpret and
self-answer instead of waiting for user input.

Exit codes:
    0: Success (allow stop with logging)
"""

import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file


def get_state_file(session_id: str) -> Path:
    """Get path to state file tracking end-of-session subagent invocation for this session."""
    return Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")


def main():
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except json.JSONDecodeError:
        # On error, allow stop (fail-safe)
        print(json.dumps({}))
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    get_state_file(session_id)

    # Disabled per issue #188 - conditional reminder was causing agents to self-answer
    # Keep logging for debugging but don't block
    output: dict[str, Any] = {}
    safe_log_to_debug_file("Stop/SubagentStop", input_data, output)
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
