---
name: dispatch
type: command
category: instruction
description: Advance the queue one step — pick the next queued task and DISPATCH it to a background surface (polecat or subagent). Never executes inline. Thin alias over the task-lifecycle skill's dispatch mode.
triggers:
  - "dispatch task"
  - "dispatch next"
  - "send work to a worker"
  - "advance the queue"
modifies_files: false
needs_task: false
mode: dispatch
domain:
  - operations
allowed-tools: Skill
permalink: commands/dispatch
---

# /dispatch — Dispatch Next Queued Task to a Background Surface

Selects the next queued task and dispatches it to the appropriate background
execution surface (polecat or subagent). Performs exactly one dispatch step and
exits. **Does not execute the task inline** — for that, use `/pull`.

## Execution

Delegate to the `task-lifecycle` skill in `dispatch` mode, passing all arguments
exactly as provided:

`Skill(skill="task-lifecycle", args="dispatch: <user args>")`

If no arguments are given, run:

`Skill(skill="task-lifecycle", args="dispatch")`
