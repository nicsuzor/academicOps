"""Output channel routing — parameterised across gates × events × verdicts.

Verifies that advisory text reaches the agent (via the correct channel per
event type) and never leaks to user-visible channels. Covers:

- Stop/SessionEnd: advisory → ``reason`` (agent), summary → ``stopReason``/
  ``systemMessage`` (user)
- General HSO events (PreToolUse, UserPromptSubmit, PostToolUse): advisory →
  ``hookSpecificOutput.additionalContext`` (agent), summary → ``systemMessage``
  (user)
- Non-HSO events (SessionStart, SubagentStart, etc.): no ``hookSpecificOutput``
  emitted; ``context_injection`` has no delivery channel and must not silently
  accumulate

Adding a new stop-gate: append to STOP_GATES in gate_helpers.py.
"""

import json

import pytest
from hooks.router import _strip_hook_markers
from hooks.schemas import (
    CanonicalHookOutput,
    ClaudeGeneralHookOutput,
    ClaudeStopHookOutput,
)

from tests.hooks.gate_helpers import (
    ADVISORY,
    ALL_HOOK_EVENTS,
    CLAUDE_ACCEPTED_HOOK_EVENT_NAMES,
    STOP_GATES,
    GateVerdict,
    make_gate_trigger_context,
    make_gate_trigger_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# The Stop `reason` field is user-visible (Claude Code renders a blocking Stop
# hook's reason to the user). The router therefore strips the
# <SYSTEM HOOK INSTRUCTION> scaffold before placing the advisory in `reason`.
# The advisory BODY still reaches the agent — only the marker tags are removed.
ADVISORY_IN_REASON = _strip_hook_markers(ADVISORY)

# Events that use hookSpecificOutput.additionalContext for agent delivery
HSO_EVENTS = sorted(CLAUDE_ACCEPTED_HOOK_EVENT_NAMES)

# Events that use decision=block + reason for agent delivery
STOP_EVENTS = ["Stop", "SessionEnd"]

# Events where hookSpecificOutput is NOT accepted by Claude Code
NON_HSO_EVENTS = sorted(
    set(ALL_HOOK_EVENTS) - CLAUDE_ACCEPTED_HOOK_EVENT_NAMES - {"Stop", "SessionEnd"}
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
        # reason carries the advisory BODY, with the marker scaffold stripped
        # (reason is user-visible — see ADVISORY_IN_REASON).
        assert output.reason == ADVISORY_IN_REASON
        assert "SYSTEM HOOK INSTRUCTION" not in output.reason

    def test_stop_does_not_emit_hook_specific_output(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        assert not hasattr(output, "hookSpecificOutput") or output.hookSpecificOutput is None

    def test_session_end_same_routing_as_stop(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "SessionEnd")
        assert output.decision == "block"
        assert output.reason == ADVISORY_IN_REASON

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
        assert output.reason == ADVISORY_IN_REASON
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
        assert payload.get("reason") == ADVISORY_IN_REASON

        for user_field in ("stopReason", "systemMessage"):
            value = payload.get(user_field)
            if value is not None:
                assert "SYSTEM HOOK INSTRUCTION" not in value, (
                    f"Advisory leaked into {user_field!r} of serialised JSON"
                )


# ===========================================================================
# General event channel routing (PreToolUse, UserPromptSubmit, PostToolUse)
# ===========================================================================


class TestGeneralEventAdvisoryReachesAgent:
    """Advisory text reaches agent via hookSpecificOutput.additionalContext."""

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_context_injection_routes_to_additional_context(self, router, event):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, event)
        assert isinstance(output, ClaudeGeneralHookOutput)
        assert output.hookSpecificOutput is not None, (
            f"{event}: hookSpecificOutput missing — context_injection has no delivery channel"
        )
        assert output.hookSpecificOutput.additionalContext == ADVISORY

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_deny_context_injection_routes_to_additional_context(self, router, event):
        canonical = CanonicalHookOutput(verdict="deny", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, event)
        assert isinstance(output, ClaudeGeneralHookOutput)
        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.additionalContext == ADVISORY

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_system_message_routes_to_system_message(self, router, event):
        canonical = CanonicalHookOutput(verdict="allow", system_message="User-facing note")
        output = router.output_for_claude(canonical, event)
        assert output.systemMessage == "User-facing note"


class TestGeneralEventAdvisoryDoesNotLeakToUser:
    """Advisory text must not appear in systemMessage for general events."""

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_advisory_does_not_leak_to_system_message(self, router, event):
        canonical = CanonicalHookOutput(
            verdict="warn",
            context_injection=ADVISORY,
            system_message="short user note",
        )
        output = router.output_for_claude(canonical, event)
        assert "SYSTEM HOOK INSTRUCTION" not in (output.systemMessage or ""), (
            f"{event}: advisory leaked into user-visible systemMessage"
        )

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_deny_with_both_channels_separates_correctly(self, router, event):
        canonical = CanonicalHookOutput(
            verdict="deny",
            context_injection=ADVISORY,
            system_message="Tool use denied",
        )
        output = router.output_for_claude(canonical, event)

        assert output.systemMessage == "Tool use denied"
        assert "SYSTEM HOOK INSTRUCTION" not in (output.systemMessage or "")
        assert output.hookSpecificOutput.additionalContext == ADVISORY


class TestGeneralEventJsonEnvelope:
    """Serialised JSON envelope for general events carries advisory only in agent channel."""

    @pytest.mark.parametrize("event", HSO_EVENTS)
    def test_serialised_json_advisory_in_additional_context_not_system_message(self, router, event):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True))

        hso = payload.get("hookSpecificOutput", {})
        assert hso.get("additionalContext") == ADVISORY

        sys_msg = payload.get("systemMessage")
        if sys_msg is not None:
            assert "SYSTEM HOOK INSTRUCTION" not in sys_msg, (
                f"{event}: advisory leaked into systemMessage of serialised JSON"
            )


