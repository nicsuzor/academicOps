---
name: dispatch
description: Take an objective, assemble a compliant workflow from templates, reify the resulting worker instructions as complete dispatchable tasks, and dispatch them.
---

# /dispatch: compose a task from an objective and dispatch it

The task is the whole message to the worker. Write it once, keep it short, send it as written.

## 1. Get or create the task

**Idempotency**: Search before creating new tasks. Update existing tasks with new criteria rather than minting duplicates. If a task is already completely specified, you may dispatch it directly without re-writing it.

- Retrieve the task description from the PKB using the Task ID provided.
- If you are not given a task ID, you must create one via `/q` using the provided description. Make sure you search the PKB first and consolidate into existing related tasks and avoid splitting the record with duplicates.

## 2. Obtain required context

Call `/hydrate` to retrieve any required context for the task.

## 3. Compose all relevant workflows

Once you have the context you need, call `/workflow-library` to weave together all workflows that are relevant to the task in context.

## 4. Write each task

- Default to creating a single task with steps as sub-tasks; every extra cut costs a hand-off and loses context.
- Cut into separate leaves only when independent sessions are strictly required (e.g. forks, loops, independent reviews).
- If you must split a task, make each task as big as possible.
- Wire `depends_on` edges only where one unit genuinely requires another's output.
- Mint multi-task cuts using `pkb.decompose_task`.'

```markdown
## Goal

[ the end state, in the ask's words, naming what it applies to by PKB id or repo ]

## Context

[ only include decisions and facts the worker cannot find (omit if none) ]

## Acceptance

[ Write each Acceptance item so that it requires evidence sufficient to prove the criterion has been met in substance. Verifiable evidence must be recorded on the task because the task record is the only thing that comes back. ]

## Instructions

[ Each step the worker must follow, drawn only from the composed workflow templates. The workflow templates are the only source of truth for instructions, obligations, and required processes. Add none of your own, because the workflow is where that judgement is maintained. ]
```

- Give the worker the end state and the bounds; leave the method to it.
- Every heading is a prompt for you to fill, and there is no slot for restrictions or exclusions:ay what has to be done, not what shouldn't.
- Keep each task under 150 words. Include only what the worker cannot find for itself.
- Assume the worker could run anywhere; never reference local paths, tools, or conventions.
- Leave out methods, tool names, runtime hints, notes on the worker's limits, summaries of linked notes, counts and history.
- Change an existing task only for a defect you can point to in its text; otherwise send it as written.

**Exclusions:**

- Omit execution methods, command scripts, or implementation hints.
- Omit summaries of linked notes; reference documents by pointer.
- Omit provenance, changelogs, session narratives, and perishable counts or SHAs.
- Do not create standalone decision tasks or file questions as tasks.
- Do not dispatch workers or begin execution.

## 5. Dispatch

Set each task with no open `depends_on` to `queued` and start a worker on it through the project's dispatch pathway.

## 6. Report

- Dispatch is 'fire-and-forget': you do not get a report back from the worker. Do not poll or wait for a worker to return.
- Output only a summary of tasks dispatched: one line per task, including title, id, and any identification of the worker assigned.
