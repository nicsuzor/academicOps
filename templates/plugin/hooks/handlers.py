"""Example hook handlers.

Registered against the canonical event names and loaded by the shared runtime
in ``dispatch.py``, which puts this directory on ``sys.path`` before importing this module.
"""

from __future__ import annotations

from dispatch import HookContext, Result, load_message_pair, warn


def example_check(ctx: HookContext) -> Result | None:
    """An example hook handler that currently does nothing.

    You can inspect the context properties such as `ctx.tool`, `ctx.session_id`,
    and the raw JSON event in `ctx.raw`.

    To inject a warning into the agent's context without blocking:
        return warn("Agent message", "User-visible message")

    To block an action from proceeding (like refusing a tool call):
        return refuse("Agent refusal reason", "User-visible refusal reason")
    """
    return None


def remind_to_be_honest(ctx: HookContext) -> Result | None:
    """Example: Remind the agent to be honest before it acts on a user prompt.

    This handler returns an advisory warning (warn) that is injected into the
    agent's context. The strings are loaded canonically from `messages/honest.md`
    (for the agent) and optionally `messages/honest.user.md` (the one-liner the
    user sees in their terminal).
    """
    return warn(*load_message_pair(ctx.hooks_dir, "honest"))


# Map canonical event names to lists of handler functions.
HANDLERS = {
    "PreToolUse": [example_check],
    "UserPromptSubmit": [remind_to_be_honest],
}
