"""James's hook handlers.

"""

from __future__ import annotations

from dispatch import HookContext, Result, load_message_pair, warn


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind the dispatcher that a subagent's report is not evidence.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


HANDLERS: dict[str, list] = {
    "PostToolUse": [rule_against_hearsay]
}
