"""Gate lifecycle — per-gate state transitions.

Tests gate-specific lifecycle behaviour where the transition sequence is
genuinely gate-specific (e.g. IDA re-arm on UPS, handover opens on skill).
"""

import os

import pytest

from tests.hooks.gate_helpers import (
    GateRegistry,
    GateStatus,
    GateVerdict,
    HookContext,
    SessionState,
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


# --- Handover read-only exemption (aops-16a15a05) ---


class TestHandoverReadOnlyExemption:
    """Handover gate exempts sessions that made no writes and claimed no task.

    AC from aops-16a15a05:
    - Read-only polecat session: handover gate OPEN at Stop, verdict ALLOW
    - Working polecat session: handover gate CLOSED at Stop, verdict DENY (block)
    - Max-fire loop-breaker: block→warn after N Stop blocks so a done session
      is not perpetually denied (Gemini watchdog fix, was aops-c5513f7f)
    """

    def _make_polecat_state(self, session_id: str) -> "SessionState":
        old = os.environ.get("POLECAT_SESSION_TYPE")
        os.environ["POLECAT_SESSION_TYPE"] = "polecat"
        try:
            return SessionState.create(session_id)
        finally:
            if old is not None:
                os.environ["POLECAT_SESSION_TYPE"] = old
            else:
                os.environ.pop("POLECAT_SESSION_TYPE", None)

    def test_read_only_polecat_allows_stop(self, router, monkeypatch):
        """Read-only session (no writes, no task claim) exits without handover block."""
        set_gate_modes(monkeypatch, handover="block", ida="off")
        reinit_gates_with_defaults()

        state = self._make_polecat_state("test-read-only-stop")
        # Gate starts CLOSED for polecat — but session_did_work is False
        assert state.gates["handover"].status == GateStatus.CLOSED
        assert state.session_did_work is False

        ctx = HookContext(
            session_id="test-read-only-stop",
            hook_event="Stop",
        )
        result = router._dispatch_gates(ctx, state)

        # Policy must NOT fire — read-only sessions are exempt from handover
        assert result is None or result.verdict == GateVerdict.ALLOW, (
            "Read-only polecat session must not be blocked by handover gate at Stop. "
            f"Got verdict={result.verdict.value if result else 'None'}"
        )

    def test_working_polecat_blocks_stop(self, router, monkeypatch):
        """Session that used a write tool is still blocked at Stop until handover."""
        set_gate_modes(monkeypatch, handover="block", ida="off")
        reinit_gates_with_defaults()

        state = self._make_polecat_state("test-working-stop")
        state.gates["handover"].status = GateStatus.CLOSED
        # Simulate a write tool having been used — triggers the full handover requirement
        state.session_did_work = True
        # Open QA so it doesn't mask the handover DENY
        state.gates["qa"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id="test-working-stop",
            hook_event="Stop",
        )
        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Working session must be blocked at Stop"
        assert result.verdict == GateVerdict.DENY, (
            f"Expected DENY from handover gate, got {result.verdict.value if result else 'None'}"
        )

    def test_set_session_did_work_on_task_claim(self, router, monkeypatch):
        """Claiming a task (update_task in_progress) sets session_did_work=True."""
        set_gate_modes(monkeypatch, handover="block", ida="off")
        reinit_gates_with_defaults()

        state = self._make_polecat_state("test-task-claim")
        assert state.session_did_work is False

        ctx = HookContext(
            session_id="test-task-claim",
            hook_event="PostToolUse",
            tool_name="mcp__plugin_aops-core_pkb__update_task",
            tool_input={"id": "task-abc", "updates": {"status": "in_progress"}},
        )
        router._dispatch_gates(ctx, state)

        assert state.session_did_work is True, (
            "Claiming a task must set session_did_work=True so the handover policy fires"
        )

    def test_set_session_did_work_on_write_tool(self, router, monkeypatch):
        """Using a write tool (Edit) sets session_did_work=True in polecat sessions."""
        set_gate_modes(monkeypatch, handover="block", ida="off")
        reinit_gates_with_defaults()

        state = self._make_polecat_state("test-write-tool")
        state.main_agent.current_task = "task-xyz"  # required for is_write_tool to fire
        assert state.session_did_work is False

        ctx = HookContext(
            session_id="test-write-tool",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "foo.py"},
        )
        router._dispatch_gates(ctx, state)

        assert state.session_did_work is True, (
            "Using a write tool must set session_did_work=True so the handover policy fires"
        )


