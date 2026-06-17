---
name: pull
type: command
category: instruction
description: Claim the next queued task and run it INLINE in this interactive session — with licence to ask the user questions. Thin alias over the task-lifecycle skill's execute mode. For background dispatch use /dispatch.
triggers:
  - "pull task"
  - "get work"
  - "what should I work on"
  - "next task"
  - "claim and run a task"
modifies_files: true
needs_task: false
mode: execute
domain:
  - operations
allowed-tools: Task, Bash, Read, Grep, Edit, Write, Skill, AskUserQuestion, mcp__plugin_aops-core_pkb__get_task, mcp__plugin_aops-core_pkb__get_task_children, mcp__plugin_aops-core_pkb__list_tasks, mcp__plugin_aops-core_pkb__update_task
permalink: commands/pull
---

# /pull — Claim and Run the Next Queued Task Inline

Selects the next queued task and **runs it in the current interactive session**:
claim → execute → verify → complete. Because this is interactive, you may ask the
user questions whenever a decision is genuinely theirs. To hand work to a
background worker instead, use `/dispatch`.

## Invocation & Arguments

- `/pull` — claim the highest focus-score queued task and run it.
- `/pull <task-id>` — claim the specified task (or its first queued leaf).

## Execution

Delegate to the `task-lifecycle` skill in `execute` mode, passing all arguments
exactly as provided:

`Skill(skill="task-lifecycle", args="execute: <user args>")`

If no arguments are given, run:

`Skill(skill="task-lifecycle", args="execute")`

The skill owns the shared Select + Gates spine (premise gate, freshness
pre-check) and the inline claim/execute/verify/complete lifecycle. See
[[../skills/task-lifecycle/SKILL.md]].

<!-- cowork:only -->

## Cowork: native-list mirror

On the Cowork surface the claim step mirrors the task onto the native task list.
`/pull` and `/end_session` are the only drivers of that mirror — see
[[../skills/cowork-sync/SKILL.md]]. If `/pull` is run again in the same session,
the prior parent native task is cancelled before the new one is mirrored.

<!-- /cowork:only -->
