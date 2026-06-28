#!/usr/bin/env python3
"""Tests for the rbg-review Stop gate.

Reworked (epic-f490bb11) from the original block-every-stop #1928. The gate is
now an END-OF-SESSION rbg axiom audit, scoped to TASK-BOUND (polecat/crew)
sessions only:

- POLECAT/CREW: ARMED (CLOSED) from session start; re-arms CLOSED on every
  UserPromptSubmit, so the autonomous session's exit Stop forces a final rbg
  audit. DENIES Stop while armed until the rbg subagent runs (structural
  trigger: Stop + armed + session type — NOT a content sniff). CLEARS (OPEN)
  when rbg runs, then exit is allowed.
- AD HOC INTERACTIVE: starts OPEN (inert) and NEVER re-arms — the UPS re-arm is
  session_type_filtered to polecat/crew. The Stop policy never fires, so
  interactive users eat no per-turn rbg delay.
- ESCAPE-HATCH: after RBG_REVIEW_DEGRADE_THRESHOLD consecutive Stop blocks,
  degrades DENY -> WARN-and-allow with a loud message so a broken rbg dispatch
  cannot permanently trap the session.

Drives the gate through router._dispatch_gates with a real SessionState +
HookContext, mirroring test_handover_gate_regression.py.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.hook_context import HookContext
from lib.session_state import SessionState


def _reinit_gates():
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture
def router(monkeypatch):
    # Isolate the rbg-review gate: silence the other Stop gates so their
    # verdicts don't mask rbg-review's, and pin block mode + threshold.
    monkeypatch.setenv("RBG_REVIEW_GATE_MODE", "block")
    monkeypatch.setenv("RBG_REVIEW_DEGRADE_THRESHOLD", "5")
    monkeypatch.setenv("IDA_GATE_MODE", "off")
    monkeypatch.setenv("QA_GATE_MODE", "off")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "off")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "off")
    _reinit_gates()
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _ctx(event: str, **kw) -> HookContext:
    return HookContext(session_id="rbg-test", client_type="claude", hook_event=event, **kw)


def _ups(prompt: str = "do a thing") -> HookContext:
    return _ctx("UserPromptSubmit", raw_input={"prompt": prompt})


def _polecat_state(session_id: str = "rbg-test") -> SessionState:
    """Create a polecat (task-bound) SessionState — rbg-review starts CLOSED."""
    old = os.environ.get("AOPS_POLECAT_CONTAINER")
    os.environ["AOPS_POLECAT_CONTAINER"] = "1"
    try:
        return SessionState.create(session_id, client_type="claude")
    finally:
        if old is not None:
            os.environ["AOPS_POLECAT_CONTAINER"] = old
        else:
            os.environ.pop("AOPS_POLECAT_CONTAINER", None)


def _interactive_state(session_id: str = "rbg-test") -> SessionState:
    """Create an ad hoc interactive SessionState — rbg-review starts OPEN."""
    # Ensure the polecat env is not leaking in from another test.
    old = os.environ.pop("AOPS_POLECAT_CONTAINER", None)
    try:
        return SessionState.create(session_id, client_type="claude")
    finally:
        if old is not None:
            os.environ["AOPS_POLECAT_CONTAINER"] = old


def _armed_polecat_state(router) -> SessionState:
    """Fresh polecat session, armed by a UserPromptSubmit (gate CLOSED)."""
    state = _polecat_state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    return state


# --- SCOPING: armed only for task-bound (polecat/crew) sessions --------------


def test_polecat_gate_starts_armed_from_session_start(router):
    """Polecat: gate is CLOSED (armed) from session start."""
    state = _polecat_state()
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


def test_crew_gate_starts_armed_from_session_start(router):
    """Crew (also task-bound autonomous): gate is CLOSED (armed)."""
    old = os.environ.get("AOPS_POLECAT_CONTAINER")
    old_crew = os.environ.get("POLECAT_CREW_NAME")
    os.environ["AOPS_POLECAT_CONTAINER"] = "1"
    os.environ["POLECAT_CREW_NAME"] = "alpha"
    try:
        state = SessionState.create("rbg-test", client_type="claude")
    finally:
        for k, v in (("AOPS_POLECAT_CONTAINER", old), ("POLECAT_CREW_NAME", old_crew)):
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
    assert state.session_type == "crew"
    # crew is in initial_status_by_session_type -> CLOSED
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


def test_interactive_gate_starts_open_inert(router):
    """Ad hoc interactive: gate starts OPEN (inert) — no per-turn rbg delay."""
    state = _interactive_state()
    assert state.session_type == "interactive"
    assert state.gates["rbg-review"].status == GateStatus.OPEN


def test_interactive_ups_does_not_arm_the_gate(router):
    """Interactive: UserPromptSubmit does NOT re-arm — stays OPEN every turn."""
    state = _interactive_state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.OPEN


def test_interactive_stop_never_blocks_per_turn(router):
    """Interactive: Stop is ALLOWED every turn — gate never fires the rbg delay.

    This is the core of the rework: ad hoc interactive discussions must NOT eat
    the rbg delay on every turn (the bug in the original block-every-stop PR).
    """
    state = _interactive_state()
    for _ in range(3):
        router._dispatch_gates(_ups(), state)
        result = router._dispatch_gates(_ctx("Stop"), state)
        # Other Stop gates are off, so an allowed Stop yields no blocking verdict.
        assert result is None or result.verdict == GateVerdict.ALLOW
        assert state.gates["rbg-review"].status == GateStatus.OPEN


def test_polecat_ups_arms_the_gate(router):
    """Polecat: UserPromptSubmit re-arms the gate (so the exit Stop is armed)."""
    state = _polecat_state()
    state.gates["rbg-review"].status = GateStatus.OPEN
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


# --- (a) Stop DENIED when armed and rbg has not run (polecat) -----------------


def test_polecat_stop_denied_when_armed_and_rbg_not_run(router):
    """Polecat exit: Stop is DENIED while armed and rbg has not run."""
    state = _armed_polecat_state(router)
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is not None
    assert result.verdict == GateVerdict.DENY
    assert "subagent_type='aops-core:rbg'" in (result.context_injection or "")


def test_stop_stays_denied_across_retries_no_fire_once_leak(router):
    """Repeated Stops without rbg stay DENIED — no fire-once 'open on Stop' leak.

    This is the key difference from qa/handover/ida: those open on the first
    Stop so a retried Stop passes. rbg-review must NOT — that would let the
    second (exit) Stop pass without rbg having run.
    """
    state = _armed_polecat_state(router)
    r1 = router._dispatch_gates(_ctx("Stop"), state)
    r2 = router._dispatch_gates(_ctx("Stop"), state)
    assert r1.verdict == GateVerdict.DENY
    assert r2.verdict == GateVerdict.DENY
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


# --- (b) Stop ALLOWED after rbg has run (polecat) -----------------------------


def test_rbg_run_clears_the_gate(router):
    """When the rbg subagent runs, the gate clears (OPEN) and latches sticky."""
    state = _armed_polecat_state(router)
    router._dispatch_gates(_ctx("Stop"), state)  # deny first
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    gate = state.gates["rbg-review"]
    assert gate.status == GateStatus.OPEN
    assert gate.sticky is True
    assert gate.metrics.get("stop_deny_count") == 0


def test_stop_allowed_after_rbg_run(router):
    """After rbg runs, Stop is ALLOWED (no DENY/WARN from this gate)."""
    state = _armed_polecat_state(router)
    router._dispatch_gates(_ctx("Stop"), state)
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    result = router._dispatch_gates(_ctx("Stop"), state)
    # Other Stop gates are off, so an allowed Stop yields no blocking verdict.
    assert result is None or result.verdict == GateVerdict.ALLOW


def test_bare_rbg_subagent_name_clears(router):
    """A bare 'rbg' subagent_type (no aops-core: prefix) also clears the gate."""
    state = _armed_polecat_state(router)
    router._dispatch_gates(_ctx("SubagentStart", subagent_type="rbg"), state)
    assert state.gates["rbg-review"].status == GateStatus.OPEN


def test_post_rbg_edits_do_not_reblock_this_turn(router):
    """Sticky latch: edits after rbg ran do not re-block / re-arm the same turn.

    This is the gate-discharge re-trigger invariant for THIS gate: the rbg
    discharge completing, and any follow-up edit, must NOT re-arm the gate.
    """
    state = _armed_polecat_state(router)
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    # An edit (PostToolUse write) must not re-close the gate this turn.
    router._dispatch_gates(
        _ctx("PostToolUse", tool_name="Edit", tool_input={"file_path": "foo.py"}), state
    )
    assert state.gates["rbg-review"].status == GateStatus.OPEN
    # A retried Stop after the rbg discharge + edit is still ALLOWED (no loop).
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is None or result.verdict == GateVerdict.ALLOW
    # Next turn re-arms (polecat).
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    assert state.gates["rbg-review"].sticky is False


# --- (c) Escape-hatch degrades after N failures (polecat) ---------------------


def test_escape_hatch_degrades_after_threshold(router):
    """After RBG_REVIEW_DEGRADE_THRESHOLD consecutive Stop blocks, degrade to WARN."""
    state = _armed_polecat_state(router)
    verdicts = []
    for _ in range(5):
        r = router._dispatch_gates(_ctx("Stop"), state)
        verdicts.append(r.verdict)
    # First four DENY, fifth degrades to WARN-and-allow.
    assert verdicts[:4] == [GateVerdict.DENY] * 4
    assert verdicts[4] == GateVerdict.WARN


def test_escape_hatch_message_is_loud(router):
    """The degraded fire emits the loud, user-visible escape-hatch message."""
    state = _armed_polecat_state(router)
    result = None
    for _ in range(5):
        result = router._dispatch_gates(_ctx("Stop"), state)
    assert result.verdict == GateVerdict.WARN
    assert "ESCAPE-HATCH" in (result.system_message or "")


def test_deny_count_resets_on_next_turn(router):
    """The escape-hatch deny budget resets each turn (UPS re-arm, polecat)."""
    state = _armed_polecat_state(router)
    for _ in range(2):
        router._dispatch_gates(_ctx("Stop"), state)
    assert state.gates["rbg-review"].metrics.get("stop_deny_count") == 2
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].metrics.get("stop_deny_count") == 0


# --- Coexistence: rbg-review defers Ida, does not break it -------------------


def test_rbg_review_defers_ida_without_breaking_it(router, monkeypatch):
    """rbg-review DENY defers Ida (advisory) — Ida fires once rbg has cleared.

    Ida is armed in ALL session types; rbg-review only fires for polecat/crew,
    so we run this on a polecat session where both are armed.
    """
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    _reinit_gates()
    state = _polecat_state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["ida"].status == GateStatus.CLOSED
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    # rbg-review denies first; ida is deferred (still CLOSED, not consumed).
    r = router._dispatch_gates(_ctx("Stop"), state)
    assert r.verdict == GateVerdict.DENY
    assert state.gates["ida"].status == GateStatus.CLOSED
    # rbg runs -> clears; next Stop, ida fires its advisory and opens.
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    router._dispatch_gates(_ctx("Stop"), state)
    assert state.gates["ida"].status == GateStatus.OPEN


def test_interactive_ida_still_fires_without_rbg_review(router, monkeypatch):
    """Ida is NOT suppressed in interactive: rbg-review is inert, ida still fires."""
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    _reinit_gates()
    state = _interactive_state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["ida"].status == GateStatus.CLOSED
    assert state.gates["rbg-review"].status == GateStatus.OPEN  # inert
    r = router._dispatch_gates(_ctx("Stop"), state)
    # rbg-review is OPEN/inert; ida fires its advisory (WARN) and opens.
    assert r is not None
    assert r.verdict == GateVerdict.WARN
    assert state.gates["ida"].status == GateStatus.OPEN
