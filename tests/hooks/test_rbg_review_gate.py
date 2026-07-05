#!/usr/bin/env python3
"""Tests for the rbg-review Stop gate.

Reworked AGAIN (turn: destroy in-code session-type branching) from the
original per-surface split (epic-f490bb11, itself a rework of #1928). The
gate is now a single, uniform state machine for EVERY session type — armed
(CLOSED) from session start, re-arming CLOSED on every UserPromptSubmit, no
session_type_filter anywhere in the gate config. The ONLY lever for "does
this actually bite" is RBG_REVIEW_GATE_MODE:

- mode=block: DENIES Stop while armed until the rbg subagent runs (structural
  trigger: Stop + armed flag — NOT a content sniff). CLEARS (OPEN) when rbg
  runs, then exit is allowed.
- mode=off (the built-in code default for an ad hoc CLI session with no
  polecat.yaml override): the gate still mechanically arms/re-arms, but the
  block/warn policies never match "off", so Stop is never blocked.
- ESCAPE-HATCH: after RBG_REVIEW_DEGRADE_THRESHOLD consecutive Stop blocks,
  degrades DENY -> WARN-and-allow with a loud message so a broken rbg dispatch
  cannot permanently trap the session.

Drives the gate through router._dispatch_gates with a real SessionState +
HookContext, mirroring test_handover_gate_regression.py.
"""

import importlib
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
    monkeypatch.setenv("RBG_GATE_MODE", "off")
    _reinit_gates()
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _ctx(event: str, **kw) -> HookContext:
    return HookContext(session_id="rbg-test", client_type="claude", hook_event=event, **kw)


def _ups(prompt: str = "do a thing") -> HookContext:
    return _ctx("UserPromptSubmit", raw_input={"prompt": prompt})


def _state(session_id: str = "rbg-test") -> SessionState:
    return SessionState.create(session_id, client_type="claude")


def _armed_state(router) -> SessionState:
    """Fresh session, armed by a UserPromptSubmit (gate CLOSED)."""
    state = _state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED
    return state


# --- LIFECYCLE: armed for every session type; mode gates the consequence ----


def test_gate_starts_armed_from_session_start(router):
    """Gate is CLOSED (armed) from session start — every session type alike."""
    state = _state()
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


def test_ups_rearms_the_gate(router):
    """UserPromptSubmit re-arms the gate (so the exit Stop is armed)."""
    state = _state()
    state.gates["rbg-review"].status = GateStatus.OPEN
    router._dispatch_gates(_ups(), state)
    assert state.gates["rbg-review"].status == GateStatus.CLOSED


# --- SCOPING: mode=off makes the (still-armed) gate inert --------------------


def test_mode_off_stop_never_blocks_per_turn(router, monkeypatch):
    """mode=off: Stop is ALLOWED every turn even though the gate keeps arming.

    This is the core of the env-var-only scoping: an ad hoc CLI session with
    no polecat.yaml override (RBG_REVIEW_GATE_MODE's built-in default is
    "off") must NOT eat the rbg delay on every turn (the bug the original
    block-every-stop PR caused, #1928) — achieved purely by mode, never by a
    different in-code lifecycle for that surface.
    """
    monkeypatch.setenv("RBG_REVIEW_GATE_MODE", "off")
    _reinit_gates()
    state = _state()
    for _ in range(3):
        router._dispatch_gates(_ups(), state)
        assert state.gates["rbg-review"].status == GateStatus.CLOSED  # still arms
        result = router._dispatch_gates(_ctx("Stop"), state)
        # Other Stop gates are off, so an allowed Stop yields no blocking verdict.
        assert result is None or result.verdict == GateVerdict.ALLOW


def test_mode_warn_still_fires_advisory(router, monkeypatch):
    """mode=warn: fires a hard-block-once (D1 — warn now DENYs to force one
    continuation, then the warn-mode fire-once trigger opens the gate)."""
    monkeypatch.setenv("RBG_REVIEW_GATE_MODE", "warn")
    _reinit_gates()
    state = _armed_state(router)
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is not None
    assert result.verdict == GateVerdict.DENY
    # warn-mode fire-once: gate opens after firing so a retried Stop passes.
    assert state.gates["rbg-review"].status == GateStatus.OPEN


# --- (a) Stop DENIED when armed and rbg has not run (mode=block) ------------


def test_stop_denied_when_armed_and_rbg_not_run(router):
    """Exit: Stop is DENIED while armed and rbg has not run."""
    state = _armed_state(router)
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is not None
    assert result.verdict == GateVerdict.DENY
    # rbg agent definition lives in aops-pkb since the aops-pkb extraction.
    assert "subagent_type='aops-pkb:rbg'" in (result.context_injection or "")


def test_stop_stays_denied_across_retries_no_fire_once_leak(router):
    """Repeated Stops without rbg stay DENIED — no fire-once 'open on Stop' leak.

    This is the key difference from qa/handover/ida: those open on the first
    Stop so a retried Stop passes. rbg-review must NOT — that would let the
    second (exit) Stop pass without rbg having run.
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
    """Sticky latch: edits after rbg ran do not re-block / re-arm the same turn.

    This is the gate-discharge re-trigger invariant for THIS gate: the rbg
    discharge completing, and any follow-up edit, must NOT re-arm the gate.
    """
    state = _armed_state(router)
    router._dispatch_gates(_ctx("SubagentStop", subagent_type="aops-core:rbg"), state)
    # An edit (PostToolUse write) must not re-close the gate this turn.
    router._dispatch_gates(
        _ctx("PostToolUse", tool_name="Edit", tool_input={"file_path": "foo.py"}), state
    )
    assert state.gates["rbg-review"].status == GateStatus.OPEN
    # A retried Stop after the rbg discharge + edit is still ALLOWED (no loop).
    result = router._dispatch_gates(_ctx("Stop"), state)
    assert result is None or result.verdict == GateVerdict.ALLOW
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
    state = _state()
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


def test_ida_still_fires_when_rbg_review_mode_off(router, monkeypatch):
    """Ida is NOT suppressed when rbg-review mode is off: rbg-review is inert, ida still fires."""
    monkeypatch.setenv("RBG_REVIEW_GATE_MODE", "off")
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    _reinit_gates()
    state = _state()
    router._dispatch_gates(_ups(), state)
    assert state.gates["ida"].status == GateStatus.CLOSED
    assert state.gates["rbg-review"].status == GateStatus.CLOSED  # armed but inert
    r = router._dispatch_gates(_ctx("Stop"), state)
    # rbg-review mode=off is inert; ida fires its hard-block-once (D1: warn now
    # DENYs) and opens.
    assert r is not None
    assert r.verdict == GateVerdict.DENY
    assert state.gates["ida"].status == GateStatus.OPEN
