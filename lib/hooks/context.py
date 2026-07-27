"""HookContext: the small, normalized shape every handler reads.

Raw hook JSON varies by client and event; ``normalize`` flattens the fields
handlers actually need. Handlers that need something not lifted here can
still reach into ``ctx.raw``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import messages


@dataclass(frozen=True)
class HookContext:
    client: str  # "claude" | "agy"
    event: str  # canonical event name, e.g. "PreToolUse", "Stop"
    tool: str = ""  # tool_name, e.g. "Bash" (PreToolUse only)
    command: str = ""  # tool_input.command, for Bash-shaped tools
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    hooks_dir: Path = field(default_factory=Path)

    def message(self, name: str) -> str:
        """Load ``hooks/messages/<name>.md`` for this hook.

        Raises ``messages.MessageNotFoundError`` if the file is missing or
        empty — never returns a silent empty string.
        """
        return messages.load(self.hooks_dir, name)


def normalize(client: str, event: str, raw: dict[str, Any], hooks_dir: Path) -> HookContext:
    tool_input = raw.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return HookContext(
        client=client,
        event=event,
        tool=raw.get("tool_name") or raw.get("toolName") or "",
        command=command,
        session_id=raw.get("session_id") or raw.get("conversationId") or "",
        raw=raw,
        hooks_dir=hooks_dir,
    )
