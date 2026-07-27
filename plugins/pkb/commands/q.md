---
name: q
type: command
description: Quick-queue a thought, ask, or fragment onto the task graph.
allowed-tools: Skill
---

# /q — Quick Queue

Capture the argument as work on the graph, without stopping what you were doing.

Run `Skill(skill="situate", args="<the argument, verbatim>")`. With no argument,
run `Skill(skill="situate")` and let it read the current turn for what to
capture.

Pass the argument through unchanged. Do not interpret it, expand it, or start
the work — `situate` hydrates it, places one task, and stops.
