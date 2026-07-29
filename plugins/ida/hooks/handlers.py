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

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it (lib/hooks/
messages.py). No handler here builds either from a Python literal.
"""

from __future__ import annotations

import messages
from context import HookContext
from result import Result, warn


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    Loaded as a pair, because the message has two readers. The agent gets the
    full instruction and the searches worth running; the person watching gets
    one line saying their prompt was routed through the PKB first — this hook
    fires on every prompt, so without that line the most frequent injection in
    the session is also the one they can never see happen.
    """
    return warn(*messages.load_pair(ctx.hooks_dir, "hearsay"))


HANDLERS: dict[str, list] = {
    "SubagentStop": [rule_against_hearsay],
}
