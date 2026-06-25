"""IDA honesty gate — AskUserQuestion mid-turn blocker challenge (aops-5c01b2a9).

Tests the three-component design:
  B: AskUserQuestion PreToolUse re-closes the IDA gate (when OPEN), so the next
     Stop is still armed. Lifecycle: block-once -> allow-retry -> re-close-on-AUQ
     -> re-block-next-Stop.
  C: AskUserQuestion PreToolUse injects the capability-verification advisory
     (ida.askuserquestion_reminder) into the agent's context at the moment the
     blocker is manufactured — regardless of gate open/closed state.

Hard constraint (verified): AskUserQuestion is NEVER denied on any path.
"""

from __future__ import annotations

from tests.hooks.gate_helpers import (
    GateStatus,
    GateVerdict,
    HookContext,
    make_gate_trigger_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

_CAPABILITY_MARKER = "capability"  # present in ida-askuserquestion-reminder.md


def _auq_pretool_ctx(session_id: str = "test-ida-auq") -> HookContext:
    """PreToolUse context for AskUserQuestion."""
    return HookContext(
        session_id=session_id,
        client_type="claude",
        hook_event="PreToolUse",
        tool_name="AskUserQuestion",
        tool_input={"question": "Can you run agy?"},
    )


def _stop_ctx(session_id: str = "test-ida-auq") -> HookContext:
    """Stop context (IDA fires here)."""
    return HookContext(
        session_id=session_id,
        client_type="claude",
        hook_event="Stop",
    )


# ---------------------------------------------------------------------------
# Component C — advisory inject at AskUserQuestion
# ---------------------------------------------------------------------------


class TestIdaAskUserQuestionAdvisoryInject:
    """Component C: capability-verification reminder injected on AskUserQuestion."""

    def test_askuserquestion_injects_advisory_when_ida_active(self, router, monkeypatch):
        """IDA active (warn mode): AskUserQuestion gets capability reminder."""
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = _auq_pretool_ctx()

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Expected a gate result for AskUserQuestion when IDA active"
        assert result.context_injection, (
            "IDA active: AskUserQuestion must receive capability-verification advisory "
            f"in context_injection. Got: {result!r}"
        )
        assert _CAPABILITY_MARKER in result.context_injection, (
            f"Advisory must contain '{_CAPABILITY_MARKER}'. Got: {result.context_injection!r}"
        )

    def test_askuserquestion_injects_advisory_in_block_mode(self, router, monkeypatch):
        """IDA block mode: AskUserQuestion still gets advisory (advisory-only, never deny)."""
        set_gate_modes(monkeypatch, ida="block")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = _auq_pretool_ctx()

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Expected advisory result for AskUserQuestion in block mode"
        assert result.context_injection, (
            "IDA block mode: AskUserQuestion must still receive advisory (not a deny). "
            f"Got: {result!r}"
        )
        assert _CAPABILITY_MARKER in result.context_injection

    def test_askuserquestion_never_denied(self, router, monkeypatch):
        """Hard constraint: AskUserQuestion must NEVER receive a deny/block verdict."""
        for mode in ("warn", "block", "deny"):
            set_gate_modes(monkeypatch, ida=mode)
            reinit_gates_with_defaults()

            state = make_gate_trigger_state("ida")
            ctx = _auq_pretool_ctx(f"test-ida-auq-never-deny-{mode}")

            result = router._dispatch_gates(ctx, state)

            verdict = getattr(result, "verdict", None)
            verdict_value = getattr(verdict, "value", verdict) if verdict else None
            assert verdict_value not in ("deny", "block"), (
                f"AskUserQuestion must NEVER be denied (ida mode={mode!r}). "
                f"Got verdict={verdict_value!r}, result={result!r}"
            )

    def test_askuserquestion_no_advisory_when_ida_off(self, router, monkeypatch):
        """IDA off: AskUserQuestion gets no advisory injection."""
        set_gate_modes(monkeypatch, ida="off")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = _auq_pretool_ctx()

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert (
                not result.context_injection or _CAPABILITY_MARKER not in result.context_injection
            ), (
                "IDA off: capability advisory must NOT be injected. "
                f"Got: {result.context_injection!r}"
            )

    def test_askuserquestion_advisory_fires_regardless_of_gate_status(self, router, monkeypatch):
        """Advisory fires both when gate is CLOSED (armed) and OPEN (fired-once)."""
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        # Test when gate is CLOSED (armed — default state)
        state_closed = make_gate_trigger_state("ida")
        assert state_closed.gates["ida"].status == GateStatus.CLOSED
        ctx = _auq_pretool_ctx("test-auq-closed")
        result_closed = router._dispatch_gates(ctx, state_closed)
        assert result_closed is not None and result_closed.context_injection
        assert _CAPABILITY_MARKER in result_closed.context_injection

        # Test when gate is OPEN (after a Stop fire-once)
        state_open = make_gate_trigger_state("ida")
        state_open.gates["ida"].status = GateStatus.OPEN
        ctx_open = _auq_pretool_ctx("test-auq-open")
        result_open = router._dispatch_gates(ctx_open, state_open)
        assert result_open is not None and result_open.context_injection
        assert _CAPABILITY_MARKER in result_open.context_injection


# ---------------------------------------------------------------------------
# Component B — state machine re-close on AskUserQuestion
# ---------------------------------------------------------------------------


class TestIdaAskUserQuestionReClose:
    """Component B: AskUserQuestion PreToolUse re-closes the gate when OPEN."""

    def test_askuserquestion_recloses_gate_when_open(self, router, monkeypatch):
        """When IDA is OPEN (fired once), AskUserQuestion re-closes it."""
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        state.gates["ida"].status = GateStatus.OPEN  # simulate post-Stop open

        ctx = _auq_pretool_ctx()
        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "Component B: AskUserQuestion PreToolUse must re-close IDA gate when OPEN. "
            f"Got status={state.gates['ida'].status!r}"
        )

    def test_askuserquestion_closed_stays_closed(self, router, monkeypatch):
        """When gate is already CLOSED, AskUserQuestion is a no-op for gate status."""
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        assert state.gates["ida"].status == GateStatus.CLOSED

        ctx = _auq_pretool_ctx()
        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "Gate already CLOSED — AskUserQuestion must not change it. "
            f"Got status={state.gates['ida'].status!r}"
        )

    def test_b_state_machine_full_lifecycle(self, router, monkeypatch):
        """Full B state machine: block-once → allow-retry → re-close-on-AUQ → re-block-Stop.

        Sequence:
          1. Stop (gate CLOSED) → IDA fires WARN, gate opens (fire-once)
          2. Stop again (gate OPEN) → IDA does NOT fire (gate already open)
          3. AskUserQuestion PreToolUse (gate OPEN) → gate re-closes + inject advisory
          4. Stop (gate re-CLOSED) → IDA fires WARN again
        """
        set_gate_modes(monkeypatch, ida="warn")
        reinit_gates_with_defaults()

        session_id = "test-b-state-machine"
        state = make_gate_trigger_state("ida")
        assert state.gates["ida"].status == GateStatus.CLOSED, "precondition: gate starts CLOSED"

        # Step 1: Stop fires → gate opens
        stop_ctx = _stop_ctx(session_id)
        result1 = router._dispatch_gates(stop_ctx, state)
        assert result1 is not None and result1.verdict == GateVerdict.WARN, (
            f"Step 1: Stop must WARN when IDA CLOSED. Got {result1!r}"
        )
        assert state.gates["ida"].status == GateStatus.OPEN, (
            "Step 1: gate must OPEN after Stop fire-once"
        )

        # Step 2: Stop again → gate is OPEN, no fire
        result2 = router._dispatch_gates(stop_ctx, state)
        if result2 is not None:
            verdict2 = getattr(result2.verdict, "value", result2.verdict)
            assert verdict2 not in ("deny", "warn"), (
                f"Step 2: IDA must not fire on second Stop (gate OPEN). Got {result2!r}"
            )
        assert state.gates["ida"].status == GateStatus.OPEN, "Step 2: gate must remain OPEN"

        # Step 3: AskUserQuestion → re-close gate + inject advisory
        auq_ctx = _auq_pretool_ctx(session_id)
        result3 = router._dispatch_gates(auq_ctx, state)
        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "Step 3: AskUserQuestion must re-close IDA gate"
        )
        assert result3 is not None and result3.context_injection, (
            "Step 3: AskUserQuestion must inject advisory"
        )

        # Step 4: Stop again (gate re-CLOSED) → IDA fires again
        result4 = router._dispatch_gates(stop_ctx, state)
        assert result4 is not None and result4.verdict == GateVerdict.WARN, (
            f"Step 4: Stop must WARN again after re-close. Got {result4!r}"
        )
        assert state.gates["ida"].status == GateStatus.OPEN, (
            "Step 4: gate must OPEN after re-firing"
        )
