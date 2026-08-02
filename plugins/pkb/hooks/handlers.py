"""pkb's hook handlers.

One hook: ``UserPromptSubmit``. It tells the agent to ground the prompt in the
PKB, via the pkb:hydrate skill, before acting on it.

It does not reach the PKB itself. Establishing an MCP session, running a query,
and ranking the result costs a multi-step round trip on the critical path of
every single prompt, and a slow or unreachable server would stall the turn. The
agent already holds the PKB tools; the cheap, reliable move is to point it at
them. So this handler always takes the "instruct the agent to search" branch of
the contract in specs/ARCHITECTURE.md — it never blocks, never waits on the
network, and never invents context the PKB did not supply.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it, loaded via
``load_message_pair`` (lib/hooks/dispatch.py). No handler here builds either
from a Python literal.
"""

from __future__ import annotations

from dispatch import HookContext, Result


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    We can't run this stop on any agent that deals with subagents, because subagents returning trigger the hook and it piles up quickly and confuses the agent.
    """
    return None

    # return warn(*load_message_pair(ctx.hooks_dir, "pkb-context"))


HANDLERS: dict[str, list] = {
    # "UserPromptSubmit": [search_the_pkb],
}
