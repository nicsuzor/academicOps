#!/usr/bin/env python3
"""
PostToolUse/Stop hook: Remind agent to document work to memory server.

Triggers on:
- PostToolUse (TodoWrite matcher) - after task list updates
- Stop - at end of session

Reads reminder message from hooks/templates/memory-reminder.md.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from hooks.hook_logger import log_hook_event


def get_reminder_message() -> str:
    """Load reminder message from template file."""
    aops_root = Path(os.environ.get("AOPS", ""))
    template_path = aops_root / "hooks" / "templates" / "memory-reminder.md"

    if template_path.exists():
        return template_path.read_text().strip()

    # Raise if template not found
    raise FileNotFoundError(
        "Memory reminder template not found at: " + str(template_path)
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
        output: dict[str, Any] = {"reason": message, "continue": True}
        print(json.dumps(output))
        sys.exit(0)  # Advisory message only - don't affect CLI exit code

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
            "additionalContext": message,
        }
    }

    # Log to hooks JSONL for transcript visibility
    session_id = input_data.get("session_id", "")
    if session_id:
        log_hook_event(
            session_id=session_id,
            hook_event=hook_event,
            input_data=input_data,
            output_data=output,
            exit_code=0,
        )

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
