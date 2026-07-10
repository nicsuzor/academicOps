"""Gate verdict logic — parameterised across gates × modes.

Tests that the gate system produces correct block/warn/allow verdicts.
Uses fixture data for scenario-driven tests and parameterised mode overrides.
"""

import pytest

from tests.hooks.gate_helpers import (
    GateStatus,
    GateVerdict,
    flatten_scenarios,
    make_context,
    make_gate_trigger_context,
    make_gate_trigger_state,
    make_session_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# --- Gate mode override parameterisation ---

_GATE_MODE_CASES = [
    ("rbg", "warn", GateVerdict.WARN),
    ("rbg", "block", GateVerdict.DENY),
    # Stop-triggered gates: warn mode delivers non-blockingly (WARN, no forced
    # continuation); block mode forces a continuation (DENY). The warn-vs-block
    # difference is now both the verdict AND the re-fire latch (warn=fire-once,
    # block=persist).
    ("qa", "warn", GateVerdict.WARN),
    ("qa", "block", GateVerdict.DENY),
    ("handover", "warn", GateVerdict.WARN),
    ("handover", "block", GateVerdict.DENY),
    ("ida", "warn", GateVerdict.WARN),
    ("ida", "block", GateVerdict.DENY),
]


class TestGateModeConfigOverrides:
    """Gate modes control enforcement for all gates."""

    @pytest.mark.parametrize(
        "gate_name,mode,expected_verdict",
        _GATE_MODE_CASES,
        ids=[f"{g}-{m}" for g, m, _ in _GATE_MODE_CASES],
    )
    def test_gate_mode_verdict(self, router, monkeypatch, gate_name, mode, expected_verdict):
        kwargs: dict[str, str] = {gate_name: mode}
        set_gate_modes(monkeypatch, **kwargs)
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)

        if expected_verdict is None:
            assert result is None, (
                f"{gate_name} gate with mode={mode} should be ALLOW (None), "
                f"got {result.verdict.value if result else 'N/A'}"
            )
            return

        assert result is not None, (
            f"{gate_name} gate with mode={mode} should produce a verdict, got None"
        )
        assert result.verdict == expected_verdict, (
            f"{gate_name} gate with mode={mode}: "
            f"expected {expected_verdict.value}, got {result.verdict.value}"
        )


class TestTwoModeLatch:
    """D1 two-mode latch (client-agnostic — pure GateStatus, no stop_hook_active).

    Warn emits WARN (non-blocking) and block emits DENY (verdict tested
    above); this pins the LATCH that distinguishes their re-fire behavior:
    `warn` fires once then latches the gate OPEN (fire-once),
    while `block` keeps the gate CLOSED and re-fires every Stop until a
    satisfaction trigger opens it (persist-until-satisfied). Uses `handover`
    (no PKB/temp dependency) for the warn-vs-block contrast, and `ida` for the
    fire-once-in-both-modes case (ida has no satisfaction predicate).
    """

    def test_handover_warn_fires_once_then_latches_open(self, router, monkeypatch):
        set_gate_modes(monkeypatch, handover="warn", qa="off", ida="off")
        reinit_gates_with_defaults()
        state = make_gate_trigger_state("handover")  # sets turn_did_work
        ctx = make_gate_trigger_context("handover")

        r1 = router._dispatch_gates(ctx, state)
        assert r1 is not None and r1.verdict == GateVerdict.WARN
        assert state.gates["handover"].status == GateStatus.OPEN, (
            "warn is fire-once: the gate latches OPEN after the first delivery"
        )
        r2 = router._dispatch_gates(ctx, state)
        assert r2 is None or r2.verdict != GateVerdict.WARN, (
            "warn must not re-fire on a retried Stop in the same turn"
        )

    def test_handover_block_persists_closed_and_refires(self, router, monkeypatch):
        set_gate_modes(monkeypatch, handover="block", qa="off", ida="off")
        reinit_gates_with_defaults()
        state = make_gate_trigger_state("handover")
        ctx = make_gate_trigger_context("handover")

        r1 = router._dispatch_gates(ctx, state)
        assert r1 is not None and r1.verdict == GateVerdict.DENY
        assert state.gates["handover"].status == GateStatus.CLOSED, (
            "block persists: no fire-once, the gate stays CLOSED (block-until-satisfied)"
        )
        r2 = router._dispatch_gates(ctx, state)
        assert r2 is not None and r2.verdict == GateVerdict.DENY, (
            "block re-fires on every Stop until a satisfaction trigger opens the gate"
        )

    @pytest.mark.parametrize("mode", ["warn", "block"])
    def test_ida_is_fire_once_in_both_modes(self, router, monkeypatch, mode):
        # ida has no satisfaction predicate, so block == warn == fire-once
        # (block would otherwise be an unescapable loop). block hard-blocks
        # (DENY); warn delivers non-blockingly (WARN). Both fire exactly once.
        set_gate_modes(monkeypatch, ida=mode, qa="off", handover="off")
        reinit_gates_with_defaults()
        state = make_gate_trigger_state("ida")
        ctx = make_gate_trigger_context("ida")

        expected = GateVerdict.DENY if mode == "block" else GateVerdict.WARN
        r1 = router._dispatch_gates(ctx, state)
        assert r1 is not None and r1.verdict == expected, f"ida {mode} fires {expected.value} once"
        assert state.gates["ida"].status == GateStatus.OPEN, (
            f"ida {mode} is fire-once (latches OPEN) regardless of mode"
        )


# --- Read-only bypass ---


class TestReadOnlyBypassesEnforcer:
    """Read-only tools bypass enforcer gate (unlike write tools)."""

    SCENARIOS = flatten_scenarios("read_only_bypasses_enforcer")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_bypasses_enforcer(self, router, scenario):
        state = make_session_state(scenario)
        ctx = make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' "
                f"should bypass enforcer gate, got {result.verdict.value}"
            )
