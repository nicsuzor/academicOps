"""Stateful gate: the single Stop-time handover reminder.

The one Stop-time reminder mechanism (consolidation of the former
``router.py`` Stop branch and the original short exit-reflection warn,
per the 2026-07-23 ruling on the honesty-hook design): on the first
clean Stop of a session, inject the full ``templates/handover.md``
reminder as non-blocking context, once per session, for every session
type. Never blocks. The dispatcher's structural self-loop guard already
filters ``stop_hook_active`` re-entries before any gate runs.

State is a plain dict the dispatcher loaded for this session; this gate
mutates it and relies on the dispatcher to persist it.
"""

from __future__ import annotations

from pathlib import Path

from .event import Event
from .verdict import Verdict, warn

_TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "handover.md"

_USER_TEXT = "≡ **Before you hand back to the user — be honest and useful.**"


def _reminder_text() -> str:
    if _TEMPLATE.exists():
        return _TEMPLATE.read_text().strip()
    return f"<!-- {_TEMPLATE.name} not found -->"


def exit_reflection_reminder(e: Event, state: dict) -> Verdict | None:
    if e.event != "Stop":
        return None
    # Still waiting on background tasks: skip without marking state, so the
    # reminder is delivered on the session's next (clean) Stop instead.
    if e.raw.get("background_tasks"):
        return None
    if state.get("exit_reflection_reminded"):
        return None
    state["exit_reflection_reminded"] = True
    return warn(_reminder_text(), user_text=_USER_TEXT)
