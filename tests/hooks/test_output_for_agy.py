"""Unit coverage for ``HookRouter.output_for_agy`` (aops-d27d55a0).

The subprocess accept-contract (``test_agy_protojson_contract.py``) exercises
only PreToolUse + PostToolUse end-to-end. This module calls ``output_for_agy``
directly with synthetic ``CanonicalHookOutput`` verdicts to cover ALL FIVE agy
result shapes (Pre/PostTool, Pre/PostInvocation, Stop) and validates each emitted
payload against the strict ``exa.hooks_pb.*Result`` accept-contract.

It also pins the two invariants the silent-drop regression (aops-27004ffd)
turned on:
  * ``metadata`` (and every other Claude/Gemini-schema field) NEVER appears, for
    any event — that single leaked field is what made agy discard the verdict;
  * a DENY is structural (``permissionOverrides.allowTool=false``), needing no
    unverified enum string.

DEFERRED guard: ``test_stop_hard_block_terminationbehavior_is_deferred`` is
``xfail(strict=True)`` — the hard stop-block enum (PostInvocation
``terminationBehavior`` / Stop ``decision``) is blocked on live-agy discovery
(aops-939b6c3a). When that enum lands and ``output_for_agy`` emits it, the guard
XPASSes and trips strict-xfail, forcing whoever lands it to wire the live
"Stop respected" regression (aops-7fa86b45).
"""

from __future__ import annotations

import pytest
from hooks.router import HookRouter
from hooks.schemas import CanonicalHookOutput

from tests.hooks.agy_accept_contract import ACCEPT_MODEL_BY_EVENT, is_accepted_by_agy

# Every Claude/Gemini-schema field that, if leaked, makes agy reject the payload
# on an unknown field (the verbatim cli.log failure mode in aops-27004ffd).
_FORBIDDEN_FIELDS = ("decision", "metadata", "systemMessage", "hookSpecificOutput", "reason")


def _agy(verdict, *, event, context=None, system=None):
    """Run a synthetic verdict through output_for_agy for `event`."""
    result = CanonicalHookOutput(
        verdict=verdict,
        context_injection=context,
        system_message=system,
    )
    return HookRouter().output_for_agy(result, event)


def _assert_accepted(payload, event):
    accepted, offending = is_accepted_by_agy(payload, event)
    assert accepted, f"agy would reject {event} payload on unknown field(s): {offending}: {payload}"


# --- Acceptance across every event x verdict -------------------------------


@pytest.mark.parametrize("event", list(ACCEPT_MODEL_BY_EVENT))
@pytest.mark.parametrize("verdict", ["allow", "deny", "warn", "ask"])
def test_every_event_and_verdict_is_accepted_by_agy(event, verdict):
    """No (event, verdict) combination may emit output agy's protojson rejects."""
    payload = _agy(verdict, event=event, context="advisory text", system="short reason")
    _assert_accepted(payload, event)


@pytest.mark.parametrize("event", list(ACCEPT_MODEL_BY_EVENT))
@pytest.mark.parametrize("verdict", ["allow", "deny", "warn", "ask"])
def test_no_claude_schema_field_ever_leaks(event, verdict):
    """The single leaked field that caused the silent drop must never appear.

    ``reason`` is legal on StopHookResult, so it is only forbidden off the Stop
    result; every other field is forbidden everywhere.
    """
    payload = _agy(verdict, event=event, context="advisory text", system="short reason")
    forbidden = (
        _FORBIDDEN_FIELDS
        if event != "Stop"
        else tuple(f for f in _FORBIDDEN_FIELDS if f != "reason")
    )
    for field in forbidden:
        assert field not in payload, f"{field!r} leaked into {event}/{verdict} output: {payload}"


# --- PreToolUse ------------------------------------------------------------


