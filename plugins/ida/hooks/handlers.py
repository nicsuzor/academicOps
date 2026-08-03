"""ida's hook handlers.

``strip_the_reply`` is the ``Stop`` gate, and the only handler here. It returns a ``warn``
(lib/hooks/dispatch.py) reminding ida to strip its own reply to the person
down to load-bearing content before it stops — not a check on what was
already said, since the hook has no transcript to read, only a reminder that
fires at the moment ida is about to speak.

The event is load-bearing. ``Stop`` fires only on the session's own turn
boundary, so registering there scopes the gate to the face — ida is the only
agent this plugin ships, and the only one that speaks to the person.
``SubagentStop`` fires on the *stopping
subagent's* own context — wiring it there would direct a worker to strip a
reply it never sends to the person, which is not what this gate is for.
Deliberately not wired.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it, loaded via
``load_message_pair`` (lib/hooks/dispatch.py). No handler here builds either
from a Python literal.
"""

from __future__ import annotations

from dispatch import HookContext, Result, load_message_pair, warn


def strip_the_reply(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing.

    Always the same reminder, regardless of what actually happened this turn —
    the hook has no transcript to judge, only the fact that a stop is about to
    happen. Once per stop chain, not once per handler invocation: dispatch.py's
    structural self-loop guard suppresses the ``stop_hook_active`` re-fire, so
    this handler does not check that flag itself.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "quiet"))


HANDLERS: dict[str, list] = {
    # "Stop": [strip_the_reply],
}
