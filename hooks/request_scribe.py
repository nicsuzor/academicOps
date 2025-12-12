#!/usr/bin/env python3
"""
PostToolUse/Stop hook: Remind agent to document work to bmem.

Triggers on:
- PostToolUse (TodoWrite matcher) - after task list updates
- Stop - at end of session

Reads reminder message from hooks/prompts/bmem-reminder.md.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def get_reminder_message() -> str:
    """Load reminder message from template file."""
    aops_root = Path(os.environ.get("AOPS", ""))
    template_path = aops_root / "hooks" / "prompts" / "bmem-reminder.md"

    if template_path.exists():
        return template_path.read_text().strip()

    # Fallback if template not found
    return (
        "[AOPS Framework Reminder: If this marks the end of a substantial chunk of work, "
        "use the bmem skill to document key decisions and outcomes.]"
    )


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    # Determine hook event type (Claude Code uses snake_case for input)
    hook_event = input_data.get("hook_event_name", "")

    # Stop hooks use different output format (no hookSpecificOutput)
    if hook_event == "Stop":
        message = get_reminder_message()
        output: dict[str, Any] = {
            "reason": message,
            "continue": True
        }
        print(json.dumps(output))
        sys.exit(1)  # 1 = warn but allow

    # For PostToolUse, only trigger on TodoWrite
    if hook_event == "PostToolUse":
        tool_name = input_data.get("tool_name", "")
        if tool_name != "TodoWrite":
            print(json.dumps({}))
            sys.exit(0)

    # Inject reminder message (only for PostToolUse)
    message = get_reminder_message()

    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": hook_event,
            "additionalContext": message
        }
    }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
