---
name: program
type: command
category: instruction
description: Program / portfolio supervision — the autonomous top loop above /supervisor that drives a release-level goal across many epics
triggers:
  - "/program"
  - "ready the release"
  - "drive the release"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
owner: junior
permalink: commands/program
---

# /program — Program / Portfolio Supervision

Runs program-level supervision across multiple epics to achieve a release-level goal.

## Execution

Invoke the program skill directly:
`Skill(skill="program", args="<program-task-id>")`

`/program` runs a single tick. To drive a release continuously, wrap it in a loop: `/loop 30m /program <program-task-id>`.
