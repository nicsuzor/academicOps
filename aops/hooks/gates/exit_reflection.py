"""Stateful gate: remind the agent, once per session, to reflect before Stop.

Proves the stateful shape end-to-end. State is a plain dict the dispatcher
loaded for this session; this gate mutates it and relies on the dispatcher
to persist it.
"""

from __future__ import annotations

from .event import Event
from .verdict import Verdict, warn

_REMINDER = (
    "Before ending: capture durable knowledge, verify subagent outputs, "
    "and confirm your commit/PR reflects the original ask."
)


def exit_reflection_reminder(e: Event, state: dict) -> Verdict | None:
    if e.event != "Stop":
        return None
    if state.get("exit_reflection_reminded"):
        return None
    state["exit_reflection_reminded"] = True
    return warn(_REMINDER)
