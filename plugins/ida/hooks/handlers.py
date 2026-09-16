"""ida hook handlers."""

from __future__ import annotations

from collections.abc import Callable

from dispatch import HookContext, Result, load_message_pair, warn

Handler = Callable[[HookContext], Result | None]


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing."""
    # Only fire on Ida
    if ctx.agent_type == "ida:ida":
        if ctx.raw.get("background_tasks"):
            return None
        return warn(*load_message_pair(ctx.hooks_dir, "quiet"))

    return None


HANDLERS: dict[str, list] = {
    # "PreToolUse": [premise_check_handler],
    "Stop": [],
    # "PostToolBatch": [premise_check_arm],
    # "PostToolBatch": [be_quiet],
}
