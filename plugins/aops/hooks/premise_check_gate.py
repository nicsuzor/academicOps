#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for premise checking.

Enforces that a supervisor (Ida) evaluates incoming subagent reports against
logic-check doctrine before dispatching further subagents:

- ``premise_check_arm``: a ``PostToolBatch`` handler that arms the check when
  an agent finishes calling tools (including subagents, before results return).
- ``premise_check_handler``: a ``PreToolUse`` handler that refuses the
  supervisor's next subagent dispatch (``Agent``/``Task``) while armed.
- ``arm()`` / ``disarm()``: state management primitives. Calling ``disarm()``
  clears the check once a verdict is recorded.

Verdict recording and OpenTelemetry trace emission live separately in
``premise_check_verdict.py``.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, refuse, warn


def _now() -> str:
    """Current time as an ISO-8601 string carrying the local system UTC offset."""
    return datetime.now().astimezone().isoformat()


# Agent profiles this check applies to
_GATED_AGENT_TYPES = ["aops:ida"]
_GATED_TOOLS = ("Agent", "Task")


# ---------------------------------------------------------------------------
# State: is the premise check armed (awaiting verdict) or disarmed?
# ---------------------------------------------------------------------------


def _state_dir() -> Path:
    override = os.environ.get("AOPS_PREMISE_CHECK_DIR") or os.environ.get("AOPS_PREMISE_GATE_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_premise_check"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(session_id: str) -> Path:
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    return _state_dir() / f"{safe_session}.json"


def _load_state(session_id: str) -> dict[str, Any]:
    target = _state_path(session_id)
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(session_id: str, state: dict[str, Any]) -> None:
    _state_path(session_id).write_text(json.dumps(state, indent=2), encoding="utf-8")


def clear_state(session_id: str) -> None:
    """Reset premise check state for a session. Used by tests."""
    target = _state_path(session_id)
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass


def get_state(session_id: str) -> dict[str, Any]:
    return _load_state(session_id)


def arm(session_id: str, claim_id: str | None = None) -> None:
    """Arm the premise check for a session until a verdict disarms it."""
    state = _load_state(session_id)
    state["armed"] = True
    state["pending"] = True  # backward compat
    state["claim_id"] = claim_id or state.get("claim_id") or "unnamed-claim"
    state["armed_at"] = _now()
    _save_state(session_id, state)


def disarm(
    session_id: str,
    claim_id: str,
    questions: list[str] | None = None,
    answers: list[str] | None = None,
) -> None:
    """Disarm the premise check after a verdict is recorded."""
    state = _load_state(session_id)
    state["armed"] = False
    state["pending"] = False  # backward compat
    state["claim_id"] = claim_id
    state["last_verdict"] = {
        "claim_id": claim_id,
        "questions": list(questions or []),
        "answers": list(answers or []),
        "recorded_at": _now(),
    }
    _save_state(session_id, state)


def is_armed(session_id: str) -> bool:
    """Return True if the premise check is armed (awaiting verdict)."""
    state = _load_state(session_id)
    return bool(state.get("armed") or state.get("pending"))


def is_disarmed(session_id: str) -> bool:
    """Return True if the premise check is disarmed (cleared to proceed)."""
    return not is_armed(session_id)


# Aliases for terminology clarity:
# "open" = disarmed (free to proceed), "closed" = armed (blocking dispatch)
close_gate = arm
open_gate = disarm
is_gate_open = is_disarmed


def _derive_claim_id(ctx: HookContext) -> str:
    for call in ctx.tool_calls:
        if call.get("tool_name") in _GATED_TOOLS:
            tool_input = call.get("tool_input") or {}
            desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
            if desc:
                return desc[:80]
            call_id = call.get("tool_use_id") or ""
            if call_id:
                return str(call_id)
    return "unnamed-claim"


def _is_override_active() -> bool:
    for var in (
        "PREMISE_CHECK_OVERRIDE",
        "PREMISE_CHECK_GATE_OVERRIDE",
        "AOP_FORCE",
        "AOP_OVERRIDE",
    ):
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return True
    return False


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def premise_check_arm(ctx: HookContext) -> Result | None:
    """PostToolBatch handler: arm the premise check when an agent calls tools.

    PostToolBatch is called when an agent finishes calling tools, including
    subagents (though the subagent results haven't returned yet). This arms
    the premise check, which then needs to be cleared (disarmed via verdict)
    before the next tool use.
    """
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None
    if not any(call.get("tool_name") in _GATED_TOOLS for call in ctx.tool_calls):
        return None
    arm(ctx.session_id, claim_id=_derive_claim_id(ctx))
    return None


def premise_check_handler(ctx: HookContext) -> Result | None:
    """PreToolUse handler: refuse the next subagent dispatch while armed."""
    if ctx.tool not in _GATED_TOOLS:
        return None
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    mode = (
        os.environ.get("PREMISE_CHECK_GATE_MODE", os.environ.get("PREMISE_CHECK_MODE", "block"))
        .strip()
        .lower()
    )
    if mode == "off":
        return None
    if _is_override_active():
        return None
    if not is_armed(ctx.session_id):
        return None

    claim_id = get_state(ctx.session_id).get("claim_id", "the pending subagent report")
    reason = (
        f"A subagent report ({claim_id!r}) is pending its logic-check verdict for session "
        f"'{ctx.session_id or 'current'}'. Use the 'premise-check' skill "
        "(or run scripts/verdict.py with hearsay.md's six-question sequence) before "
        "dispatching another subagent."
    )
    user_msg = (
        "Blocked: record the logic-check verdict on the last subagent report "
        "(use 'premise-check' skill) before dispatching another subagent."
    )
    if mode == "warn":
        return warn(reason, user_msg)
    return refuse(reason, user_msg)


# Aliases for hook registrations
premise_check_open_gate = premise_check_arm
premise_check_gate_handler = premise_check_handler
