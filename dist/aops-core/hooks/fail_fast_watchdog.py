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

import json
import sys
from pathlib import Path
from typing import Any

# Add framework lib to path for template_loader
HOOK_DIR = Path(__file__).parent
AOPS_CORE_ROOT = HOOK_DIR.parent
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.template_loader import load_template

# Template path
FAIL_FAST_TEMPLATE = HOOK_DIR / "templates" / "fail-fast-reminder.md"

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

def load_fail_fast_reminder() -> str:
    """Load the fail-fast reminder message from template."""
    return load_template(FAIL_FAST_TEMPLATE)


def contains_error(text: str) -> bool:
    """Check if text contains error indicators."""
    if not text:
        return False
    return any(indicator in text for indicator in ERROR_INDICATORS)


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Log JSON parse error - likely empty stdin or malformed input
        print(f"WARNING: JSON parse failed: {e}", file=sys.stderr)
    except Exception as e:
        # Log unexpected errors during stdin read
        print(f"ERROR: Failed to read stdin: {type(e).__name__}: {e}", file=sys.stderr)

    if "hook_event_name" not in input_data:
        raise ValueError("input_data requires 'hook_event_name' parameter (P#8: fail-fast)")
    hook_event = input_data["hook_event_name"]

    # Only process PostToolUse events
    if hook_event != "PostToolUse":
        print(json.dumps({}))
        sys.exit(0)

    # Check tool response for errors
    # Note: The field is tool_response, not tool_result
    # For Bash: {stdout, stderr, ...}
    # For other tools: varies
    if "tool_response" not in input_data:
        raise ValueError("input_data requires 'tool_response' parameter for PostToolUse (P#8: fail-fast)")
    tool_response = input_data["tool_response"]
    if "tool_name" not in input_data:
        raise ValueError("input_data requires 'tool_name' parameter (P#8: fail-fast)")
    tool_name = input_data["tool_name"]

    # Determine if this is an error based on tool type
    is_error = False

    if isinstance(tool_response, dict):
        if tool_name == "Bash":
            # For Bash: check stderr (not stdout - stdout may contain code with "error" strings)
            stderr = tool_response.get("stderr")
            if stderr is not None and isinstance(stderr, str) and contains_error(stderr):
                is_error = True
        else:
            # For other tools: check if there's an explicit error field or type
            if tool_response.get("type") == "error":
                is_error = True
            elif tool_response.get("error"):
                is_error = True
            # For MCP tools, errors often have specific patterns
            elif isinstance(tool_response.get("content"), str):
                content = tool_response.get("content")
                if content is not None:
                    # Only check if it looks like an error message, not code
                    if contains_error(content) and len(content) < 500:
                        is_error = True

    # Handle MCP tool responses which are arrays: [{type: "text", text: "..."}]
    elif isinstance(tool_response, list):
        for item in tool_response:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                # Check for error patterns in short messages (not code/docs)
                if text is not None and isinstance(text, str) and len(text) < 500 and contains_error(text):
                    is_error = True
                    break

    # If error detected, inject reminder
    if is_error:
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "additionalContext": load_fail_fast_reminder(),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # No error, no action needed
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