# --- Max-fire loop-breaker for Gemini (aops-16a15a05, was aops-c5513f7f) ---


class TestStopDenyMaxFireDowngrade:
    """After N Stop DENY events from the same gate, downgrade to WARN.

    Prevents Gemini sessions (no Stop hook = no loop-breaker) from being
    held indefinitely against the termination watchdog.
    """

    def test_ida_block_downgrades_after_n_stops(self, router, monkeypatch):
        """IDA block mode downgrades block→warn after 3 consecutive Stop blocks."""
        set_gate_modes(monkeypatch, handover="off", ida="block", qa="off")
        # qa="off" is not a valid mode but we can force qa gate open
        monkeypatch.setenv("QA_GATE_MODE", "off")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        # Force QA open so only IDA fires
        state.gates["qa"].status = GateStatus.OPEN

        stop_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="Stop",
        )
        ups_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="UserPromptSubmit",
            raw_input={"prompt": "continue"},
        )

        # Turn 1: IDA fires block, gate opens (fire-once)
        r1 = router._dispatch_gates(stop_ctx, state)
        assert r1 is not None and r1.verdict == GateVerdict.DENY, (
            f"Turn 1 should be DENY, got {r1.verdict.value if r1 else None}"
        )
        assert state.gates["ida"].status == GateStatus.OPEN
        # Re-arm for turn 2
        router._dispatch_gates(ups_ctx, state)

        # Turn 2: IDA fires block again
        r2 = router._dispatch_gates(stop_ctx, state)
        assert r2 is not None and r2.verdict == GateVerdict.DENY, (
            f"Turn 2 should be DENY, got {r2.verdict.value if r2 else None}"
        )
        router._dispatch_gates(ups_ctx, state)

        # Turn 3: max-fire threshold reached → downgrade to WARN
        r3 = router._dispatch_gates(stop_ctx, state)
        assert r3 is not None and r3.verdict == GateVerdict.WARN, (
            f"Turn 3 should downgrade to WARN (max-fire breaker), "
            f"got {r3.verdict.value if r3 else None}"
        )

    def test_handover_block_downgrades_after_n_stops(self, router, monkeypatch):
        """Handover block mode downgrades after N Stop blocks so Gemini can exit."""
        set_gate_modes(monkeypatch, handover="block", ida="off")
        monkeypatch.setenv("QA_GATE_MODE", "off")
        # The handover UPS re-arm trigger has session_type_filter=["polecat","crew"],
        # so the test needs a polecat session to re-arm correctly between turns.
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "polecat")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("handover")
        # session_did_work already set to True by make_gate_trigger_state
        state.gates["qa"].status = GateStatus.OPEN

        stop_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="Stop",
        )
        ups_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="UserPromptSubmit",
            raw_input={"prompt": "continue"},
        )

        # Turn 1 and 2: DENY
        r1 = router._dispatch_gates(stop_ctx, state)
        assert r1 is not None and r1.verdict == GateVerdict.DENY
        router._dispatch_gates(ups_ctx, state)

        r2 = router._dispatch_gates(stop_ctx, state)
        assert r2 is not None and r2.verdict == GateVerdict.DENY
        router._dispatch_gates(ups_ctx, state)

        # Turn 3: WARN (downgraded)
        r3 = router._dispatch_gates(stop_ctx, state)
        assert r3 is not None and r3.verdict == GateVerdict.WARN, (
            f"Handover should downgrade to WARN after 3 blocks, "
            f"got {r3.verdict.value if r3 else None}"
        )
