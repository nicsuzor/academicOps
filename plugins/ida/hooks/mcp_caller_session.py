#!/usr/bin/env python3
"""PreToolUse hook injecting caller ``session_id`` into PKB MCP tool calls.

Supports both Claude Code and Antigravity (AGY):

- Extracts caller ``session_id`` from the client's official environment variable
  first (``CLAUDE_CODE_SESSION_ID`` then ``CLAUDE_SESSION_ID`` on Claude Code;
  ``ANTIGRAVITY_CONVERSATION_ID`` on AGY), falling back to hook stdin only
  when the env var is absent.
- Claude Code: injects top-level ``session_id`` via
  ``hookSpecificOutput.updatedInput`` on direct PKB tools (``mcp__pkb__*``,
  ``mcp__plugin_*_pkb__*``) and into ``Arguments`` on ``call_mcp_tool`` when
  ``ServerName == "pkb"``. Never injects top-level ``session_id`` onto
  ``portal_codemode_execute`` or other ``portal_*`` tools.
- Antigravity (AGY): emits ``{"overwrite": {"session_id": sid}}`` on direct
  PKB tools (``mcp_pkb_*``, ``mcp__pkb__*``) or
  ``{"overwrite": {"Arguments": {..., "session_id": sid}}}`` on
  ``call_mcp_tool`` when ``ServerName == "pkb"``, only when missing or
  different.

In a Claude Cowork session it changes nothing: Cowork refuses any MCP call
whose input a plugin hook changed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dispatch import is_cowork, resolve_caller_session_id

DEFAULT_SESSION_SERVERS = frozenset({"pkb", "services"})


def extract_mcp_server(tool_name: str) -> str:
    """Extract MCP server name from Claude or AGY MCP tool names."""
    if tool_name.startswith("mcp_pkb_"):
        return "pkb"
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
        remainder = server_raw[7:]
        if "_" in remainder:
            _, server_name = remainder.split("_", 1)
            return server_name
        return remainder
    return server_raw


def _extract_short_tool_name(tool_name: str) -> str:
    """Return the unprefixed tool name from an ``mcp__<server>__<tool>`` name."""
    if tool_name.startswith("mcp__"):
        remainder = tool_name[5:]
        if "__" in remainder:
            return remainder.split("__", 1)[1]
    return tool_name


def _is_call_mcp_tool(tool_name: str, session_servers: frozenset[str]) -> bool:
    """Return True if *tool_name* is the services ``call_mcp_tool`` wrapper."""
    if tool_name == "call_mcp_tool":
        return "services" in session_servers
    server = extract_mcp_server(tool_name)
    short_tool = _extract_short_tool_name(tool_name)
    return server == "services" and "services" in session_servers and short_tool == "call_mcp_tool"


def uses_caller_session(
    tool_name: str,
    session_servers: frozenset[str] = DEFAULT_SESSION_SERVERS,
) -> bool:
    """Return True if *tool_name* accepts injected caller ``session_id``."""
    short_tool = _extract_short_tool_name(tool_name)
    if short_tool.startswith("portal_"):
        return False
    if _is_call_mcp_tool(tool_name, session_servers):
        return True
    server = extract_mcp_server(tool_name)
    return server == "pkb" and server in session_servers


def _resolve_root_session_id(raw_session_id: str) -> str:
    """Resolve root Phoenix session ID for subagents when tracer state exists."""
    if "/" in raw_session_id:
        return raw_session_id.split("/", 1)[0]
    try:
        state_file = Path.home() / ".claude" / "tracer" / f"{raw_session_id}.json"
        if state_file.is_file():
            sdata = json.loads(state_file.read_text(encoding="utf-8"))
            phx_sid = sdata.get("phoenix_session_id")
            if phx_sid:
                phx_root = str(phx_sid).split("/", 1)[0]
                if phx_root:
                    return phx_root
    except Exception:
        pass
    return raw_session_id


def inject_caller_session(
    raw: dict[str, Any],
    session_servers: frozenset[str] = DEFAULT_SESSION_SERVERS,
    client: str = "",
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Inject top-level ``session_id`` into PKB MCP tool inputs."""
    effective_client = client or (
        "agy" if ("toolCall" in raw or "conversationId" in raw) else "claude"
    )
    if effective_client == "agy":
        tc_val = raw.get("toolCall")
        tool_call: dict[str, Any] = tc_val if isinstance(tc_val, dict) else {}
        tool_name = str(tool_call.get("name") or raw.get("tool_name") or raw.get("toolName") or "")
        args_val = tool_call.get("args")
        if isinstance(args_val, dict):
            raw_args: dict[str, Any] = args_val
        else:
            ti_val = raw.get("tool_input")
            raw_args = ti_val if isinstance(ti_val, dict) else {}
    else:
        tool_name = str(raw.get("tool_name") or "")
        ti_val = raw.get("tool_input")
        raw_args = ti_val if isinstance(ti_val, dict) else {}

    if not uses_caller_session(tool_name, session_servers=session_servers):
        return {}

    raw_sid = resolve_caller_session_id(raw, client=effective_client, environ=environ)
    if not raw_sid:
        return {}
    sid = _resolve_root_session_id(raw_sid)
    if not sid:
        return {}

    if _is_call_mcp_tool(tool_name, session_servers):
        if raw_args.get("ServerName") != "pkb":
            return {}
        existing_args = raw_args.get("Arguments")
        if existing_args is None:
            merged_args: dict[str, Any] = {"session_id": sid}
        elif isinstance(existing_args, dict):
            if effective_client == "agy" and existing_args.get("session_id") == sid:
                return {}
            merged_args = {**existing_args, "session_id": sid}
        else:
            return {}

        if effective_client == "agy":
            return {"overwrite": {"Arguments": merged_args}}
        updated_input: dict[str, Any] = dict(raw_args)
        updated_input["Arguments"] = merged_args
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated_input,
            }
        }

    if effective_client == "agy":
        if raw_args.get("session_id") == sid:
            return {}
        return {"overwrite": {"session_id": sid}}

    direct_updated: dict[str, Any] = dict(raw_args)
    direct_updated["session_id"] = sid
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": direct_updated,
        }
    }


def main() -> int:
    client = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = json.load(sys.stdin)
    if client != "agy" and is_cowork():
        return 0
    output = inject_caller_session(raw, client=client)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
