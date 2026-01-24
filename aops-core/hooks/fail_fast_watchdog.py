#!/usr/bin/env python3
"""
PostToolUse hook: Fail-Fast Watchdog.

When a tool returns an error, reminds agent to report the error
and ask the user what to do - NOT investigate or fix infrastructure.

Implements AXIOMS #7-8 (Fail-Fast).

KNOWN LIMITATION: PostToolUse hooks don't fire for built-in tool errors
(Bash exit != 0, Read file-not-found, etc.). Claude Code bypasses PostToolUse
for these failures. However, this hook DOES work for MCP tools that return
errors in their response payload (e.g., missing config, API failures).

Exit codes:
    0: Success (always continues, may inject reminder)
"""

import contextlib
import json
import sys
from typing import Any


# Patterns that indicate a tool error
ERROR_INDICATORS = [
    "error",
    "Error",
    "ERROR",
    "failed",
    "Failed",
    "FAILED",
    "exception",
    "Exception",
    "not found",
    "Not found",
    "does not exist",
    "Does not exist",
    "Missing required",
    "missing required",
    "Permission denied",
    "permission denied",
    "timed out",
    "Timed out",
    "No such file",
    "cannot access",
    "Cannot access",
]

FAIL_FAST_REMINDER = """⚠️ FAIL-FAST REMINDER: This tool returned an error.

Per AXIOMS #7-8 (Fail-Fast):
- DO NOT investigate infrastructure or configuration
- DO NOT search for solutions or workarounds
- DO NOT try to fix the underlying problem

Instead:
- Report the error clearly to the user
- Ask what the user wants you to do

The user may want to fix it themselves, ask you to investigate, or try something else entirely. That's THEIR decision, not yours."""


def contains_error(text: str) -> bool:
    """Check if text contains error indicators."""
    if not text:
        return False
    return any(indicator in text for indicator in ERROR_INDICATORS)


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    hook_event = input_data.get("hook_event_name", "")

    # Only process PostToolUse events
    if hook_event != "PostToolUse":
        print(json.dumps({}))
        sys.exit(0)

    # Check tool response for errors
    # Note: The field is tool_response, not tool_result
    # For Bash: {stdout, stderr, ...}
    # For other tools: varies
    tool_response = input_data.get("tool_response", {})
    tool_name = input_data.get("tool_name", "")

    # Determine if this is an error based on tool type
    is_error = False

    if isinstance(tool_response, dict):
        if tool_name == "Bash":
            # For Bash: check stderr (not stdout - stdout may contain code with "error" strings)
            stderr = tool_response.get("stderr", "")
            if stderr and contains_error(stderr):
                is_error = True
        else:
            # For other tools: check if there's an explicit error field or type
            if tool_response.get("type") == "error":
                is_error = True
            elif tool_response.get("error"):
                is_error = True
            # For MCP tools, errors often have specific patterns
            elif isinstance(tool_response.get("content"), str):
                content = tool_response.get("content", "")
                # Only check if it looks like an error message, not code
                if contains_error(content) and len(content) < 500:
                    is_error = True

    # Handle MCP tool responses which are arrays: [{type: "text", text: "..."}]
    elif isinstance(tool_response, list):
        for item in tool_response:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                # Check for error patterns in short messages (not code/docs)
                if text and len(text) < 500 and contains_error(text):
                    is_error = True
                    break

    # If error detected, inject reminder
    if is_error:
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "additionalContext": FAIL_FAST_REMINDER,
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # No error, no action needed
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
