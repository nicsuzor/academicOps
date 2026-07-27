"""pkb's hook handlers.

One hook: ``UserPromptSubmit``. It tells the agent to ground the prompt in the
PKB before acting on it, and names the searches worth running.

It does not reach the PKB itself. Establishing an MCP session, running a query,
and ranking the result costs a multi-step round trip on the critical path of
every single prompt, and a slow or unreachable server would stall the turn. The
agent already holds the PKB tools; the cheap, reliable move is to point it at
them. So this handler always takes the "instruct the agent to search" branch of
the contract in specs/ARCHITECTURE.md — it never blocks, never waits on the
network, and never invents context the PKB did not supply.

All injected wording lives in ``hooks/messages/``.
"""

from __future__ import annotations

from context import HookContext
from result import Result, warn


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it."""
    return warn(ctx.message("pkb-context"))


HANDLERS: dict[str, list] = {
    "UserPromptSubmit": [search_the_pkb],
}
