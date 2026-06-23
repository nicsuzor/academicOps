#!/usr/bin/env python3
"""Tests for the rbg-review Stop gate.

The rbg-review gate makes the per-turn axiom review RUN before Stop can pass:

- ARMS on UserPromptSubmit (turn-scoped; starts CLOSED from session start).
- DENIES Stop while armed (CLOSED) until the rbg subagent has run for the turn,
  injecting the rbg-dispatch instruction. The trigger is STRUCTURAL (Stop event
  + armed flag), not a content sniff.
- CLEARS (OPEN) when the rbg subagent runs, then Stop is allowed.
- ESCAPE-HATCH: after RBG_REVIEW_DEGRADE_THRESHOLD consecutive Stop blocks in one
  turn, degrades DENY -> WARN-and-allow with a loud message so a broken rbg
  dispatch cannot permanently trap the session.

Mirrors the engine-driven gate tests in test_handover_gate_regression.py — drives
the gate through router._dispatch_gates with a real SessionState + HookContext.
"""

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
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


def _armed_state(router) -> SessionState:
    """Fresh session, armed by a UserPromptSubmit (gate CLOSED)."""
    state = SessionState.create("rbg-test", client_type="claude")
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    return state


# --- (a) Stop DENIED when armed and rbg has not run --------------------------


def test_gate_starts_armed_from_session_start(router):
    """Gate is CLOSED (armed) from session start, before any UserPromptSubmit."""
    state = SessionState.create("rbg-test", client_type="claude")
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


def test_ups_arms_the_gate(router):
    """UserPromptSubmit re-arms the gate (turn-scoped)."""
    state = SessionState.create("rbg-test", client_type="claude")
    # Force OPEN, then UPS should re-arm to CLOSED.
    state.gates["rbg-review"].status = GateStatus.OPEN
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


def test_stop_denied_when_armed_and_rbg_not_run(router):
    """Stop is DENIED while armed and rbg has not run; injects rbg dispatch."""
    state = _armed_state(router)
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is not None
    assert result.verdict == GateVerdict.DENY
    assert "subagent_type='aops-core:rbg'" in (result.context_injection or "")


def test_stop_stays_denied_across_retries_no_fire_once_leak(router):
    """Repeated Stops without rbg stay DENIED — no fire-once 'open on Stop' leak.

    This is the key difference from qa/handover/ida: those open on the first
    Stop so a retried Stop passes. rbg-review must NOT — that would let the
    second Stop pass without rbg having run.
    """
    state = _armed_state(router)
    r1 = router._dispatch_gates(_ctx("Stop"), state)
    r2 = router._dispatch_gates(_ctx("Stop"), state)
    assert r1.verdict == GateVerdict.DENY
    assert r2.verdict == GateVerdict.DENY
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


# --- (b) Stop ALLOWED after rbg has run --------------------------------------


def test_rbg_run_clears_the_gate(router):
    """When the rbg subagent runs, the gate clears (OPEN) and latches sticky."""
    state = _armed_state(router)
    router._dispatch_gates(_ctx("Stop"), state)  # deny first
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    gate = state.gates["rbg-review"]
    assert gate.status == GateStatus.OPEN
    assert gate.sticky is True
    assert gate.metrics.get("stop_deny_count") == 0


def test_stop_allowed_after_rbg_run(router):
    """After rbg runs, Stop is ALLOWED (no DENY/WARN from this gate)."""
    state = _armed_state(router)
    router._dispatch_gates(_ctx("Stop"), state)
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    result = router._dispatch_gates(_ctx("Stop"), state)
    # Other Stop gates are off, so an allowed Stop yields no blocking verdict.
    assert result is None or result.verdict == GateVerdict.ALLOW


def test_bare_rbg_subagent_name_clears(router):
    """A bare 'rbg' subagent_type (no aops-core: prefix) also clears the gate."""
    state = _armed_state(router)
    router._dispatch_gates(_ctx("SubagentStart", subagent_type="rbg"), state)
    assert state.gates["rbg-review"].status == GateStatus.OPEN


def test_post_rbg_edits_do_not_reblock_this_turn(router):
    """Sticky latch: edits after rbg ran do not re-block the same turn."""
    state = _armed_state(router)
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    # An edit (PostToolUse write) must not re-close the gate this turn.
    router._dispatch_gates(
        _ctx("PostToolUse", tool_name="Edit", tool_input={"file_path": "foo.py"}), state
    )
    assert state.gates["rbg-review"].status == GateStatus.OPEN
    # Next turn re-arms.
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    assert state.gates["rbg-review"].sticky is False


# --- (c) Escape-hatch degrades after N failures ------------------------------


def test_escape_hatch_degrades_after_threshold(router):
    """After RBG_REVIEW_DEGRADE_THRESHOLD consecutive Stop blocks, degrade to WARN."""
    state = _armed_state(router)
    verdicts = []
    for _ in range(5):
        r = router._dispatch_gates(_ctx("Stop"), state)
        verdicts.append(r.verdict)
    # First four DENY, fifth degrades to WARN-and-allow.
    assert verdicts[:4] == [GateVerdict.DENY] * 4
    assert verdicts[4] == GateVerdict.WARN


def test_escape_hatch_message_is_loud(router):
    """The degraded fire emits the loud, user-visible escape-hatch message."""
    state = _armed_state(router)
    result = None
    for _ in range(5):
        result = router._dispatch_gates(_ctx("Stop"), state)
    assert result.verdict == GateVerdict.WARN
    assert "ESCAPE-HATCH" in (result.system_message or "")


def test_deny_count_resets_on_next_turn(router):
    """The escape-hatch deny budget resets each turn (UPS re-arm)."""
    state = _armed_state(router)
    for _ in range(2):
        router._dispatch_gates(_ctx("Stop"), state)
    assert state.gates["rbg-review"].metrics.get("stop_deny_count") == 2
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].metrics.get("stop_deny_count") == 0


# --- Coexistence: rbg-review defers Ida, does not break it -------------------


def test_rbg_review_defers_ida_without_breaking_it(router, monkeypatch):
    """rbg-review DENY defers Ida (advisory) — Ida fires once rbg has cleared."""
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    _reinit_gates()
    state = SessionState.create("rbg-test", client_type="claude")
    router._dispatch_gates(_ups(), state)
    assert state.gates["ida"].status == GateStatus.CLOSED
    # rbg-review denies first; ida is deferred (still CLOSED, not consumed).
    r = router._dispatch_gates(_ctx("Stop"), state)
    assert r.verdict == GateVerdict.DENY
    assert state.gates["ida"].status == GateStatus.CLOSED
    # rbg runs -> clears; next Stop, ida fires its advisory and opens.
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    router._dispatch_gates(_ctx("Stop"), state)
    assert state.gates["ida"].status == GateStatus.OPEN
