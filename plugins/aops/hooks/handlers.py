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
    if (
        ctx.agent_type == "aops:ida"
    ):  # NS: this reference to the plugin name needs to be made into a constant -- others too.
        # No need to do anything until the background tasks complete.
        if ctx.raw.get("background_tasks"):
            return None

        return warn(*load_message_pair(ctx.hooks_dir, "quiet"))
        _ = warn


HANDLERS: dict[str, list] = {
    "PostToolBatch": [be_quiet],
}
