"""Event: the small, normalized shape every gate reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    event: str  # hook_event_name, e.g. "PreToolUse", "Stop"
    tool: str = ""  # tool_name, e.g. "Bash"
    command: str = ""  # tool_input.command, for Bash-shaped tools
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def normalize(raw: dict[str, Any]) -> Event:
    tool_input = raw.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return Event(
        event=raw.get("hook_event_name", ""),
        tool=raw.get("tool_name", "") or "",
        command=command,
        session_id=raw.get("session_id", "") or "",
        raw=raw,
    )
