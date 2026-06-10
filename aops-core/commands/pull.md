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
- **Premise gate (hard refuse — agent judgment, not a string check)**: For the selected candidate leaf task, **read the body and judge whether it contains a genuine premise assessment** — a real one-sentence, principal-voice judgment that this task is worth doing and rightly shaped, recorded when it was promoted to `queued` (see [[premise-gate]]). This is a JUDGMENT you make by reading, **not** a regex/field/heading presence-check — a presence-check rig would itself be the deterministic-substitute-for-judgment this gate exists to stop (`judgment-non-delegable`). If the body shows no genuine premise judgment — absent, empty, a rubber-stamp ("looks fine"), or a checklist instead of a judgment — **do not dispatch and do not spend compute**: bounce the task back to the promoter (record a one-line reason via `mcp__pkb__update_task`, set `status: ready`, and assign to the promoter) so a real premise judgment is recorded before it is queued again. A genuine judgment is present → proceed.
- **Freshness Pre-check**: For the selected candidate leaf task:
  - **Path Resolution Check**: Read the task body and title and identify the file/directory paths it points an executor at — the ones a worker would open or edit (e.g. backtick- or quote-delimited tokens naming a real file: a known repo top-level segment like `commands/`, `specs/`, `tests/`, `.agents/`, `.github/`, or a token carrying a file extension). Use judgment, not a blanket slash-match: skip prose mentions, tool names (`mcp__pkb__list_tasks`), and code identifiers (`focus_score`) — they are not the brief's working paths. Then, only if the task names a `project`/repo you have checked out in this session, verify each identified path resolves there (`Read`/`ls`); if no relevant checkout is available, skip this check rather than warn on a path you cannot verify.
    - If a verified path does not resolve, print a warning naming the stale reference: `[WARNING] Task brief references non-existent path: <stale-path>` (warn, do not hard-block — the dispatching coordinator decides).
  - **Supersession Check**:
    - If the task has a non-empty `superseded_by` field (consumes the field added by aops-a75b1fe8 #1), do not dispatch it; print a redirection warning: `[WARNING] Task <id> is superseded by <replacement-ids>` and select the next candidate.
    - If the task has a parent, retrieve the parent's children (siblings) via `mcp__pkb__get_task_children`. If **all** siblings are already `done` (a heuristic, not proof — parallel siblings legitimately finish at different times), the task may be a leftover from a completed decomposition. Print a warning (`[WARNING] Task <id>'s siblings are all done — may be a stale leftover`) and flag it for the coordinator rather than dispatching silently; do not auto-skip on this signal alone.

### 2. Route the Task

- **Specialist Subagent**: If the task or parent has an assignee matching a known specialist (`marsha`, `rbg`, `pauli`, `james`, `junior`, `qa`, `enforcer`, `polecat`), dispatch using `subagent_type="[name]"`.
- **Polecat**: For repo-scoped, PR-shippable code/docs/tests without a named specialist, dispatch to a polecat.
- **Subagent**: For research or synthesis requiring findings returned to the current session, dispatch using the `Task` tool.
- **Defer**: If the task lacks necessary inputs, is blocked, or needs manual scoping, update the task with a block note and exit without dispatching.

### 3. Record and Exit

- Do not mark the task as `in_progress` from this session. The executing surface will claim it.
- If using a subagent that does not self-claim, update the task `assignee` to the subagent and add a dispatch note via `mcp__pkb__update_task`.
- The task ID is propagated directly to the execution surface via the `$AOPS_TASK_ID` environment variable and git branch name; do not synthesise a filesystem-state binding file.
- Halt execution after dispatching.
