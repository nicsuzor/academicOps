"""Stateless gate: refuse `rm -rf` from a Bash tool call.

Proves the stateless shape end-to-end. The function IS the condition.
"""

from __future__ import annotations

from .event import Event
from .verdict import Verdict, deny


def block_rm_rf(e: Event, state: dict) -> Verdict | None:
    if e.event == "PreToolUse" and e.tool == "Bash" and "rm -rf" in e.command:
        return deny("Refuse rm -rf — confirm the exact path explicitly.")
    return None
