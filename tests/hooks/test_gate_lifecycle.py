"""Gate lifecycle — per-gate state transitions.

Tests gate-specific lifecycle behaviour where the transition sequence is
genuinely gate-specific (e.g. IDA re-arm on UPS, handover opens on skill).
"""

import pytest

from tests.hooks.gate_helpers import (
    GateRegistry,
    GateStatus,
    GateVerdict,
    HookContext,
    flatten_scenarios,
    make_context,
    make_gate_trigger_context,
    make_gate_trigger_state,
    make_session_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# --- Handover gate opens ---


class TestHandoverGateOpens:
    """Handover gate opens on /end-session or /dump skill completion."""

    SCENARIOS = flatten_scenarios("handover_gate_opens")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_handover_gate_opens_on_event(self, router, scenario):
        state = make_session_state(scenario)
        ctx = make_context(scenario)

        router._dispatch_gates(ctx, state)

        assert state.gates["handover"].status == GateStatus.OPEN, (
            f"[{scenario['id']}] Handover gate should be OPEN in response, "
            f"but got {state.gates['handover'].status}"
        )


# --- IDA per-turn lifecycle ---


class TestIdaPerTurnLifecycle:
    """IDA gate per-turn lifecycle: armed → fires → opens → re-armed on UPS."""

    def test_ida_starts_closed(self, monkeypatch):
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()
        GateRegistry.initialize()
        ida_gate = GateRegistry.get_gate("ida")
        assert ida_gate is not None, "IDA gate must be registered"
        assert ida_gate.config.initial_status == GateStatus.CLOSED, (
            "IDA gate must start CLOSED (armed) so it fires on the first Stop"
        )

    def test_ida_opens_after_firing_on_stop(self, router, monkeypatch):
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = make_gate_trigger_context("ida")

        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must be OPEN after firing (so retried Stops aren't blocked)"
        )

    def test_ida_does_not_fire_twice_same_turn(self, router, monkeypatch):
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        stop_ctx = make_gate_trigger_context("ida")

        first_result = router._dispatch_gates(stop_ctx, state)
        assert first_result is not None and first_result.verdict == GateVerdict.WARN
        assert state.gates["ida"].status == GateStatus.OPEN

        router._dispatch_gates(stop_ctx, state)
        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must remain OPEN on a second Stop in the same turn"
        )

    def test_ida_rearms_on_user_prompt_submit(self, router, monkeypatch):
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        stop_ctx = make_gate_trigger_context("ida")
        ups_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="UserPromptSubmit",
            raw_input={"prompt": "continue working"},
        )

        router._dispatch_gates(stop_ctx, state)
        assert state.gates["ida"].status == GateStatus.OPEN

        router._dispatch_gates(ups_ctx, state)
        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "IDA gate must be re-armed (CLOSED) on UserPromptSubmit"
        )

    def test_ida_block_mode_opens_after_firing(self, router, monkeypatch):
        set_gate_modes(monkeypatch, ida="block")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = make_gate_trigger_context("ida")

        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must open after firing in block mode so a retried Stop "
            "is not blocked again in the same turn"
        )
