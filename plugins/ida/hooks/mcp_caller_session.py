#!/usr/bin/env python3
"""Claude Code PreToolUse hook for injecting caller session into MCP calls.

Matching `mcp__.*` tool calls, this hook injects a reserved `_session` object
({session_id, agent_id, prompt_id}) into `hookSpecificOutput.updatedInput`
only when the receiving server uses caller session (`pkb`, `services`),
preserving all original tool arguments.
"""

from __future__ import annotations

import json
import sys
from typing import Any

DEFAULT_SESSION_SERVERS = frozenset({"pkb", "services"})


def extract_mcp_server(tool_name: str) -> str:
    """Extract MCP server name from tool name like mcp__server__tool or mcp__plugin_foo_server__tool."""
    if not tool_name.startswith("mcp__"):
        return ""
    raw = tool_name[5:]
    parts = raw.split("__")
    if not parts or not parts[0]:
        return ""
    server_raw = parts[0]
    if ":" in server_raw:
        return server_raw.split(":")[-1]
    if server_raw.startswith("plugin_"):
        subparts = server_raw.split("_")
        return subparts[-1] if len(subparts) >= 3 else server_raw
    return server_raw


def uses_caller_session(
    tool_name: str,
    session_servers: frozenset[str] = DEFAULT_SESSION_SERVERS,
) -> bool:
    """Check if the target MCP server consumes _session."""
    server = extract_mcp_server(tool_name)
    if not server:
        return False
    return server in session_servers or (
        len(tool_name.split("__")) > 1 and tool_name.split("__")[1] in session_servers
    )


def inject_caller_session(
    raw: dict[str, Any],
    session_servers: frozenset[str] = DEFAULT_SESSION_SERVERS,
) -> dict[str, Any]:
    """Inject `_session` into tool input if applicable.

    Stdin carries `session_id`, `prompt_id` and `tool_use_id`, plus `agent_id`
    inside subagents. Only MCP calls targeting servers that consume caller session
    receive `_session`.
    """
    tool_name = raw.get("tool_name", "")
    if not uses_caller_session(tool_name, session_servers=session_servers):
        return {}

    tool_input = raw.get("tool_input")
    if isinstance(tool_input, dict):
        updated_input = dict(tool_input)
    else:
        updated_input = {}

    session: dict[str, Any] = {}
    session_id = raw.get("session_id") or raw.get("conversationId") or raw.get("conversation_id")
    if session_id is not None:
        session["session_id"] = session_id
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
