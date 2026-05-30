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
from lib.gate_types import GateCondition, GateConfig, GatePolicy, GateStatus
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


# ---------------------------------------------------------------------------
# Item 5 — the never-block `continue` itself is load-bearing (#1451)
# ---------------------------------------------------------------------------
# WHY a SECOND never-block test: the real enforcer gate excludes
# always_available at the CONDITION level (definitions.py
# excluded_tool_categories), so its policy never matches AskUserQuestion and
# test_enforcer_does_not_block_askuserquestion would pass even if the engine's
# never-block `continue` were deleted — it never reaches it. That test proves
# the *invariant* holds, not that the WS7 engine code is what holds it. This
# test removes the confound with a synthetic gate that DOES match every
# PreToolUse call, so the never-block `continue` in _evaluate_policies is the
# ONLY thing that can stop the deny. Mutating that `continue` away flips this
# test to FAIL — which is the property a load-bearing test must have.


def _always_deny_pretooluse_gate() -> GateConfig:
    """Synthetic gate: deny EVERY PreToolUse call, with no category exclusions.

    Unlike the real enforcer, its policy condition has no
    excluded_tool_categories, so the condition matches never-block tools
    (AskUserQuestion) too. That makes the engine's never-block guard the sole
    line of defence — exactly what this test needs to discriminate.
    """
    return GateConfig(
        name="ws7_never_block_probe",
        description="test-only gate that denies all PreToolUse calls",
        policies=[
            GatePolicy(
                condition=GateCondition(hook_event="PreToolUse"),
                verdict="deny",
                message_template="probe deny",
            )
        ],
    )


def test_never_block_continue_is_load_bearing(monkeypatch):
    """WS7 item 5: the engine's never-block `continue` — not a condition-level
    exclusion — is what spares AskUserQuestion from a matching deny policy.

    Removing the `continue` block in engine._evaluate_policies makes this FAIL.
    """
    monkeypatch.delenv("AOPS_SESSION_REGISTER", raising=False)
    gate = GenericGate(_always_deny_pretooluse_gate())
    state = SessionState.create("ws7-never-block-probe")

    # Control: an ordinary write IS denied — proves the policy actually fires
    # against this synthetic gate (so the AskUserQuestion pass below is the
    # never-block guard, not a dead policy).
    assert _verdict(gate.check(_ctx("Write"), state)) == "deny"

    # Treatment: AskUserQuestion matches the SAME always-deny condition, so the
    # never-block `continue` is the only thing that can save it. The policy loop
    # then exhausts with nothing matched, so check() returns None (no deny, no
    # warn). This is the global never-block invariant honoured by the engine.
    assert gate.check(_ctx("AskUserQuestion"), state) is None, (
        "never-block engine guard must stop the deny on AskUserQuestion (#1451)"
    )
