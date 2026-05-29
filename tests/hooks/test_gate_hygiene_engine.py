#!/usr/bin/env python3
"""WS7 gate-hygiene behaviour, exercised against the REAL gate engine.

These tests drive GenericGate (the production engine) with real GateConfig
definitions and SessionState, proving the composition primitives in
hooks.gate_config actually change gate verdicts — not just that the helpers
return the right booleans (covered by test_gate_config.py).

Each test maps to a WS7 deliverable item and the specific field failure it
targets (cited inline).
"""

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).resolve().parents[2] / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.schemas import HookContext
from lib.gate_types import GateStatus
from lib.gates.definitions import GATE_CONFIGS
from lib.gates.engine import GenericGate
from lib.session_state import SessionState

_CONFIGS = {c.name: c for c in GATE_CONFIGS}


def _ctx(tool_name, hook_event="PreToolUse", tool_input=None):
    return HookContext(
        session_id="ws7-engine-test",
        trace_id=None,
        hook_event=hook_event,
        tool_name=tool_name,
        tool_input=tool_input or {},
        is_subagent=False,
        raw_input={},
    )


def _state_with_enforcer_overdue():
    """Session state with the enforcer gate past its block threshold."""
    state = SessionState.create("ws7-engine-test")
    state.main_agent.current_task = "task-x"  # so the gate is "armed"
    state.gates["enforcer"].status = GateStatus.OPEN
    state.gates["enforcer"].ops_since_open = 999
    return state


def _verdict(result):
    if result is None:
        return None
    return getattr(result.verdict, "value", result.verdict)


# ---------------------------------------------------------------------------
# Item 5 — never-block honoured by the engine (#1451)
# ---------------------------------------------------------------------------


def test_enforcer_blocks_write_at_threshold(monkeypatch):
    """Control: an overdue enforcer DOES deny an ordinary write tool."""
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("Write"), _state_with_enforcer_overdue())
    assert _verdict(result) == "deny"


def test_enforcer_does_not_block_askuserquestion(monkeypatch):
    """WS7 item 5: never-block stops the enforcer denying AskUserQuestion (#1451).

    Same overdue state as the control above; only the tool changed. The deny
    must NOT fire, because AskUserQuestion is on the never-block list.
    """
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("AskUserQuestion"), _state_with_enforcer_overdue())
    assert _verdict(result) != "deny", (
        "AskUserQuestion must never be denied by a gate (never-block, #1451)"
    )


# ---------------------------------------------------------------------------
# Item 6 — register-scaling enforced by the engine (retro MF4)
# ---------------------------------------------------------------------------


def test_capture_register_suppresses_enforcer_block(monkeypatch):
    """WS7 item 6: in the capture register the enforcer drops its ceremony.

    Identical overdue state + Write tool as the item-5 control (which denies);
    only the register changed, so the deny must NOT fire.
    """
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_SESSION_REGISTER", "capture")
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("Write"), _state_with_enforcer_overdue())
    assert _verdict(result) != "deny", (
        "capture register must suppress the enforcer review-grade block (MF4)"
    )


def test_capture_register_does_not_suppress_sentinel(monkeypatch):
    """WS7 item 6: register-scaling drops ceremony, NOT safety.

    The sentinel destructive-op block must still fire in the capture register —
    losing data to `rm` on a protected path is real harm regardless of stakes.
    """
    monkeypatch.setenv("SENTINEL_GATE_MODE", "block")
    monkeypatch.setenv("AOPS_SESSION_REGISTER", "capture")
    gate = GenericGate(_CONFIGS["sentinel"])
    result = gate.check(
        _ctx("Bash", tool_input={"command": "rm -rf ~/.claude/plugins"}),
        SessionState.create("ws7-engine-test"),
    )
    assert _verdict(result) == "deny", (
        "sentinel must still block destructive ops even in the capture register"
    )


def test_working_register_does_not_suppress_enforcer(monkeypatch):
    """Control: outside the capture register the enforcer block fires normally."""
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
    gate = GenericGate(_CONFIGS["enforcer"])
    result = gate.check(_ctx("Write"), _state_with_enforcer_overdue())
    assert _verdict(result) == "deny"