# ===========================================================================
# Non-HSO event safety (SessionStart, SubagentStart, etc.)
# ===========================================================================


class TestNonHSOEventSafety:
    """Events not in Claude's HSO set must not emit hookSpecificOutput.

    Claude Code rejects payloads with hookSpecificOutput for events outside
    {PreToolUse, UserPromptSubmit, PostToolUse, PostToolBatch}. If
    context_injection is set for a non-HSO event, it has no delivery channel
    and is silently dropped — these tests document that boundary.
    """

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_no_hook_specific_output_emitted(self, router, event):
        canonical = CanonicalHookOutput(
            verdict="warn", context_injection=ADVISORY, system_message="banner"
        )
        output = router.output_for_claude(canonical, event)
        assert isinstance(output, ClaudeGeneralHookOutput)
        assert output.hookSpecificOutput is None, (
            f"{event}: hookSpecificOutput emitted for non-HSO event — "
            f"Claude Code would reject the entire payload"
        )

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_system_message_still_delivered(self, router, event):
        canonical = CanonicalHookOutput(verdict="allow", system_message="Session info")
        output = router.output_for_claude(canonical, event)
        assert output.systemMessage == "Session info"

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_context_injection_silently_dropped(self, router, event):
        """context_injection for non-HSO events has no agent delivery channel."""
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True))
        assert "additionalContext" not in json.dumps(payload), (
            f"{event}: context_injection appeared in output despite no HSO channel"
        )
        assert "SYSTEM HOOK INSTRUCTION" not in (payload.get("systemMessage") or ""), (
            f"{event}: advisory leaked into systemMessage as fallback"
        )


# ===========================================================================
# Cross-event matrix: advisory never leaks to user-visible fields
# ===========================================================================


class TestCrossEventAdvisoryNeverLeaksToUser:
    """Advisory text must NEVER appear in user-visible fields, for ANY event."""

    @pytest.mark.parametrize("event", ALL_HOOK_EVENTS)
    @pytest.mark.parametrize("verdict", ["warn", "deny"])
    def test_advisory_absent_from_user_visible_fields(self, router, event, verdict):
        canonical = CanonicalHookOutput(
            verdict=verdict,
            context_injection=ADVISORY,
            system_message="User summary",
        )
        output = router.output_for_claude(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True))

        user_fields = ["systemMessage", "stopReason"]
        for field in user_fields:
            value = payload.get(field)
            if value is not None:
                assert "SYSTEM HOOK INSTRUCTION" not in value, (
                    f"{event}/{verdict}: advisory leaked into user-visible {field!r}: {value!r}"
                )

    @pytest.mark.parametrize("event", ALL_HOOK_EVENTS)
    def test_allow_verdict_never_carries_advisory_to_user(self, router, event):
        canonical = CanonicalHookOutput(
            verdict="allow",
            context_injection=None,
            system_message="Clean status",
        )
        output = router.output_for_claude(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True))
        for field in ["systemMessage", "stopReason"]:
            value = payload.get(field)
            if value is not None:
                assert "SYSTEM HOOK INSTRUCTION" not in value
