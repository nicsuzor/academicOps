---
name: pull
type: command
category: instruction
description: Advance the queue one step — pick the next queued task and DISPATCH it to the right surface. Never executes inline. Thin one-shot alias over the program loop's dispatch trigger.
triggers:
  - "pull task"
  - "get work"
  - "what should I work on"
  - "next task"
  - "advance the queue"
modifies_files: false
needs_task: false
mode: dispatch
domain:
  - operations
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion, mcp__pkb__get_task, mcp__pkb__get_task_children, mcp__pkb__list_tasks, mcp__pkb__update_task
permalink: commands/pull
---

# /pull — Dispatch Next Queued Task

Selects the next queued task from the PKB and dispatches it to the appropriate execution surface (polecat or subagent). Performs exactly one dispatch step and exits. Do not execute the task inline in this session.

## Invocation & Arguments

- `/pull` — select the highest focus-score queued task.
- `/pull <task-id>` — select the specified task (or its first queued leaf).

## Protocol

### 1. Select the Task

- Search for task nodes with `status: "queued"`.
- If no argument is provided, list the top candidates via `mcp__pkb__list_tasks(status="queued")` and pick the one with the highest `focus_score`.
- Descend to leaf tasks if the selected task has children.
- **Freshness Pre-check**: For the selected candidate leaf task:
  - **Path Resolution Check**: Scan the task body (and title) for file or directory paths (e.g. paths starting with `aops-core/`, `specs/`, `tests/`, `.agents/`, `.github/`, or matching pattern `dir/file.ext`). Check if each path exists in the repository workspace.
    - If a path is referenced but does not exist, print a warning naming the stale reference: `[WARNING] Task brief references non-existent path: <stale-path>`.
  - **Supersession Check**:
    - If the task has a non-empty `superseded_by` field (consumes the field added by aops-a75b1fe8 #1), do not dispatch it; print a redirection warning: `[WARNING] Task <id> is superseded by <replacement-ids>` and select the next candidate.
    - If the task has a parent, retrieve the parent's children (siblings) via `mcp__pkb__get_task_children`. If the task's siblings are already `done`, the task may be superseded. Print a warning (`[WARNING] Task <id>'s siblings are already done`) and skip or flag it rather than dispatching silently.

### 2. Route the Task

- **Specialist Subagent**: If the task or parent has an assignee matching a known specialist (`marsha`, `rbg`, `pauli`, `james`, `junior`, `qa`, `enforcer`, `polecat`), dispatch using `subagent_type="[name]"`.
- **Polecat**: For repo-scoped, PR-shippable code/docs/tests without a named specialist, dispatch to a polecat.
- **Subagent**: For research or synthesis requiring findings returned to the current session, dispatch using the `Task` tool.
- **Defer**: If the task lacks necessary inputs, is blocked, or needs manual scoping, update the task with a block note and exit without dispatching.

### 3. Record and Exit

- Do not mark the task as `in_progress` from this session. The executing surface will claim it.
- If using a subagent that does not self-claim, update the task `assignee` to the subagent and add a dispatch note via `mcp__pkb__update_task`.
- Halt execution after dispatching.
