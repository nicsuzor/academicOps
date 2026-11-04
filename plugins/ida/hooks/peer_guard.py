#!/usr/bin/env python3
"""Main Ida peer guard hook.

Blocks the primary conversational Ida context from spawning or messaging
Pauli or Sara directly, requiring delegation through an internal sub-Ida
(subagent_type: "ida:ida").
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dispatch import HookContext, Kind, Result, refuse

_SUBAGENT_TOOLS = frozenset({"agent", "invoke_subagent", "task"})
_MESSAGE_TOOLS = frozenset({"sendmessage", "send_message"})

_DEFAULT_BLOCKED_PEERS = ("pauli", "sara")
_REFUSAL_MESSAGE = (
    "The main Ida cannot ask Pauli or Sara directly. "
    'Delegate your ask through an internal sub-Ida (subagent_type: "ida:ida") instead.'
)


def _load_blocked_peers() -> tuple[str, ...]:
    try:
        import tomllib

        policy_path = Path(__file__).resolve().parents[3] / "tests" / "policy.toml"
        if policy_path.is_file():
            data = tomllib.loads(policy_path.read_text(encoding="utf-8"))
            peers = data.get("ida", {}).get("peer_guard", {}).get("blocked_peers")
            if peers:
                return tuple(str(p).lower().strip() for p in peers)
    except Exception:
        pass
    return _DEFAULT_BLOCKED_PEERS


def peer_guard(ctx: HookContext) -> Result | None:
    """PreToolUse handler blocking main-thread delegation to Pauli or Sara."""
    # Subagents pass through unrestricted (AC-HOOK-2)
    if ctx.agent_id:
        return None

    tool = (ctx.tool or "").strip().lower()
    tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}

    target = ""
    if tool in _SUBAGENT_TOOLS:
        target = (
            tool_input.get("subagent_type")
            or tool_input.get("agent_type")
            or tool_input.get("TypeName")
            or tool_input.get("typeName")
            or tool_input.get("type")
            or ""
        )
    elif tool in _MESSAGE_TOOLS:
        target = (
            tool_input.get("to") or tool_input.get("recipient") or tool_input.get("Recipient") or ""
        )
    else:
        return None

    target_str = str(target).strip()
    if not target_str:
        return None

    normalized = target_str.lower()
    base = normalized.split(":")[-1].split("@")[0].strip()

    blocked = _load_blocked_peers()
    if base in blocked or normalized in blocked or any(f":{p}" in normalized for p in blocked):
        return refuse(_REFUSAL_MESSAGE)

    return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry point failing closed on invalid JSON or blocked calls."""
    if sys.stdin.isatty():
        return 0

    raw_text = sys.stdin.read()
    if not raw_text.strip():
        return 0

    try:
        data = json.loads(raw_text)
    except Exception as exc:
        print(f"peer_guard: hook input is not valid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("peer_guard: hook input must be a JSON object", file=sys.stderr)
        return 2

    hooks_dir = Path(__file__).resolve().parent
    from dispatch import normalize

    ctx = normalize("claude", "PreToolUse", data, hooks_dir)
    res = peer_guard(ctx)
    if res is not None and res.kind is Kind.REFUSE:
        print(f"peer_guard: {res.inject_text}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
