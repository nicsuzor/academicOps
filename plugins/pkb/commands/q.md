---
name: q
type: command
description: Quick-queue a thought, ask, or fragment onto the task graph.
allowed-tools: Skill, mcp__services__pkb__create_task, mcp__services__pkb__update_body
---

# /q — Quick Queue

Capture the argument as work on the graph, without stopping what you were doing.
Two steps, and no third.

1. Run `Skill(skill="hydrate", args="<the argument, verbatim>")`. With no
   argument, run `Skill(skill="hydrate")` and let it read the current turn for
   what to capture.
2. Record **one** node at `status: inbox` with `create_task`, carrying the ask
   verbatim plus hydrate's shortlist in its body. Title it in the user's own
   words. The shortlist is a list of ids, so it stays true as the graph moves —
   do not expand it into prose.

Pass the argument through unchanged. Do not interpret it, expand it, or start
the work.

**Stop there.** Do not place it under a considered parent, value it, wire edges,
sort its assumptions, or decide anything. `situate` does all of that later —
inline if it is cheap, in the consolidation sweep otherwise. Capture that costs
more than a few seconds is capture that stops happening, and every judgment made
here is one made on the thinnest context anyone will ever have about this ask.

If hydrate answered the ask outright — a pure information request, no work in it
— say the answer and write no node.
