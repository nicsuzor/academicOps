"""End-to-end message-path leak coverage — data-driven from GATE_CONFIGS.

The sibling ``test_output_channel_routing.py`` proves the router splits
*already-tagged synthetic* input correctly. It does NOT prove that the real
gate→engine→router pipeline never leaks full instruction/context bodies into
user-visible channels.

This module closes that gap. It enumerates EVERY message path in
``GATE_CONFIGS`` programmatically (each policy's message_key/context_key and
each transition's system_message_key/context_key), renders the REAL templates
the engine would render, runs the real output through ``output_for_claude`` for
the path's event, and asserts — marker-independently — that:

  1. The full context body reaches the AGENT channel (``reason`` for Stop, or
     ``hookSpecificOutput.additionalContext`` for HSO events) where one exists.
  2. The rendered context body does NOT appear (substring, whitespace-
     normalised) in ANY user-visible field (``systemMessage`` / ``stopReason``
     / ``permissionDecisionReason``). This is the core leak assertion. It does
     NOT depend on the ``<SYSTEM HOOK INSTRUCTION>`` marker, because the
     TRANSITION path in engine.py never adds that marker (only the POLICY path
     does, around engine.py line 450).
  3. Where a path has both a short message_key and a context_key, the
     user channel carries the SHORT message, not the context body.

Adding a gate or path to ``GATE_CONFIGS`` is automatically covered — the
parameterisation reads the config, never a hardcoded gate list.

Failures here are FINDINGS (genuine leaks), not test bugs. Production code is
not modified to make them pass.
"""

import re
from dataclasses import dataclass

import pytest
from hooks.schemas import CanonicalHookOutput  # noqa: E402
from lib.gates.definitions import GATE_CONFIGS
from lib.template_registry import TemplateRegistry

