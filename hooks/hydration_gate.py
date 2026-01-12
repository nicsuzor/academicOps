#!/usr/bin/env python3
"""
PreToolUse hook: Block ALL tools until prompt-hydrator is invoked.

The hydration gate ensures agents invoke the prompt-hydrator subagent before
proceeding with any work. This is a mechanical trigger that cannot be bypassed
by the agent (unlike instructions which can be ignored).

Gate logic:
1. UserPromptSubmit sets hydration_pending=True (unless prompt starts with / or .)
2. PreToolUse blocks ALL tools while hydration_pending=True
3. When Task tool is used with subagent_type="prompt-hydrator", the gate clears
4. Agent cannot write to session state files directly (deny rule)

Exit codes:
    0: Allow (hydration complete or Task(prompt-hydrator) being invoked)
    2: Block (hydration pending, show reminder message)

Failure mode: FAIL-OPEN (allow on error - don't break normal operation)
"""

import json
import os
import sys
from typing import Any

from lib.session_state import clear_hydration_pending, is_hydration_pending

# Message shown when blocking
BLOCK_MESSAGE = """⛔ HYDRATION GATE: Invoke prompt-hydrator before proceeding.

**MANDATORY**: Spawn the hydrator subagent FIRST:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: [brief task summary]",
     prompt="Read /tmp/claude-hydrator/hydrate_XXX.md and provide workflow guidance.")
```

The hydrator provides workflow guidance, context, and guardrails. Follow its output before continuing.

**Override**: If hydrator fails, user can prefix next prompt with `.` to bypass.
"""


def get_session_id(input_data: dict[str, Any]) -> str:
    """Get session ID from hook input data or environment.

    Args:
        input_data: Hook input data dict

    Returns:
        Session ID string, or empty string if not found
    """
    return input_data.get("session_id", "") or os.environ.get("CLAUDE_SESSION_ID", "")


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

    # Block all other tools while hydration is pending
    print(BLOCK_MESSAGE, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
