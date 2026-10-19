#!/usr/bin/env python3
"""Claude Code PreToolUse hook for injecting caller session into MCP calls.

Matching `mcp__.*` tool calls, this hook injects a reserved `_session` object
({session_id, agent_id, prompt_id}) into `hookSpecificOutput.updatedInput`,
preserving all original tool arguments.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def inject_caller_session(raw: dict[str, Any]) -> dict[str, Any]:
    """Inject `_session` into tool input if applicable.

    Stdin carries `session_id`, `prompt_id` and `tool_use_id`, plus `agent_id`
    inside subagents.
    """
    tool_name = raw.get("tool_name", "")
    if tool_name and not tool_name.startswith("mcp__"):
        return {}

    tool_input = raw.get("tool_input")
    if isinstance(tool_input, dict):
        updated_input = dict(tool_input)
    else:
        updated_input = {}

    session: dict[str, Any] = {}
    if raw.get("session_id") is not None:
        session["session_id"] = raw["session_id"]
    if raw.get("agent_id") is not None:
        session["agent_id"] = raw["agent_id"]
    if raw.get("prompt_id") is not None:
        session["prompt_id"] = raw["prompt_id"]

    updated_input["_session"] = session

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": updated_input,
        }
    }


def main() -> int:
    raw = json.load(sys.stdin)
    output = inject_caller_session(raw)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
