"""Output channel routing — parameterised across gates × events × verdicts.

Verifies that advisory text reaches the agent (via `reason`) and never leaks
to user-visible channels (`stopReason`, `systemMessage`). Parameterised across
all stop-gates: handover, qa, ida.

Adding a new stop-gate: append to STOP_GATES in gate_helpers.py.
"""

import json

import pytest
from hooks.schemas import CanonicalHookOutput, ClaudeStopHookOutput

from tests.hooks.gate_helpers import (
    ADVISORY,
    STOP_GATES,
    GateVerdict,
    make_gate_trigger_context,
    make_gate_trigger_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# --- Parameterised across all stop-gates ---


class TestAdvisoryReachesAgent:
    """Advisory text reaches agent via decision=block + reason for all stop-gates."""

    @pytest.mark.parametrize("gate_name", STOP_GATES)
    def test_warn_mode_advisory_reaches_agent_via_reason(self, router, monkeypatch, gate_name):
        set_gate_modes(monkeypatch, **{gate_name: "warn"})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        assert result is not None and result.verdict == GateVerdict.WARN

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        assert output.decision == "block", (
            f"{gate_name} warn mode must use decision='block' to deliver advisory. "
            f"Got decision={output.decision!r}."
        )
        assert output.reason, f"{gate_name} warn mode must populate reason with advisory text"

    @pytest.mark.parametrize("gate_name", STOP_GATES)
    def test_block_mode_advisory_reaches_agent(self, router, monkeypatch, gate_name):
        set_gate_modes(monkeypatch, **{gate_name: "block"})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        assert result is not None and result.verdict == GateVerdict.DENY

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        assert output.decision == "block", f"{gate_name} block mode must block Stop"


class TestAdvisoryDoesNotLeakToUser:
    """Advisory text must not appear in user-visible channels for any stop-gate."""

    @pytest.mark.parametrize("gate_name", STOP_GATES)
    def test_advisory_does_not_leak_to_stop_reason(self, router, monkeypatch, gate_name):
        set_gate_modes(monkeypatch, **{gate_name: "warn"})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")

        assert output.stopReason is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.stopReason or ""
        ), f"{gate_name}: advisory leaked into user-visible stopReason"

    @pytest.mark.parametrize("gate_name", STOP_GATES)
    def test_advisory_does_not_leak_to_system_message(self, router, monkeypatch, gate_name):
        set_gate_modes(monkeypatch, **{gate_name: "warn"})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")

        assert output.systemMessage is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.systemMessage or ""
        ), f"{gate_name}: advisory leaked into user-visible systemMessage"


# --- Synthetic canonical output tests (not gate-specific) ---


class TestCanonicalChannelRouting:
    """Channel routing from CanonicalHookOutput → Claude Stop output."""

    def test_warn_with_advisory_routes_to_reason(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        assert output.decision == "block"
        assert output.reason == ADVISORY

    def test_stop_does_not_emit_hook_specific_output(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        assert not hasattr(output, "hookSpecificOutput") or output.hookSpecificOutput is None

    def test_session_end_same_routing_as_stop(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "SessionEnd")
        assert output.decision == "block"
        assert output.reason == ADVISORY

    def test_approve_when_no_advisory(self, router):
        canonical = CanonicalHookOutput(
            verdict="warn", context_injection=None, system_message="short note"
        )
        output = router.output_for_claude(canonical, "Stop")
        assert output.decision == "approve"
        assert output.stopReason == "short note"

    def test_deny_routes_advisory_to_agent_summary_to_user(self, router):
        canonical = CanonicalHookOutput(
            verdict="deny",
            context_injection=ADVISORY,
            system_message="Handover required before stop",
        )
        output = router.output_for_claude(canonical, "Stop")
        assert output.decision == "block"
        assert output.reason == ADVISORY
        assert output.stopReason == "Handover required before stop"
        assert output.systemMessage == "Handover required before stop"
        assert "SYSTEM HOOK INSTRUCTION" not in (output.stopReason or "")
        assert "SYSTEM HOOK INSTRUCTION" not in (output.systemMessage or "")


# --- JSON envelope integrity ---


class TestStopHookJsonEnvelope:
    """Serialised JSON envelope carries advisory only in agent channels."""

    def test_serialised_json_carries_advisory_in_reason_not_stop_reason(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        payload = json.loads(output.model_dump_json(exclude_none=True))

        assert payload.get("decision") == "block"
        assert payload.get("reason") == ADVISORY

        for user_field in ("stopReason", "systemMessage"):
            value = payload.get(user_field)
            if value is not None:
                assert "SYSTEM HOOK INSTRUCTION" not in value, (
                    f"Advisory leaked into {user_field!r} of serialised JSON"
                )
