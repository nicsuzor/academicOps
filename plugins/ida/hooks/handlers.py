"""ida's hook handlers.

Two handlers, both on ``PostToolBatch``, and the event is load-bearing for both.

``be_quiet`` reminds ida to strip its own reply to the person down to
load-bearing content — not a check on what was already said, since the hook has
no transcript to read, only a reminder that fires before ida speaks again.

``render_landed`` puts the completion line for any finished delegated unit into
the daily note. It has to run *before* ida's next words exist, not after, because
the whole contract is that the line ida speaks is a pointer to a record already
on disk. ``PostToolBatch`` fires after a batch of tool calls and before the model
produces its next text, which is the only event in the set that gives that
ordering. ``Stop`` fires once the turn's text is already written, so a renderer
wired there would always be one turn late — it would announce a record it had
not yet made.

``SubagentStop`` fires on the *stopping subagent's* own context. Wiring
``be_quiet`` there would direct a worker to strip a reply it never sends to the
person, which is not what that gate is for. Deliberately not wired.

Every agent-visible string comes from ``messages/<name>.md``. A ``*.user.md``
sibling, if one exists, becomes a ``systemMessage`` the person actually reads
(lib/hooks/dispatch.py). No handler here builds either from a Python literal.

**There is deliberately no ``quiet.user.md``.** A gate that announces itself is
itself a mention of the delegated work, and the one thing this plugin owes Nic
between an instruction and its completion is silence. ``load_message_pair``
returns ``None`` for a missing user file and ``dispatch.py`` then emits no
``systemMessage`` at all, so the file's absence *is* the suppression — a
mechanism, not an instruction to be quiet.
"""

from __future__ import annotations

import os
from datetime import date

from dispatch import HookContext, Result, load_message_pair, warn


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing.

    Always the same reminder, regardless of what actually happened this turn —
    the hook has no transcript to judge, only the fact that ida is about to
    speak. Once per stop chain, not once per handler invocation: dispatch.py's
    structural self-loop guard suppresses the ``stop_hook_active`` re-fire, so
    this handler does not check that flag itself.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "quiet"))


def render_landed(ctx: HookContext) -> Result | None:
    """Put the day's finished delegated units into the daily note. Silently.

    Returns ``None`` on every path, including failure. This handler exists to
    make a record, not to say anything: it must add nothing to the agent's
    context and nothing to the person's, or it becomes the very leak the
    capability it serves exists to close. ``dispatch.py`` turns a raised
    exception into an agent-visible warning, so everything here is caught rather
    than allowed to escape.

    Cheap enough for a per-tool-batch cadence because ``sweep`` is bounded twice
    over: to task files the day has touched, and among those to the ones carrying
    an outcome marker the graph's own status agrees with. Set
    ``AOPS_LANDED_DISABLE`` to turn it off without unwiring anything.
    """
    if os.environ.get("AOPS_LANDED_DISABLE"):
        return None
    try:
        import landed

        aca_data = landed.resolve_aca_data()
        if aca_data is None:
            return None
        landed.sweep(aca_data, day=date.today(), create=(aca_data / "daily").is_dir())
    except Exception:  # noqa: BLE001 - a broken renderer must never become a message
        pass
    return None


HANDLERS: dict[str, list] = {
    "PostToolBatch": [be_quiet, render_landed],
}
