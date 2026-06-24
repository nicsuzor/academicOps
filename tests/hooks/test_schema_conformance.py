"""Schema conformance — parameterised across all hook events × platforms.

Verifies that every hook event produces output conforming to the schema
each platform (Claude Code, Gemini CLI, agy) will accept.
"""

import json

import pytest
from hooks.schemas import CanonicalHookOutput
from pydantic import ValidationError

from tests.hooks.agy_accept_contract import (
    ACCEPT_MODEL_BY_EVENT,
    HookInjectedStep,
    is_accepted_by_agy,
)
from tests.hooks.gate_helpers import ALL_HOOK_EVENTS, CLAUDE_ACCEPTED_HOOK_EVENT_NAMES

_AGY_FORBIDDEN_FIELDS = ("decision", "metadata", "systemMessage", "hookSpecificOutput", "reason")


@pytest.fixture
def run_router(router):
    def _run(client_type, canonical, event):
        if client_type == "claude":
            output = router.output_for_claude(canonical, event)
            return json.loads(output.model_dump_json(exclude_none=True))
        elif client_type == "gemini":
            output = router.output_for_gemini(canonical, event)
            return json.loads(output.model_dump_json(exclude_none=True, by_alias=True))
        else:
            return router.output_for_agy(canonical, event)

    return _run


@pytest.mark.parametrize("client_type", ["claude", "gemini", "agy"])
@pytest.mark.parametrize("event", ALL_HOOK_EVENTS)
@pytest.mark.parametrize("verdict", ["allow", "warn", "deny", "ask"])
def test_hook_output_schema_conformance(run_router, client_type, event, verdict):
    """Every hook event must produce output conforming to the client's schema."""
    kwargs = {
        "verdict": verdict,
        "context_injection": "<SYSTEM HOOK INSTRUCTION>test</SYSTEM HOOK INSTRUCTION>",
        "system_message": "test note",
    }

    if client_type == "claude":
        if event not in CLAUDE_ACCEPTED_HOOK_EVENT_NAMES and event not in ("Stop", "SessionEnd"):
            kwargs["context_injection"] = None
            if verdict in ("deny", "ask"):
                kwargs["verdict"] = "allow"
    elif client_type == "agy":
        if event not in ACCEPT_MODEL_BY_EVENT:
            kwargs["context_injection"] = None
            kwargs["system_message"] = None
            if verdict in ("deny", "ask"):
                kwargs["verdict"] = "allow"
        else:
            if event == "PreToolUse":
                kwargs["context_injection"] = None
                if verdict == "allow":
                    kwargs["system_message"] = None
            elif event == "PostToolUse":
                kwargs["system_message"] = None
                kwargs["context_injection"] = None
            elif event == "Stop":
                kwargs["context_injection"] = None
                if verdict == "allow":
                    kwargs["system_message"] = None

    canonical = CanonicalHookOutput(**kwargs)
    payload = run_router(client_type, canonical, event)

    if client_type == "claude":
        hso = payload.get("hookSpecificOutput")
        if hso is not None:
            event_name = hso.get("hookEventName")
            assert event_name in CLAUDE_ACCEPTED_HOOK_EVENT_NAMES

    elif client_type == "gemini":
        hso = payload.get("hookSpecificOutput")
        if hso is not None:
            event_name = hso.get("hookEventName")
            assert event_name == event

    elif client_type == "agy":
        if event in ACCEPT_MODEL_BY_EVENT:
            accepted, offending = is_accepted_by_agy(payload, event)
            assert accepted, offending
            for forbidden in _AGY_FORBIDDEN_FIELDS:
                if event == "Stop" and forbidden == "reason":
                    continue
                assert forbidden not in payload, f"{forbidden} leaked into agy {event} payload"
        else:
            assert payload == {}, f"agy must return empty dict for unmapped event {event}"


# --- Client-specific Semantic Falsification & Anchor Guards ---


@pytest.mark.parametrize("verdict", ["allow", "warn"])
def test_agy_pretooluse_nonblocking_emits_allow_tool_true(router, verdict):
    canonical = CanonicalHookOutput(verdict=verdict)
    payload = router.output_for_agy(canonical, "PreToolUse")
    assert payload == {"allowTool": True}
    assert "denyReason" not in payload
    assert "decision" not in payload


def test_agy_pretooluse_deny_uses_top_level_allow_tool(router):
    canonical = CanonicalHookOutput(verdict="deny", system_message="blocked")
    payload = router.output_for_agy(canonical, "PreToolUse")
    assert payload["allowTool"] is False
    assert payload["denyReason"] == "blocked"
    assert "permissionOverrides" not in payload


def test_agy_postinvocation_folds_system_and_context_into_steps(router):
    """PostInvocation with both system_message+context_injection must fold both
    into injectSteps, not crash.

    The IDA WARN policy sets both system_message ("≡ Honesty check...") and
    context_injection ("be honest..."). PostInvocation has no system_message
    channel, so short_reason is folded into the advisory text. The earlier code
    raised ValueError here, making the router subprocess exit non-zero with no
    stdout — callers got {} and the IDA advisory was silently dropped
    (aops-test-1798). Ported from the consolidated test_output_for_agy.py.
    """
    canonical = CanonicalHookOutput(
        verdict="warn", system_message="status msg", context_injection="advisory text"
    )
    payload = router.output_for_agy(canonical, "PostInvocation")
    steps = payload.get("injectSteps", [])
    assert steps, f"both system+context must be delivered via injectSteps: {payload!r}"
    joined = " ".join(s.get("ephemeralMessage", "") for s in steps)
    assert "status msg" in joined and "advisory text" in joined, (
        f"both messages must appear in injectSteps: {joined!r}"
    )


def test_agy_injected_step_oneof_variant_shapes_match_binary_descriptor():
    HookInjectedStep.model_validate({"ephemeralMessage": "scalar ok"})
    with pytest.raises(ValidationError):
        HookInjectedStep.model_validate({"ephemeralMessage": {"text": "wrong-object"}})


@pytest.mark.xfail(strict=True, reason="Waiting for terminationBehavior enum discovery")
def test_agy_stop_hard_block_terminationbehavior_is_deferred(router):
    canonical = CanonicalHookOutput(verdict="deny", context_injection="x")
    payload = router.output_for_agy(canonical, "PostInvocation")
    assert "terminationBehavior" in payload
