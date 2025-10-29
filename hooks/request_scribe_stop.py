#!/usr/bin/env python3
"""
Stop/SubagentStop hook that requests end-of-session subagent on first stop, allows on second.

This hook blocks the first Stop/SubagentStop event after completing work and instructs
Claude to invoke the end-of-session subagent which handles: commits, scribe, task updates.

Prevents infinite loop by:
1. Tracking state in /tmp/claude_end_of_session_requested_{session_id}.flag
2. UserPromptSubmit hook cleans up state on new user interaction
3. First stop → Block with "invoke end-of-session subagent"
4. SubagentStop (after subagent finishes) → Flag exists → Allow
5. Stop (when returning to main agent) → Flag exists → Allow

Used by both Stop and SubagentStop hooks with identical logic.

Exit codes:
    0: Success (allow stop or block with instruction)
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
    state_file = get_state_file(session_id)

    # Check if end-of-session subagent already requested this turn
    if state_file.exists():
        # Second/third stop - end-of-session subagent was invoked, now allow stop
        # (Can be SubagentStop when subagent finishes, then Stop when returning to main)
        output: dict[str, Any] = {}
        safe_log_to_debug_file("Stop/SubagentStop", input_data, output)
        print(json.dumps(output))
        sys.exit(0)

    # First stop - block and request end-of-session subagent invocation
    state_file.touch()

    output = {
        "decision": "block",
        "reason": "If this marks the end of a substantial chunk of work, please invoke the end-of-session agent to handle commits, context capture, and task updates. Use: Task(subagent_type='end-of-session', prompt='Run end-of-session workflow', description='End of session workflow')"
    }

    safe_log_to_debug_file("Stop", input_data, output)
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
