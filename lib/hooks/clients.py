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
# it is an identity map. agy collapses Claude's finer-grained events into two
# coarse invocation phases; only the two rows below are confirmed by prior
# hook behaviour (aops-jr/hooks/router.py, pre-refactor). A canonical event
# with no agy entry here has no confirmed agy wire equivalent — it simply
# never fires on agy until a client adapter wires a new agy hook and this
# table gains a row for it.
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
    if result.is_refusal:
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "permissionDecision": "deny",
                "permissionDecisionReason": result.inject_text,
            }
        }
    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": result.inject_text,
        }
    }
    if result.user_text:
        output["systemMessage"] = result.user_text
    return output


def _render_agy(result: Result) -> dict:
    # A refusal is a decision about one tool call, so the only agy event it can
    # be rendered for is a tool event. agy has no wire name for one (see
    # _TO_CANONICAL), so nothing reaches this branch today; it is here so the
    # shape is correct on the day agy gains that event, not so that a refusal
    # can be smuggled onto a prompt-level surface.
    if result.is_refusal:
        return {"allowTool": False, "denyReason": result.inject_text}
    return {"injectSteps": [{"ephemeralMessage": result.inject_text}]}