def test_pretooluse_allow_emits_explicit_allow_tool_true():
    """A PreToolUse ALLOW must emit ``{"allowTool": true}`` EXPLICITLY — never ``{}``.

    SEMANTIC regression guard for aops-1e68682a. agy parses hook stdout as
    ``exa.hooks_pb.PreToolHookResult`` protojson, where an OMITTED bool defaults
    to ``false``. So an empty-object "allow" ``{}`` is parsed by agy as
    ``allowTool=false, denyReason=""`` — a DENY with an empty reason — and agy
    blocks EVERY allowed tool call on the agy/Antigravity client (reproduced live
    in session 22b4caa2, 2026-06-15: 10 PreToolUse events all logged
    ``verdict:allow`` internally, yet all 10 tools were denied with empty reason).

    The predecessor of this test (``test_pretooluse_allow_is_empty_object``)
    asserted ``== {}`` — it encoded the bug as the contract, which is precisely
    what let the regression ship. The contract is now SEMANTIC: the allow must
    set ``allowTool`` true, not merely be "accepted" by the unknown-field guard.
    """
    payload = _agy("allow", event="PreToolUse", context="ignored")
    assert payload == {"allowTool": True}
    # No deny fields leak onto an allow.
    assert "denyReason" not in payload
    assert "decision" not in payload


def test_pretooluse_allow_parses_as_allow_tool_true_under_protojson_model():
    """The ALLOW output, parsed as ``PreToolHookResult``, must yield allowTool==True.

    This is the SEMANTIC roundtrip the old contract test missed: the existing
    ``is_accepted_by_agy`` guard only checks for UNKNOWN fields, so the buggy
    ``{}`` passed it trivially (no unknown fields) while meaning DENY on the wire.
    Here we parse the emitted dict through the same ``PreToolHookResult`` model
    agy uses (transcribed from the ``exa.hooks_pb`` descriptor; the real binary
    descriptor is not yet vendored — epic aops-2dc18411) and assert the BOOL the
    harness reads is explicitly true, NOT the protojson omitted-bool default of
    false.
    """
    from tests.hooks.agy_accept_contract import PreToolHookResult

    payload = _agy("allow", event="PreToolUse")
    parsed = PreToolHookResult.model_validate(payload)
    assert parsed.allowTool is True, (
        f"agy reads PreToolHookResult.allowTool; an allow must parse as True, "
        f"not the protojson omitted-bool default. payload={payload!r}"
    )

    # Falsification anchor: the BUGGY empty-object allow parses as allowTool=None,
    # which agy's protojson coerces to the bool default false → DENY. This pins
    # exactly why {} is wrong on the wire even though it passes the unknown-field
    # accept-contract.
    accepted, _ = is_accepted_by_agy({}, "PreToolUse")
    assert accepted, "the empty object passes the unknown-field guard (the blindspot)"
    assert PreToolHookResult.model_validate({}).allowTool is None, (
        "empty-object allow leaves allowTool unset → agy protojson defaults it to "
        "false → DENY; this is the aops-1e68682a bug the {} allow shipped"
    )


def test_pretooluse_deny_uses_top_level_allow_tool_no_enum():
    """``allowTool`` and ``denyReason`` are TOP-LEVEL on ``PreToolHookResult``.

    Nesting them under ``permissionOverrides`` (a *repeated* field for per-tool
    permission overrides) made protojson reject with ``unexpected token {`` and
    silently dropped every enforcer DENY in live agy (aops-891c0e36).
    """
    payload = _agy("deny", event="PreToolUse", system="blocked: compliance overdue")
    assert payload["allowTool"] is False
    assert payload["denyReason"] == "blocked: compliance overdue"
    # The fields must be TOP-LEVEL — they must NOT be nested under a
    # message-valued permissionOverrides (the protojson-rejected pre-fix shape).
    assert "permissionOverrides" not in payload
    # Structural deny: no top-level decision enum string.
    assert "decision" not in payload


def test_pretooluse_ask_is_blocked_in_headless_agy():
    """`ask` cannot prompt headless, so the enforcing interpretation is block."""
    payload = _agy("ask", event="PreToolUse", system="needs confirmation")
    assert payload["allowTool"] is False
    assert "permissionOverrides" not in payload


# --- PostToolUse -----------------------------------------------------------


@pytest.mark.parametrize("verdict", ["allow", "deny", "warn", "ask"])
def test_posttooluse_is_always_empty(verdict):
    assert _agy(verdict, event="PostToolUse", context="x", system="y") == {}


