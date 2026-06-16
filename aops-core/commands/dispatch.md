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
allowed-tools: Task, Bash, Read, Grep, Skill, mcp__plugin_aops-core_pkb__get_task, mcp__plugin_aops-core_pkb__get_task_children, mcp__plugin_aops-core_pkb__list_tasks, mcp__plugin_aops-core_pkb__update_task
permalink: commands/dispatch
---

# /dispatch — Dispatch Next Queued Task to a Background Surface

Selects the next queued task and dispatches it to the appropriate background
execution surface (polecat or subagent). Performs exactly one dispatch step and
exits. **Does not execute the task inline** — for that, use `/pull`.

## Invocation & Arguments

- `/dispatch` — select the highest focus-score queued task.
- `/dispatch <task-id>` — select the specified task (or its first queued leaf).

## Execution

Delegate to the `task-lifecycle` skill in `dispatch` mode, passing all arguments
exactly as provided:

`Skill(skill="task-lifecycle", args="dispatch: <user args>")`

If no arguments are given, run:

`Skill(skill="task-lifecycle", args="dispatch")`

The skill owns the shared Select + Gates spine (premise gate, freshness
pre-check) and the routing/halt behaviour. See
[[../skills/task-lifecycle/SKILL.md]].
