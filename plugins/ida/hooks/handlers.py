"""ida's hook handlers.

``be_quiet`` reminds ida to strip its own reply to the person down to
load-bearing content — not a check on what was already said, since the hook has
no transcript to read, only a reminder that fires before ida speaks again.

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

from dispatch import HookContext, Result, load_message_pair, warn


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing.

    Always the same reminder, regardless of what actually happened this turn —
    the hook has no transcript to judge, only the fact that ida is about to
    speak. Once per stop chain, not once per handler invocation: dispatch.py's
    structural self-loop guard suppresses the ``stop_hook_active`` re-fire, so
    this handler does not check that flag itself.
    """
    # Only fire on Ida
    if ctx.agent_type == "ida:ida":
        return warn(*load_message_pair(ctx.hooks_dir, "quiet"))


HANDLERS: dict[str, list] = {
    # "PostToolBatch": [be_quiet],
}
