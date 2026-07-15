"""Verdict -> wire format, one small adapter function per client.

Not a framework: two `if client ==` branches, nothing more. Add a client by
adding a branch here, not by touching the gates or the dispatcher.

Claude mapping (confirmed against current Claude Code docs, 2026-07):
- PreToolUse deny  -> hookSpecificOutput.permissionDecision:"deny" +
  permissionDecisionReason.
- Everything else (Stop/PostToolUse/etc.) deny -> top-level decision:"block"
  + reason.
- warn (any event) -> hookSpecificOutput.additionalContext (non-blocking).
- allow (verdict is None) -> no output.

agy (Antigravity) mapping: only the non-blocking context-injection shape is
confirmed (matches aops/hooks/router.py's existing PreInvocation/
PostInvocation `injectSteps`/`ephemeralMessage` pattern). agy has no
confirmed equivalent of Claude's permissionDecision:"deny" block. A `deny`
verdict on agy currently degrades to the same context-injection shape as
`warn` rather than guessing at a schema — see TODO(agy-deny-format) below.
Tracked as a follow-up.
"""

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
                "permissionDecisionReason": verdict.message,
            }
        }
    if verdict.outcome == "deny":
        return {"decision": "block", "reason": verdict.message}
    # warn, any event: non-blocking context injection.
    return {
        "hookSpecificOutput": {
            "hookEventName": event.event,
            "additionalContext": verdict.message,
        }
    }


def _emit_agy(verdict: Verdict, event: Event) -> dict:
    if verdict.outcome == "deny":
        # TODO(agy-deny-format): agy's blocking wire contract is unconfirmed.
        # Fall back to context injection rather than guess at a schema; the
        # message still reaches the agent. Tracked as a follow-up.
        pass
    return {"injectSteps": [{"ephemeralMessage": verdict.message}]}
