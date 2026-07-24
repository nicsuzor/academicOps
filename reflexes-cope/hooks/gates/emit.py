"""Verdict -> wire format adapter for reflexes-cope."""

from __future__ import annotations

from .event import Event
from .verdict import Verdict


def emit(verdict: Verdict | None, event: Event, client: str) -> dict:
    if verdict is None:
        return {}
    if client == "claude":
        return _emit_claude(verdict, event)
    if client == "agy":
        return _emit_agy(verdict, event)
    raise ValueError(f"emit: unknown client {client!r}")


def _emit_claude(verdict: Verdict, event: Event) -> dict:
    if event.event == "PreToolUse" and verdict.outcome == "deny":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": verdict.inject_text,
            }
        }
    if verdict.outcome == "deny":
        return {"decision": "block", "reason": verdict.inject_text}
    output = {
        "hookSpecificOutput": {
            "hookEventName": event.event,
            "additionalContext": verdict.inject_text,
        }
    }
    if verdict.user_text:
        output["systemMessage"] = verdict.user_text
    return output


def _emit_agy(verdict: Verdict, event: Event) -> dict:
    return {"injectSteps": [{"ephemeralMessage": verdict.inject_text}]}
