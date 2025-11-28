#!/usr/bin/env python3
"""
Stop/SubagentStop/PostToolUse(TodoWrite) hook requesting end-of-session documentation.

This hook blocks execution on first trigger to request agent invoke session
documentation workflow, then allows on subsequent triggers to prevent loops.

Triggered on:
- Stop/SubagentStop events (agent pausing)
- PostToolUse for TodoWrite (objectives captured, document outcomes)

Uses state flag to track whether documentation was requested this turn.
Flag is cleared by UserPromptSubmit hook for next turn.

Exit codes:
    0: Success (either blocked with request or allowed)
"""

import json
import sys
from pathlib import Path
from typing import Any


def get_state_file(session_id: str) -> Path:
    """Get path to state file tracking documentation request for this session."""
    cache_dir = Path.home() / ".cache" / "aops"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"session_end_{session_id}.flag"


def main():
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except json.JSONDecodeError:
        # On error, allow execution (fail-safe)
        print(json.dumps({}))
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    hook_event = input_data.get("hook_event", "Unknown")
    state_file = get_state_file(session_id)

    # Check if we already requested documentation this turn
    if state_file.exists():
        # Second+ trigger: Allow execution (documentation already requested)
        output: dict[str, Any] = {}
        print(json.dumps(output))
        print(
            f"✓ {hook_event} allowed (documentation already requested)",
            file=sys.stderr,
        )
        sys.exit(0)

    # First trigger: Block and request documentation
    # Create state flag to prevent loop
    state_file.touch()

    # Different messages based on hook event
    hook_event = input_data.get("hook_event", "Unknown")

    if hook_event == "PostToolUse" and input_data.get("tool_name") == "TodoWrite":
        # TodoWrite: Document planned work
        reason = (
            "[AOPS Framework Reminder: You just updated the todo list. "
            "Consider documenting to bmem: (1) what you plan to work on next, "
            "(2) any decisions made about approach or priorities.]"
        )
    else:
        # Stop/SubagentStop: Document completed work
        reason = (
            "[AOPS Framework Reminder: If this marks the end of a substantial chunk of work "
            "(not during interactive conversation), use the bmem skill to document key decisions and outcomes.]"
        )

    output = {
        "decision": "block",
        "reason": reason,
    }

    print(json.dumps(output))
    print(
        f"⏸️  {hook_event} blocked: Requesting end-of-session documentation",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
