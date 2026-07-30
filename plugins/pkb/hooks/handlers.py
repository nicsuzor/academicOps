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
user-visible one from ``messages/<name>.user.md`` beside it (lib/hooks/
messages.py). No handler here builds either from a Python literal.
"""

from __future__ import annotations

from dispatch import HookContext, Result, load_message_pair, warn


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    Loaded as a pair, because the message has two readers. The agent gets the
    instruction to hydrate; the person watching gets one line telling them the
    reminder fired — this hook fires on every prompt, so without that line the
    most frequent injection in the session is also the one they can never see
    happen.
    """
    return warn(*load_message_pair(ctx.hooks_dir, "pkb-context"))


HANDLERS: dict[str, list] = {
    "UserPromptSubmit": [search_the_pkb],
}
