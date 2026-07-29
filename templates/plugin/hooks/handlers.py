"""Example hook handlers.

Registered against the canonical event names and loaded by the shared runtime 
in ``dispatch.py``, which puts this directory on ``sys.path`` before importing this module.
"""

from __future__ import annotations

import result
from context import HookContext


def example_check(ctx: HookContext) -> result.Result | None:
    """An example hook handler that currently does nothing.
    
    You can inspect the context properties such as `ctx.tool`, `ctx.session_id`, 
    and the raw JSON event in `ctx.raw`.

    To inject a warning into the agent's context without blocking:
        return result.warn("Agent message", "User-visible message")
        
    To block an action from proceeding (like refusing a tool call):
        return result.refuse("Agent refusal reason", "User-visible refusal reason")
    """
    return None


# Map canonical event names to lists of handler functions.
HANDLERS = {
    "PreToolUse": [example_check],
    "PostInvocation": [example_check],
}
