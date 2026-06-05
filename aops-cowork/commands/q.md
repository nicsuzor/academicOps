---
name: q
type: command
category: instruction
description: Quick-queue a task — delegates to planner capture mode
triggers:
  - "/q"
  - "quick queue"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - planning
owner: pauli
---

# /q — Quick Queue

Captures a task by delegating to the `planner` skill in `capture` mode.

## Execution

Invoke the planner skill:
`Skill(skill="planner", args="capture: <user args>")`

Pass all arguments exactly as provided. If no arguments are given, run:
`Skill(skill="planner", args="capture")`
