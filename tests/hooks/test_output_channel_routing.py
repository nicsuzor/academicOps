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
"""

import json

import pytest
from hooks.schemas import (
    CanonicalHookOutput,
    ClaudeGeneralHookOutput,
    ClaudeStopHookOutput,
)

from tests.hooks.gate_helpers import (
    ADVISORY,
    ALL_HOOK_EVENTS,
    CLAUDE_ACCEPTED_HOOK_EVENT_NAMES,
)

# The Stop `reason` field is user-visible (Claude Code renders a blocking Stop
# hook's reason to the user). Advisory injections no longer carry the
# `<SYSTEM HOOK INSTRUCTION>` scaffold (removed 2026-06-27), so the advisory body
# IS the reason — nothing to strip. The assertions below remain as regression
# guards that the scaffold never returns to a user-visible channel.
ADVISORY_IN_REASON = ADVISORY

# Events that use hookSpecificOutput.additionalContext for agent delivery
HSO_EVENTS = sorted(CLAUDE_ACCEPTED_HOOK_EVENT_NAMES)

# Events that use decision=block + reason for agent delivery
STOP_EVENTS = ["Stop", "SessionEnd"]

# Events where hookSpecificOutput is NOT accepted by Claude Code
NON_HSO_EVENTS = sorted(
    set(ALL_HOOK_EVENTS) - CLAUDE_ACCEPTED_HOOK_EVENT_NAMES - {"Stop", "SessionEnd"}
)


# --- Synthetic canonical output tests (not gate-specific) ---


class TestCanonicalChannelRouting:
    """Channel routing from CanonicalHookOutput → Claude Stop output."""

    def test_warn_with_advisory_delivers_without_block(self, router):
        # Invariant B / P4 line (c): warn-mode Stop advisory delivers via
        # hookSpecificOutput.additionalContext WITHOUT a spurious block.
        # Claude Code 2.1.191 accepts + delivers additionalContext on Stop
        # without blocking (mem-4ab6cc0b, live-verified 2026-06-25;
        # channel_spec("claude","Stop").agent_context_without_block == True).
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        # No spurious block — the agent keeps continuing (warn semantics).
        assert output.decision == "approve"
        # Advisory rides the agent-only additionalContext channel; markers stay
        # intact there (the gate's trust framing — additionalContext is NOT
        # user-visible, unlike `reason`).
        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.additionalContext == ADVISORY
        assert output.hookSpecificOutput.hookEventName == "Stop"

    def test_warn_advisory_not_in_user_visible_reason(self, router):
        # The retired block-to-deliver no longer leaks advisory into the
        # user-visible `reason` for warn-mode gates.
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        assert output.reason is None

    def test_session_end_same_routing_as_stop(self, router):
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "SessionEnd")
        assert output.decision == "approve"
        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.additionalContext == ADVISORY

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

    def test_serialised_json_carries_warn_advisory_in_additional_context(self, router):
        # Invariant B / P4 (c): warn-mode Stop advisory rides
        # hookSpecificOutput.additionalContext (agent-only), not a block.
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, "Stop")
        payload = json.loads(output.model_dump_json(exclude_none=True))

        assert payload.get("decision") == "approve"
        assert payload.get("hookSpecificOutput", {}).get("additionalContext") == ADVISORY

        for user_field in ("stopReason", "systemMessage", "reason"):
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
    context_injection (or a blocking verdict) is set for a non-HSO event it has
    no delivery/enforcement channel, so the router DROPS it — with a loud stderr
    breadcrumb — and never emits hookSpecificOutput. It must NOT raise: a
    multi-event trigger legitimately produces an undeliverable advisory here
    (e.g. the rbg reset trigger fires on PreToolUse|SubagentStart|SubagentStop
    with one shared transition), and crashing the hook over an advisory it
    merely can't route is worse than dropping it. See router
    ``_resolve_policy_for_claude_general`` and the pre-600985c9 graceful-drop.
    """

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_system_message_still_delivered(self, router, event):
        canonical = CanonicalHookOutput(verdict="allow", system_message="Session info")
        output = router.output_for_claude(canonical, event)
        assert output.systemMessage == "Session info"

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_context_injection_dropped_not_crashed(self, router, event, capsys):
        """context_injection for non-HSO events is dropped (no HSO channel), not raised.

        Regression for the SubagentStart rbg-dispatch crash: the rbg reset
        trigger emits ``rbg.verified`` context_injection on SubagentStart, which
        has no additionalContext channel. The router must drop it gracefully so
        the hook does not fail with a ValueError traceback.
        """
        canonical = CanonicalHookOutput(verdict="warn", context_injection=ADVISORY)
        output = router.output_for_claude(canonical, event)  # must NOT raise

        payload = json.loads(output.model_dump_json(exclude_none=True))
        assert "hookSpecificOutput" not in payload, (
            f"{event}: emitted hookSpecificOutput despite no HSO channel"
        )
        assert "additionalContext" not in json.dumps(payload), (
            f"{event}: context_injection leaked into output despite no HSO channel"
        )
        # Advisory must not fall back into the user-visible systemMessage.
        assert ADVISORY not in (payload.get("systemMessage") or "")
        # Dropped, but loudly — a breadcrumb reaches stderr for debug logs.
        assert event in capsys.readouterr().err

    @pytest.mark.parametrize("event", NON_HSO_EVENTS)
    def test_blocking_verdict_dropped_not_crashed(self, router, event, capsys):
        """Blocking verdicts for non-HSO events are downgraded to allow, not raised.

        Claude cannot enforce a block on SessionStart/SubagentStart/etc (no
        permission channel), so the router downgrades to allow with a stderr
        breadcrumb rather than crashing the hook.
        """
        canonical = CanonicalHookOutput(verdict="deny", system_message="blocked")
        output = router.output_for_claude(canonical, event)  # must NOT raise

        payload = json.loads(output.model_dump_json(exclude_none=True))
        assert "hookSpecificOutput" not in payload
        # No block wire-decision survives (decision/permissionDecision absent).
        assert payload.get("decision") != "block"
        assert event in capsys.readouterr().err


# ===========================================================================
# Cross-event matrix: advisory never leaks to user-visible fields
# ===========================================================================


class TestCrossEventAdvisoryNeverLeaksToUser:
    """Advisory text must NEVER appear in user-visible fields, for ANY event."""

    @pytest.mark.parametrize("event", HSO_EVENTS + STOP_EVENTS)
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
