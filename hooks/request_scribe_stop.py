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

Special case (Issue #188):
- If last assistant message contains AskUserQuestion, suppress reminder
- Agent is waiting for user input, not completing work

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


def has_recent_ask_user_question(transcript_path: str, max_messages: int = 2) -> bool:
    """
    Check if last N assistant messages contain AskUserQuestion tool use.

    Args:
        transcript_path: Path to session transcript JSONL file
        max_messages: Maximum number of recent assistant messages to check

    Returns:
        True if AskUserQuestion found in recent messages, False otherwise
    """
    try:
        if not Path(transcript_path).exists():
            return False

        assistant_messages = []

        # Read transcript file (JSONL format - one JSON object per line)
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Look for assistant messages
                    if entry.get("type") == "assistant":
                        assistant_messages.append(entry)

                except json.JSONDecodeError:
                    continue

        # Check last N assistant messages
        recent_messages = assistant_messages[-max_messages:] if assistant_messages else []

        for msg in recent_messages:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("name") == "AskUserQuestion":
                            return True

        return False

    except Exception:
        # On error, fail open (don't suppress reminder)
        return False


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
    transcript_path = input_data.get("transcript_path", "")
    state_file = get_state_file(session_id)

    # Special case (Issue #188): Agent asked user a question, waiting for response
    # Suppress reminder to prevent misinterpretation
    if has_recent_ask_user_question(transcript_path):
        output: dict[str, Any] = {}
        safe_log_to_debug_file("Stop/SubagentStop (AskUserQuestion)", input_data, output)
        print(json.dumps(output))
        sys.exit(0)

    # Check if end-of-session subagent already requested this turn
    if state_file.exists():
        # Second/third stop - end-of-session subagent was invoked, now allow stop
        # (Can be SubagentStop when subagent finishes, then Stop when returning to main)
        output = {}
        safe_log_to_debug_file("Stop/SubagentStop", input_data, output)
        print(json.dumps(output))
        sys.exit(0)

    # First stop - block and request end-of-session subagent invocation
    state_file.touch()

    output = {
        "decision": "block",
        "reason": "If this marks the end of a substantial chunk of work (not during interactive conversation with user), please invoke the end-of-session agent to handle commits, context capture, and task updates. Provide a brief description of what was accomplished and the state (e.g., 'completed', 'in-progress', 'blocked', 'aborted', 'planned', 'failed'). Use: Task(subagent_type='end-of-session', prompt='[Brief work description]', description='[work description and state]')"
    }

    safe_log_to_debug_file("Stop", input_data, output)
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
