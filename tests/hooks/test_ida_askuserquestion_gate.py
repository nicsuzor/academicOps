"""IDA honesty gate — AskUserQuestion mid-turn blocker challenge (aops-5c01b2a9).

Tests the three-component design:
  B: AskUserQuestion PreToolUse re-closes the IDA gate (when OPEN), so the next
     Stop is still armed. Lifecycle: block-once -> allow-retry -> re-close-on-AUQ
     -> re-block-next-Stop.
  C: AskUserQuestion PreToolUse injects the capability-verification advisory
     (ida.askuserquestion_reminder) into the agent's context at the moment the
     blocker is manufactured — regardless of gate open/closed state.

Hard constraint: AskUserQuestion is never denied. This holds NOT because each
gate is individually checked, but because the gate engine consults the global
``is_never_block`` list before emitting any deny/block on a PreToolUse tool, and
no individual gate may override that list (lib/tool_categories.py). The
structural proof of the class-wide guarantee is
``test_askuserquestion_globally_never_block``; the IDA-mode sweep below
additionally verifies the IDA gate honours it across warn/block/deny.
"""

from __future__ import annotations

from lib.template_registry import TemplateRegistry
from lib.tool_categories import is_never_block

from tests.hooks.gate_helpers import (
    GateStatus,
    GateVerdict,
    HookContext,
    make_gate_trigger_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# Structural identity, not a prose token: the AskUserQuestion trigger injects the
# rendered content of context_key "ida.askuserquestion_reminder" (definitions.py).
# Assert against that render — never a substring like "capability" — so the
# advisory wording stays free to change without breaking the routing test
# ({#judgment-non-delegable}).
_AUQ_CONTEXT_KEY = "ida.askuserquestion_reminder"


def _rendered_auq_advisory() -> str:
    """The exact text the AskUserQuestion advisory template renders to."""
    return TemplateRegistry.instance().render(_AUQ_CONTEXT_KEY, {})


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
        assert result.context_injection == _rendered_auq_advisory(), (
            "Injected advisory must be the rendered ida.askuserquestion_reminder "
            f"template, not arbitrary text. Got: {result.context_injection!r}"
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
        assert result.context_injection == _rendered_auq_advisory()

    def test_askuserquestion_never_denied_across_ida_modes(self, router, monkeypatch):
        """The IDA gate never denies AskUserQuestion, across every IDA mode.

        Scoped deliberately to the IDA gate. The class-wide guarantee ("never
        denied on ANY path — all gates, all clients") is not provable by
        enumerating gates here; it is proved structurally at its chokepoint by
        ``test_askuserquestion_globally_never_block``.
        """
        for mode in ("warn", "block", "deny"):
            set_gate_modes(monkeypatch, ida=mode)
            reinit_gates_with_defaults()

            state = make_gate_trigger_state("ida")
            ctx = _auq_pretool_ctx(f"test-ida-auq-never-deny-{mode}")

            result = router._dispatch_gates(ctx, state)

            verdict = getattr(result, "verdict", None)
            verdict_value = getattr(verdict, "value", verdict) if verdict else None
            assert verdict_value not in ("deny", "block"), (
                f"IDA gate must NEVER deny AskUserQuestion (ida mode={mode!r}). "
                f"Got verdict={verdict_value!r}, result={result!r}"
            )

    def test_askuserquestion_globally_never_block(self):
        """Structural proof of the class-wide claim: NO gate can deny AskUserQuestion.

        "AskUserQuestion is never denied on any path" is true not because each
        gate/mode/client is enumerated, but because the gate engine consults the
        global ``is_never_block`` list before emitting any deny/block on a
        PreToolUse tool, and no individual gate may override it
        (lib/tool_categories.py; engine.py PreToolUse guard). Asserting that
        chokepoint invariant proves the universal claim over the whole class.
        """
        assert is_never_block("AskUserQuestion"), (
            "AskUserQuestion must be in the global never-block set — that single "
            "guard is what makes 'never denied on any path' true across all gates."
        )

    def test_askuserquestion_no_advisory_when_ida_off(self, router, monkeypatch):
        """IDA off: AskUserQuestion gets no advisory injection."""
        set_gate_modes(monkeypatch, ida="off")
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("ida")
        ctx = _auq_pretool_ctx()

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.context_injection != _rendered_auq_advisory(), (
                "IDA off: the capability advisory must NOT be injected. "
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
        assert result_closed.context_injection == _rendered_auq_advisory()

        # Test when gate is OPEN (after a Stop fire-once)
        state_open = make_gate_trigger_state("ida")
        state_open.gates["ida"].status = GateStatus.OPEN
        ctx_open = _auq_pretool_ctx("test-auq-open")
        result_open = router._dispatch_gates(ctx_open, state_open)
        assert result_open is not None and result_open.context_injection
        assert result_open.context_injection == _rendered_auq_advisory()


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
