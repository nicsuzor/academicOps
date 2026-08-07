---
name: q
type: command
description: Quick-queue a thought, ask, or fragment onto the task graph.
allowed-tools: Skill, AskUserQuestion, mcp__services__pkb__create_task
---

# /q — Quick Queue

Capture the argument as work on the graph, without stopping what you were doing.
Two steps, and no third.

1. Run `Skill(skill="hydrate", args="<the argument, verbatim>")`. With no
   argument, run `Skill(skill="hydrate")` and let it read the current turn for
   what to capture.

2. Record **one** node at `status: inbox` with `pkb__create_task` (or `mcp__services__pkb__create_task` under the `services` MCP server), under the parent
   it belongs to. Title it in the user's own words, and carry the ask verbatim
   plus hydrate's shortlist in the body. The shortlist is a list of ids, so it
   stays true as the graph moves — do not expand it into prose.

Pass the argument through unchanged. Do not interpret it, expand it, or start
the work.

## Placing it

The shortlist hydrate just returned is what you place from. Reading it is the
whole of the work; do not search again.

- **A task or epic on the shortlist is the obvious home** — the ask is a
  follow-up to it, a piece of it, or the same subject. Parent it there.
- **Otherwise, the task this session already holds**, where the ask arose out of
  the work in front of you.
- **Otherwise, ask.** One `AskUserQuestion`, offering the closest candidates the
  shortlist surfaced.

`project` comes from the parent. Set it explicitly only when the parent's own
slug is wrong for this ask.

**Never park it in a catch-all, and never leave it unparented.** Everything
belongs somewhere real on the graph. A node with no parent is an orphan the next
sweep has to chase, and a junk-drawer parent is an orphan that does not show up
as one — which is worse.

## Stop there

Placement is the only judgment you make. Do not value it, wire `contributes_to`
or any other edge, sort its assumptions, name its forks, or decide anything. All
of that happens later, when the user calls for it. Capture that costs more than a
few seconds is capture that stops happening.

If hydrate answered the ask outright — a pure information request, no work in it
— say the answer and write no node.
