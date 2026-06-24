"""Schema conformance — parameterised across all hook events × platforms.

Verifies that every hook event produces output conforming to the schema
each platform (Claude Code, Gemini CLI) will accept.
"""

import json

import pytest
from hooks.schemas import CanonicalHookOutput

from tests.hooks.gate_helpers import ALL_HOOK_EVENTS, CLAUDE_ACCEPTED_HOOK_EVENT_NAMES


class TestClaudeSchemaConformance:
    """Every hook event's Claude output must conform to Claude Code's schema.

    Claude Code validates hookSpecificOutput.hookEventName against a fixed
    discriminator set. If the router emits a hookEventName not in that set,
    the entire JSON payload is silently rejected.
    """

    @pytest.mark.parametrize("event", ALL_HOOK_EVENTS)
    def test_claude_hook_output_schema_conformance(self, router, event):
        if event in CLAUDE_ACCEPTED_HOOK_EVENT_NAMES or event in ("Stop", "SessionEnd"):
            canonical = CanonicalHookOutput(
                verdict="warn",
                context_injection="<SYSTEM HOOK INSTRUCTION>test</SYSTEM HOOK INSTRUCTION>",
                system_message="test note",
            )
        else:
            canonical = CanonicalHookOutput(
                verdict="allow",
                context_injection=None,
                system_message="test note",
            )
        output = router.output_for_claude(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True))

        hso = payload.get("hookSpecificOutput")
        if hso is not None:
            event_name = hso.get("hookEventName")
            assert event_name in CLAUDE_ACCEPTED_HOOK_EVENT_NAMES, (
                f"Hook event {event!r} emitted hookSpecificOutput with "
                f"hookEventName={event_name!r}, which Claude Code will reject. "
                f"Accepted values: {CLAUDE_ACCEPTED_HOOK_EVENT_NAMES}"
            )


class TestGeminiSchemaConformance:
    """Gemini CLI hookEventName must match its event."""

    @pytest.mark.parametrize("event", ALL_HOOK_EVENTS)
    def test_gemini_hook_output_schema_conformance(self, router, event):
        canonical = CanonicalHookOutput(
            verdict="warn",
            context_injection="<SYSTEM HOOK INSTRUCTION>test</SYSTEM HOOK INSTRUCTION>",
            system_message="test note",
        )
        output = router.output_for_gemini(canonical, event)
        payload = json.loads(output.model_dump_json(exclude_none=True, by_alias=True))

        hso = payload.get("hookSpecificOutput")
        if hso is not None:
            event_name = hso.get("hookEventName")
            assert event_name == event, (
                f"Gemini hookEventName mismatch: expected {event!r}, got {event_name!r}"
            )
