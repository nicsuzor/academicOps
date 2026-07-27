"""Client-neutral wire translation: event-name aliases and response shape.

Almost every hook in specs/ARCHITECTURE.md's Hooks table — including cope's
PreToolUse rule enforcement — is advisory only: nothing in-session blocks on a
rule verdict (see the Enforcement section). One hook refuses, and only on a
capability fact rather than a verdict: a headless session cannot answer an
interactive prompt. So there are two non-empty response shapes per client, and
which one is rendered is decided in exactly one place — ``Result.is_refusal``
(lib/hooks/result.py), where the rule about when a refusal is legitimate is
also written down. Both directions of per-client naming are normalized here,
once, so no ``if client == "agy"`` needs to scatter through handler logic.
"""

from __future__ import annotations

from result import Result

# The canonical event vocabulary — exactly the events named in
# specs/ARCHITECTURE.md's Hooks table. Claude's own event names ARE this
# vocabulary. Every event here is one a plugin may register a Python handler
# for; ts's SessionEnd hook is a plain shell script that never routes through
# dispatch.py, so it registers nothing, but the table names the event and this
# tuple tracks the table.
CANONICAL_EVENTS: tuple[str, ...] = (
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "Stop",
    "SubagentStop",
)

# Wire event name (as a given client's own hook config names it) -> the
# canonical name above. Claude's vocabulary is the canonical vocabulary, so
# it is an identity map.
#
# agy fires five hook events in all — PreToolUse, PostToolUse, PreInvocation,
# PostInvocation and Stop (the "Supported Event Types" table in the reference
# document the agy CLI embeds in its own binary). It has no session-level
# event of any kind, so SessionStart and SessionEnd cannot fire there and no
# row can be written for them. The two rows below are the invocation phases,
# which are the two agy events whose payload lib/hooks/context.py can read;
# agy's tool events carry a differently shaped payload and stay unmapped
# until it can. A canonical event with no agy entry never fires on agy.
_TO_CANONICAL: dict[str, dict[str, str]] = {
    "claude": {name: name for name in CANONICAL_EVENTS},
    "agy": {
        "PreInvocation": "UserPromptSubmit",
        "PostInvocation": "Stop",
    },
}


def wire_events(client: str) -> dict[str, str]:
    """This client's whole wire vocabulary: wire event name -> canonical name.

    The build and its tests need to know which canonical events a client can
    actually fire, so they read it from this table rather than restating it.
    An unknown client has no vocabulary — an empty mapping, not an error.
    """
    return dict(_TO_CANONICAL.get(client, {}))


def to_canonical(client: str, wire_event: str) -> str | None:
    """Map a client's wire event name to the canonical name.

    Returns ``None`` if this client has no hook wired for that event — the
    caller's response is a clean no-op, not an error.
    """
    return _TO_CANONICAL.get(client, {}).get(wire_event)


def render(client: str, event: str, result: Result | None) -> dict:
    """Render a handler result to the client's wire format.

    ``{}`` means nothing to say — no output, no side effect.
    """
    if result is None:
        return {}
    if client == "claude":
        return _render_claude(result, event)
    if client == "agy":
        return _render_agy(result)
    raise ValueError(f"render: unknown client {client!r}")


def _render_claude(result: Result, event: str) -> dict:
    """Claude Code carries both readers: `hookSpecificOutput` goes to the agent,
    `systemMessage` prints one line to the person watching. A refusal needs the
    user line most of all — the agent is being told no, and the only signal the
    user gets that a hook intervened is that line."""
    if result.is_refusal:
        specific = {
            "hookEventName": event,
            "permissionDecision": "deny",
            "permissionDecisionReason": result.inject_text,
        }
    else:
        specific = {"hookEventName": event, "additionalContext": result.inject_text}
    output: dict = {"hookSpecificOutput": specific}
    if result.user_text:
        output["systemMessage"] = result.user_text
    return output


def _render_agy(result: Result) -> dict:
    # agy has no user-facing channel, so `user_text` is dropped here rather
    # than smuggled onto an agent-facing one. Its documented response steps are
    # `ephemeralMessage` (a transient system message the model reads),
    # `userMessage` (injected as if the person had typed it) and `toolCall` —
    # all of them speak to the agent, and the middle one would misattribute the
    # framework's words to the user. A line meant for a human watching the
    # session has nowhere to go on this client, which is a fact about agy.
    # A refusal is a decision about one tool call, so the only agy event it can
    # be rendered for is a tool event. No agy tool event is mapped (see
    # _TO_CANONICAL), so nothing reaches this branch today; it is here so the
    # shape is correct on the day one is, not so that a refusal can be smuggled
    # onto a prompt-level surface. The shape is agy's documented PreToolUse
    # response — `decision` is one of allow/deny/ask, with `reason` alongside.
    if result.is_refusal:
        return {"decision": "deny", "reason": result.inject_text}
    return {"injectSteps": [{"ephemeralMessage": result.inject_text}]}
