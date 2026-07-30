"""ida's hook handlers.

Two hooks, and each one's event is load-bearing.

``PostToolUse``, matched to the ``Agent`` tool, fires in the context of whoever
dispatched a subagent, at the moment that subagent's report lands, and reminds
them that a report is not evidence. The rule binds the *caller* — the party who
has to decide whether to trust the report — so it must be delivered on the
caller's own side. ``SubagentStop`` cannot carry it: that event fires on the
stopping subagent's context and its injection is visible only there, never to
the session that dispatched it. Aimed at the worker, this text does worse than
miss — the worker spends its final message arguing with a warning about itself,
and the caller loses the report it was waiting for.

``Stop`` carries the honesty floor, and is the counterpart: hearsay governs what
ida accepts from a worker, the floor governs what ida then asserts to the user.
``Stop`` fires only on the session's own turn boundary, so a handler registered
there reaches the face and nothing else — a subagent ends on ``SubagentStop``,
which is not wired here. That is what scopes this to ida without a per-agent
discriminator, which the hook payload does not carry.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it (lib/hooks/
messages.py). No handler here builds either from a Python literal.
"""

from __future__ import annotations

from dispatch import HookContext, Result, load_message_pair, warn


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind the dispatcher that a subagent's report is not evidence.

    Loaded as a pair, because the message has two readers. The agent gets the
    rule; the person watching gets one line saying a subagent just reported
    back and the claim is unverified — otherwise the moment a report enters
    the session's reasoning is invisible to them.

    Advisory only (``warn``): it cannot block, and the call has already run by
    the time this fires. It has one job, which is to arrive at the instant the
    caller is deciding what to believe.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


def honesty_floor(ctx: HookContext) -> Result | None:
    """Require every claim in the handback to carry its evidence and its
    confidence, at the moment ida is about to answer the user.

    Advisory (``warn``), which renders as ``additionalContext`` on this event:
    the text reaches the model and the turn continues, so ida can revise before
    the answer lands rather than being forced back into the turn.

    ``stop_hook_active`` is the guard that makes this fire once per stop-chain.
    Injecting on a stop gives the session another turn, which stops again — so
    without the check this handler would re-fire against its own continuation
    and never let the session end. ``background_tasks`` holds it silent while
    work is still running, because a handback is not being written yet.
    """
    if ctx.raw.get("stop_hook_active") or ctx.raw.get("background_tasks"):
        return None
    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


HANDLERS: dict[str, list] = {
    "PostToolUse": [rule_against_hearsay],
    "Stop": [honesty_floor],
}