# gate_helpers inserts aops-core onto sys.path as a side effect of import.
from tests.hooks.gate_helpers import (  # noqa: F401
    make_gate_trigger_context,
    make_gate_trigger_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# ---------------------------------------------------------------------------
# Whitespace-normalised substring check (marker-independent leak detector).
# ---------------------------------------------------------------------------


def _norm(text: str | None) -> str:
    """Collapse all runs of whitespace to single spaces and strip.

    The marker wrapping and channel plumbing may reflow whitespace; comparing
    normalised forms makes the substring test robust to that.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


_MARKER_OPEN = "<SYSTEM HOOK INSTRUCTION>"
_MARKER_CLOSE = "</SYSTEM HOOK INSTRUCTION>"


def _strip_marker(text: str) -> str:
    """Remove the policy-path SYSTEM HOOK INSTRUCTION wrapper, if present."""
    return text.replace(_MARKER_OPEN, "").replace(_MARKER_CLOSE, "").strip()


def _body_leaked_into(user_text: str | None, context_body: str) -> bool:
    """True if the (normalised) context body appears inside the user text.

    Marker-independent: we look for the rendered template body itself, not the
    ``<SYSTEM HOOK INSTRUCTION>`` wrapper.
    """
    norm_body = _norm(context_body)
    norm_user = _norm(user_text)
    if not norm_body or not norm_user:
        return False
    return norm_body in norm_user


# ---------------------------------------------------------------------------
# Template variable resolution.
#
# Some context templates require variables (temp_path, ops_since_open). We
# supply realistic stand-ins so render() succeeds. The values are arbitrary;
# what matters is that the *rendered body* must not reach the user channel.
# ---------------------------------------------------------------------------

_TEMPLATE_VARS: dict[str, dict[str, object]] = {
    "enforcer.policy_context": {"temp_path": "/tmp/enforcer-ctx.md", "ops_since_open": 50},
    "qa.policy_context": {"temp_path": "/tmp/qa-gate.md"},
    "enforcer.policy_message": {"ops_since_open": 50},
}


def _render(key: str) -> str:
    return TemplateRegistry.instance().render(key, _TEMPLATE_VARS.get(key, {}))


# ---------------------------------------------------------------------------
# Enumerate every message path from GATE_CONFIGS.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MessagePath:
    gate: str
    kind: str  # "policy" or "transition"
    index: int  # position within the gate's policies/triggers list
    event: str  # representative concrete hook event the path fires on
    verdict: str  # engine verdict for the path ("deny"/"warn"/"allow")
    message_key: str | None  # short user-facing message key (policy)/sys key (transition)
    context_key: str | None  # full context-injection key

    @property
    def id(self) -> str:
        return f"{self.gate}.{self.kind}[{self.index}]:{self.event}"


# Map an engine verdict string ("block" → "deny") to the canonical verdict the
# router consumes. Policies declare verdict as the resolved gate mode string;
# transitions always emit allow.
def _canonical_verdict(raw: str) -> str:
    v = str(getattr(raw, "value", raw))
    return "deny" if v == "block" else v


# A condition's hook_event may be a regex alternation (e.g. enforcer's
# transition). Resolve to a single concrete event for routing.
def _concrete_event(hook_event: str | None) -> str:
    if not hook_event:
        # No event constraint — exercise it as a PreToolUse (general HSO path).
        return "PreToolUse"
    # Strip regex anchors and pick the first alternative.
    cleaned = hook_event.strip("^$")
    first = cleaned.split("|")[0]
    first = first.strip("()")
    return first


def _enumerate_paths() -> list[MessagePath]:
    paths: list[MessagePath] = []
    for gate in GATE_CONFIGS:
        for i, policy in enumerate(gate.policies):
            paths.append(
                MessagePath(
                    gate=gate.name,
                    kind="policy",
                    index=i,
                    event=_concrete_event(policy.condition.hook_event),
                    verdict=_canonical_verdict(policy.verdict),
                    message_key=policy.message_key,
                    context_key=policy.context_key,
                )
            )
        for i, trigger in enumerate(gate.triggers):
            t = trigger.transition
            # Only transitions that emit message content are interesting here.
            if not (t.system_message_key or t.context_key):
                continue
            paths.append(
                MessagePath(
                    gate=gate.name,
                    kind="transition",
                    index=i,
                    event=_concrete_event(trigger.condition.hook_event),
                    verdict="allow",  # transitions always emit allow
                    message_key=t.system_message_key,
                    context_key=t.context_key,
                )
            )
    return paths


ALL_PATHS = _enumerate_paths()
# Only paths that actually inject a context body can leak it.
CONTEXT_PATHS = [p for p in ALL_PATHS if p.context_key]

USER_VISIBLE_FIELDS = ("systemMessage", "stopReason")


def _user_visible_values(output) -> dict[str, str | None]:
    """Collect all user-visible channel values from a router output object."""
    vals: dict[str, str | None] = {}
    for field in USER_VISIBLE_FIELDS:
        vals[field] = getattr(output, field, None)
    hso = getattr(output, "hookSpecificOutput", None)
    if hso is not None:
        vals["permissionDecisionReason"] = getattr(hso, "permissionDecisionReason", None)
    return vals


def _agent_channel_value(output) -> str | None:
    """Collect the agent-delivery channel value (reason or additionalContext)."""
    reason = getattr(output, "reason", None)
    if reason:
        return reason
    hso = getattr(output, "hookSpecificOutput", None)
    if hso is not None:
        ac = getattr(hso, "additionalContext", None)
        if ac:
            return ac
    return None


def _build_canonical(path: MessagePath) -> tuple[CanonicalHookOutput, str, str]:
    """Reproduce, faithfully, the CanonicalHookOutput the engine would emit.

    Returns (canonical, rendered_context_body, short_user_message).

    POLICY path (engine._evaluate_policies):
      - context_injection = "<SYSTEM HOOK INSTRUCTION>" + ctx + "</...>"
      - system_message    = short message (message_key)
      - verdict propagated (deny/warn)
    TRANSITION path (engine._apply_transition):
      - context_injection = rendered context body (NO marker wrap)
      - system_message    = rendered system message
      - verdict = allow
    """
    rendered_ctx = _render(path.context_key) if path.context_key else ""
    short_msg = _render(path.message_key) if path.message_key else ""

    if path.kind == "policy":
        ctx_inj = (
            "<SYSTEM HOOK INSTRUCTION>" + rendered_ctx + "</SYSTEM HOOK INSTRUCTION>"
            if rendered_ctx
            else None
        )
        canonical = CanonicalHookOutput(
            verdict=path.verdict,
            system_message=short_msg or None,
            context_injection=ctx_inj,
        )
    else:  # transition — engine applies NO marker
        canonical = CanonicalHookOutput(
            verdict="allow",
            system_message=short_msg or None,
            context_injection=rendered_ctx or None,
        )
    return canonical, rendered_ctx, short_msg


# ---------------------------------------------------------------------------
# Tests: synthetic-but-real-template drive of the router (covers every path).
# ---------------------------------------------------------------------------


class TestContextBodyNeverLeaksToUser:
    """The rendered context body must never appear in a user-visible field."""

    @pytest.mark.parametrize("path", CONTEXT_PATHS, ids=[p.id for p in CONTEXT_PATHS])
    def test_context_body_absent_from_user_channels(self, router, path: MessagePath):
        canonical, rendered_ctx, _short = _build_canonical(path)
        output = router.output_for_claude(canonical, path.event)

        user_vals = _user_visible_values(output)
        leaks = {
            field: value
            for field, value in user_vals.items()
            if value is not None and _body_leaked_into(value, rendered_ctx)
        }
        assert not leaks, (
            f"LEAK [{path.id}] verdict={path.verdict} context_key={path.context_key!r}: "
            f"context body reached user-visible field(s) {list(leaks)}. "
            f"First leaking field shows: {next(iter(leaks.values()))[:120]!r}"
        )


class TestContextBodyReachesAgent:
    """The full context body must reach the AGENT channel for events with one."""

    # Events that have an agent-delivery channel in output_for_claude.
    _AGENT_DELIVERABLE = {"Stop", "SessionEnd", "PreToolUse", "PostToolUse", "UserPromptSubmit"}

    @pytest.mark.parametrize("path", CONTEXT_PATHS, ids=[p.id for p in CONTEXT_PATHS])
    def test_context_body_reaches_agent_channel(self, router, path: MessagePath):
        if path.event not in self._AGENT_DELIVERABLE:
            pytest.skip(f"{path.event}: no agent-delivery channel in output_for_claude")
        # Stop-event allow-verdict transitions have no agent channel (decision
        # would be "approve", reason unset). Only deny/warn reach the agent on
        # Stop. Document that boundary rather than asserting a false invariant.
        if path.event in ("Stop", "SessionEnd") and path.verdict == "allow":
            pytest.skip(
                f"{path.id}: allow-verdict on Stop has no agent channel "
                "(decision=approve; reason unset)"
            )

        canonical, rendered_ctx, _short = _build_canonical(path)
        output = router.output_for_claude(canonical, path.event)
        agent_text = _agent_channel_value(output)
        assert agent_text is not None, (
            f"{path.id}: context body had no agent-delivery channel "
            f"(verdict={path.verdict}, event={path.event})"
        )
        # The agent channel carries the (marker-wrapped, for policies) body.
        assert _norm(rendered_ctx) in _norm(agent_text), (
            f"{path.id}: rendered context body did not reach the agent channel"
        )


class TestShortMessageInUserChannelNotContext:
    """Where a path has both a short message and a context body, the user
    channel must carry the SHORT message — never the context body."""

    _BOTH = [p for p in CONTEXT_PATHS if p.message_key and p.message_key != p.context_key]

    @pytest.mark.parametrize("path", _BOTH, ids=[p.id for p in _BOTH])
    def test_user_channel_has_short_message(self, router, path: MessagePath):
        canonical, rendered_ctx, short_msg = _build_canonical(path)
        output = router.output_for_claude(canonical, path.event)
        user_vals = _user_visible_values(output)

        # At least one user-visible field should carry the short message for
        # paths that populate a user channel (Stop deny/warn, HSO deny).
        populated = {f: v for f, v in user_vals.items() if v}
        if not populated:
            pytest.skip(f"{path.id}: no user-visible channel populated for this verdict/event")

        for field, value in populated.items():
            assert not _body_leaked_into(value, rendered_ctx), (
                f"{path.id}: user field {field!r} carries the CONTEXT body, "
                f"expected the short message {short_msg!r}"
            )


# ---------------------------------------------------------------------------
# Same-key suspicion: enforcer.verified feeds one template into BOTH channels.
# ---------------------------------------------------------------------------


class TestEnforcerVerifiedSameKey:
    """The enforcer 'verified' transition uses ONE key for both system_message
    and context — confirm what that template actually contains and whether it
    constitutes an instruction-text leak."""

    def test_enforcer_verified_template_is_short_status_not_instruction(self):
        body = _render("enforcer.verified")
        norm = _norm(body)
        # The template is a short status line, not a full instruction block.
        assert norm == "◇ Compliance verified.", (
            f"enforcer.verified content changed; re-evaluate leak risk. Got: {body!r}"
        )

    def test_enforcer_verified_routes_same_body_to_both_channels(self, router):
        # Mirror the transition: both system_message and context_injection are
        # the SAME rendered body (no marker — transitions don't wrap).
        body = _render("enforcer.verified")
        canonical = CanonicalHookOutput(
            verdict="allow", system_message=body, context_injection=body
        )
        # Transition fires on PreToolUse (general HSO path).
        output = router.output_for_claude(canonical, "PreToolUse")
        # The body lands in BOTH systemMessage (user) and additionalContext
        # (agent). Because the body is a benign short status, this is not a
        # full-instruction leak — but it IS the same text in both channels.
        assert output.systemMessage == body
        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.additionalContext == body


# ---------------------------------------------------------------------------
# Real end-to-end: drive gates that can actually fire through the full
# gate→engine→router pipeline (no synthetic canonical construction).
# ---------------------------------------------------------------------------


# Gates whose policy can be made to fire deterministically via gate_helpers.
_FIREABLE_STOP_GATES = ["qa", "handover", "ida"]


class TestRealPipelineStopGateLeak:
    """Full pipeline: trigger the gate, route the REAL engine output, assert the
    rendered context body never reaches a user-visible Stop channel."""

    @pytest.mark.parametrize("gate_name", _FIREABLE_STOP_GATES)
    @pytest.mark.parametrize("mode", ["warn", "block"])
    def test_real_stop_gate_context_absent_from_user(self, router, monkeypatch, gate_name, mode):
        set_gate_modes(monkeypatch, **{gate_name: mode})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        assert result is not None, f"{gate_name} ({mode}) did not fire on Stop"

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")

        # Source of truth: the context body the engine actually produced for
        # this run (temp_path etc. resolved by the real custom action). Strip
        # the policy marker so the leak check is marker-independent.
        rendered_ctx = _strip_marker(result.context_injection or "")
        assert rendered_ctx, f"{gate_name} ({mode}): no context body produced by engine"

        user_vals = _user_visible_values(output)
        leaks = {
            field: value
            for field, value in user_vals.items()
            if value is not None and _body_leaked_into(value, rendered_ctx)
        }
        assert not leaks, (
            f"LEAK [real {gate_name} {mode}]: context body in user field(s) "
            f"{list(leaks)}: {next(iter(leaks.values()))[:120]!r}"
        )

    @pytest.mark.parametrize("gate_name", _FIREABLE_STOP_GATES)
    @pytest.mark.parametrize("mode", ["warn", "block"])
    def test_real_stop_gate_context_reaches_agent(self, router, monkeypatch, gate_name, mode):
        set_gate_modes(monkeypatch, **{gate_name: mode})
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)
        assert result is not None
        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")

        # Compare against the engine's actual context body (real temp_path).
        rendered_ctx = _strip_marker(result.context_injection or "")
        assert rendered_ctx, f"{gate_name} ({mode}): no context body produced by engine"

        agent_text = _agent_channel_value(output)
        assert agent_text is not None, f"{gate_name} ({mode}): no agent channel populated"
        assert _norm(rendered_ctx) in _norm(agent_text), (
            f"{gate_name} ({mode}): context body did not reach agent channel"
        )


class TestRealPipelineEnforcerLeak:
    """Full pipeline for enforcer (PreToolUse policy): the policy context body
    must not leak into the user-visible permissionDecisionReason/systemMessage."""

    @pytest.mark.parametrize("mode", ["warn", "block"])
    def test_real_enforcer_policy_context_absent_from_user(self, router, monkeypatch, mode):
        set_gate_modes(monkeypatch, enforcer=mode)
        reinit_gates_with_defaults()

        state = make_gate_trigger_state("enforcer")
        ctx = make_gate_trigger_context("enforcer")

        result = router._dispatch_gates(ctx, state)
        if result is None:
            pytest.skip("enforcer policy did not fire under current threshold config")

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "PreToolUse")

        rendered_ctx = _strip_marker(result.context_injection or "")
        assert rendered_ctx, f"enforcer ({mode}): no context body produced by engine"
        user_vals = _user_visible_values(output)
        leaks = {
            field: value
            for field, value in user_vals.items()
            if value is not None and _body_leaked_into(value, rendered_ctx)
        }
        assert not leaks, (
            f"LEAK [real enforcer {mode}]: context body in user field(s) "
            f"{list(leaks)}: {next(iter(leaks.values()))[:120]!r}"
        )