# --- PreInvocation (UserPromptSubmit) --------------------------------------


def test_preinvocation_injects_context_as_steps():
    payload = _agy("allow", event="PreInvocation", context="search the PKB first")
    steps = payload["injectSteps"]
    assert steps == [{"ephemeralMessage": "search the PKB first"}]


def test_preinvocation_without_context_is_empty():
    assert _agy("allow", event="PreInvocation") == {}


def test_injected_step_oneof_variant_shapes_match_binary_descriptor():
    """Pin the agy 1.0.7 ``HookInjectedStep`` oneof field types we emit against.

    Decoded from the ``exa.hooks_pb`` FileDescriptorProto in the agy binary:
    ``system_message``/``tool_call`` are TYPE_MESSAGE (nested object),
    ``user_message``/``ephemeral_message`` are TYPE_STRING (scalar). The router
    emits the ``ephemeralMessage`` (scalar string) member — the variant agy
    actually renders into the model turn (the ``systemMessage`` message member
    is dropped from the rendered turn even once the hook fires). This test guards
    both the emitted scalar shape and the accept-contract's scalar-vs-message
    typing so a regression to ``{"ephemeralMessage": {...}}`` (object where a
    string is required) is caught offline.
    """
    from tests.hooks.agy_accept_contract import HookInjectedStep, is_accepted_by_agy

    # The router's emitted variant: ephemeralMessage is a scalar string.
    payload = _agy("allow", event="PreInvocation", context="x")
    assert payload["injectSteps"] == [{"ephemeralMessage": "x"}]
    accepted, offending = is_accepted_by_agy(payload, "PreInvocation")
    assert accepted, offending

    # Descriptor-typed scalar members accept a bare string and reject an object.
    HookInjectedStep.model_validate({"ephemeralMessage": "scalar ok"})
    HookInjectedStep.model_validate({"userMessage": "scalar ok"})
    import pytest as _pytest
    from pydantic import ValidationError

    with _pytest.raises(ValidationError):
        HookInjectedStep.model_validate({"ephemeralMessage": {"text": "wrong-object"}})
    # And the message members accept an object.
    HookInjectedStep.model_validate({"systemMessage": {"systemMessage": "ok"}})


# --- PostInvocation (Stop) -------------------------------------------------


def test_postinvocation_delivers_advisory_via_injectsteps():
    payload = _agy("deny", event="PostInvocation", context="finish the handover")
    assert payload["injectSteps"] == [{"ephemeralMessage": "finish the handover"}]
    # The hard stop-block enum is deferred — not emitted as a guess.
    assert "terminationBehavior" not in payload


def test_postinvocation_allow_is_empty():
    assert _agy("allow", event="PostInvocation") == {}


# --- Stop ------------------------------------------------------------------


def test_stop_deny_surfaces_reason_without_guessed_decision():
    payload = _agy("deny", event="Stop", context="commit your work before stopping")
    assert payload == {"reason": "commit your work before stopping"}
    # The blocking `decision` enum is deferred (aops-939b6c3a) — never guessed.
    assert "decision" not in payload


def test_stop_allow_is_empty():
    assert _agy("allow", event="Stop") == {}


# --- Unknown event ---------------------------------------------------------


def test_unknown_event_is_empty_object():
    assert _agy("deny", event="SessionStart", context="x", system="y") == {}


# --- Deferred hard stop-block (forcing function) ---------------------------


@pytest.mark.xfail(
    strict=True,
    reason="aops-939b6c3a: terminationBehavior/decision enum strings not yet "
    "live-verified — output_for_agy delivers the Stop advisory but does not "
    "force-continue. When the enum lands, emit it and flip this guard + wire "
    "the live 'Stop respected' test (aops-7fa86b45).",
)
def test_stop_hard_block_terminationbehavior_is_deferred():
    """Forcing function: a Stop/PostInvocation DENY must eventually force-continue.

    Today ``output_for_agy`` cannot emit the ``terminationBehavior`` enum (its
    string is unverified), so this asserts the not-yet-true end state and is
    expected to xfail until the enum is discovered.
    """
    payload = _agy("deny", event="PostInvocation", context="keep going")
    assert "terminationBehavior" in payload
