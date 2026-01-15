#!/usr/bin/env python3
"""
PreToolUse hook: Block or warn when prompt-hydrator hasn't been invoked.

The hydration gate ensures agents invoke the prompt-hydrator subagent before
proceeding with work. This is a mechanical trigger enforcing the v1.0 core loop.

Gate logic:
1. UserPromptSubmit sets hydration_pending=True (unless prompt starts with / or .)
2. PreToolUse checks hydration_pending flag
3. If pending:
   - WARN mode: Log warning, allow (exit 0)
   - BLOCK mode: Block all tools except Task(prompt-hydrator) (exit 2)
4. When Task tool is used with subagent_type="prompt-hydrator", the gate clears

Bypass conditions (gate always allows):
- Subagent sessions (CLAUDE_AGENT_TYPE environment variable set)
- First prompt from CLI (no session state exists yet)
- Task invocations spawning prompt-hydrator
- User bypass prefixes ('.' and '/' handled by UserPromptSubmit setting hydration_pending=False)

Environment variables:
- HYDRATION_GATE_MODE: "warn" (default) or "block"
- CLAUDE_AGENT_TYPE: If set, this is a subagent session (bypass gate)

Exit codes:
    0: Allow (hydration complete, bypassed, or warn mode)
    2: Block (hydration pending in block mode)

Failure mode: FAIL-OPEN (allow on error - don't break normal operation)
"""

import json
import os
import sys
from typing import Any

from lib.session_state import clear_hydration_pending, is_hydration_pending

# Gate mode from environment
GATE_MODE = os.environ.get("HYDRATION_GATE_MODE", "warn").lower()

# Message shown when blocking/warning
BLOCK_MESSAGE = """⛔ HYDRATION GATE: Invoke prompt-hydrator before proceeding.

**MANDATORY**: Spawn the hydrator subagent FIRST:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate user request",
     prompt="<path from UserPromptSubmit hook>")
```

The hydrator provides workflow guidance, context, and guardrails. Follow its output before continuing.

**Override**: If hydrator fails, user can prefix next prompt with `.` to bypass, or use `/` for slash commands.
"""

WARN_MESSAGE = """⚠️  HYDRATION GATE (warn-only): Hydrator not invoked yet.

This session is in WARN mode for testing. In production, this would BLOCK all tools.

To proceed correctly, spawn the hydrator subagent:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate user request",
     prompt="<path from UserPromptSubmit hook>")
```
"""


def get_session_id(input_data: dict[str, Any]) -> str:
    """Get session ID from hook input data or environment.

    Args:
        input_data: Hook input data dict

    Returns:
        Session ID string, or empty string if not found
    """
    return input_data.get("session_id", "") or os.environ.get("CLAUDE_SESSION_ID", "")


def is_subagent_session() -> bool:
    """Check if this is a subagent session.

    Returns:
        True if CLAUDE_AGENT_TYPE is set (indicating subagent context)
    """
    return bool(os.environ.get("CLAUDE_AGENT_TYPE"))


def is_first_prompt_from_cli(session_id: str) -> bool:
    """Check if this is the first prompt from CLI (no session state exists).

    Args:
        session_id: Claude Code session ID

    Returns:
        True if no session state file exists (first interaction)
    """
    if not session_id:
        return False

    from lib.session_state import load_session_state

    # If no session state exists, this is the first prompt
    state = load_session_state(session_id)
    return state is None


def is_hydrator_task(tool_input: dict[str, Any]) -> bool:
    """Check if this Task invocation is spawning prompt-hydrator.

    Args:
        tool_input: The tool input parameters

    Returns:
        True if this is a Task call with subagent_type="prompt-hydrator"
    """
    subagent_type = tool_input.get("subagent_type", "")
    return subagent_type == "prompt-hydrator"


def main():
    """Main hook entry point - checks hydration status and blocks/warns if needed."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # FAIL-OPEN: allow on parse error (don't break normal operation)
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    session_id = get_session_id(input_data)

    # FAIL-OPEN: if no session_id, allow (don't break edge cases)
    if not session_id:
        print(json.dumps({}))
        sys.exit(0)

    # BYPASS: Subagent sessions (invoked by main agent)
    if is_subagent_session():
        print(json.dumps({}))
        sys.exit(0)

    # BYPASS: First prompt from CLI (no state exists yet)
    if is_first_prompt_from_cli(session_id):
        print(json.dumps({}))
        sys.exit(0)

    # Check if hydration is pending
    if not is_hydration_pending(session_id):
        # Hydration complete or not required - allow all tools
        print(json.dumps({}))
        sys.exit(0)

    # Hydration is pending - check if this is the hydrator being invoked
    if tool_name == "Task" and is_hydrator_task(tool_input):
        # This is the hydrator being spawned - clear the gate and allow
        clear_hydration_pending(session_id)
        print(json.dumps({}))
        sys.exit(0)

    # Hydration pending - enforce based on mode
    if GATE_MODE == "block":
        # Block mode: exit 2 to block the tool
        print(BLOCK_MESSAGE, file=sys.stderr)
        sys.exit(2)
    else:
        # Warn mode (default): log warning but allow (exit 0)
        print(WARN_MESSAGE, file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
