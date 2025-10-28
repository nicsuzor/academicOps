#!/usr/bin/env python3
"""
Stop/SubagentStop hook that requests scribe invocation on first stop, allows on second.

This hook blocks the first Stop event after completing work and instructs Claude
to invoke the scribe skill for context extraction. On the second Stop (after
scribe completes), it allows the stop to proceed.

Prevents infinite loop by:
1. Tracking state in /tmp/claude_scribe_requested_{session_id}.flag
2. UserPromptSubmit hook cleans up state on new user interaction
3. First stop → Block with "invoke scribe"
4. Second stop (after scribe) → Allow stop

Exit codes:
    0: Success (allow stop or block with instruction)
"""

import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file


def get_state_file(session_id: str) -> Path:
    """Get path to state file tracking scribe invocation for this session."""
    return Path(f"/tmp/claude_scribe_requested_{session_id}.flag")


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

    # Check if scribe already requested this turn
    if state_file.exists():
        # Second stop - scribe was invoked, now allow stop
        output: dict[str, Any] = {}
        safe_log_to_debug_file("Stop", input_data, output)
        print(json.dumps(output))
        sys.exit(0)

    # First stop - block and request scribe invocation
    state_file.touch()

    output = {
        "decision": "block",
        "reason": "Please invoke the scribe skill to capture context about what was just accomplished before stopping. Use: Skill(command='scribe')"
    }

    safe_log_to_debug_file("Stop", input_data, output)
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
