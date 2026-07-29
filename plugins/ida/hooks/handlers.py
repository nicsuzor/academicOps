"""ida's hook handlers.

One hook: ``PostToolUse``, matched to the ``Agent`` tool. It fires in the
context of whoever dispatched a subagent, at the moment that subagent's report
lands, and reminds them that a report is not evidence.

The event is load-bearing. The rule binds the *caller* — the party who has to
decide whether to trust the report — so it must be delivered on the caller's
own side. ``SubagentStop`` cannot carry it: that event fires on the stopping
subagent's context and its injection is visible only there, never to the
session that dispatched it. Aimed at the worker, this text does worse than
miss — the worker spends its final message arguing with a warning about
itself, and the caller loses the report it was waiting for.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it (lib/hooks/
messages.py). No handler here builds either from a Python literal.
"""

from __future__ import annotations

import messages
from context import HookContext
from result import Result, warn


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
    return warn(*messages.load_pair(ctx.hooks_dir, "hearsay"))


HANDLERS: dict[str, list] = {
    "PostToolUse": [rule_against_hearsay],
}
