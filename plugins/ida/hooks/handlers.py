"""ida's hook handlers.

``rule_against_hearsay`` is the ``PostToolUse`` handler, matched to the
``Agent`` tool. It fires in the context of whoever dispatched a subagent, at
the moment that subagent's report lands, and reminds them that a report is
not evidence.

The event is load-bearing. The rule binds the *caller* — the party who has to
decide whether to trust the report — so it must be delivered on the caller's
own side. ``SubagentStop`` cannot carry it: that event fires on the stopping
subagent's context and its injection is visible only there, never to the
session that dispatched it. Aimed at the worker, this text does worse than
miss — the worker spends its final message arguing with a warning about
itself, and the caller loses the report it was waiting for.

``strip_the_reply`` is the ``Stop`` gate. It returns a ``block``
(lib/hooks/dispatch.py) directing ida to strip its own reply to the person
down to load-bearing content before it stops — not a check on what was
already said, since the hook has no transcript to read, only a reminder that
fires at the moment ida is about to speak.

The event is load-bearing, same reasoning as ``rule_against_hearsay`` above:
``Stop`` fires only on the session's own turn boundary, so registering there
scopes the gate to the face. ``SubagentStop`` fires on the *stopping
subagent's* own context — wiring it there would direct a worker or james to
strip a reply it never sends to the person, which is not what this gate is
for. Deliberately not wired.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it, loaded via
``load_message_pair`` (lib/hooks/dispatch.py). No handler here builds either
from a Python literal.
"""

from __future__ import annotations

from dispatch import HookContext, Result, block, load_message_pair, warn


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


def strip_the_reply(ctx: HookContext) -> Result | None:
    """Direct the face to strip its reply down to what is load-bearing.

    Always the same block, regardless of what actually happened this turn —
    the hook has no transcript to judge, only the fact that a stop is about to
    happen. Once per stop chain, not once per handler invocation: dispatch.py's
    structural self-loop guard suppresses the ``stop_hook_active`` re-fire, so
    this handler does not check that flag itself.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "quiet"))


HANDLERS: dict[str, list] = {
    "PostToolUse": [rule_against_hearsay],
    "Stop": [strip_the_reply],
}
