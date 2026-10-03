---
name: dispatch
description: Take an objective, assemble a compliant workflow from templates, reify the resulting worker instructions as complete dispatchable tasks, and dispatch them.
---

# /dispatch: compose a task from an objective and dispatch it

The task is the whole message to the worker. Write it once, keep it short, send it as written.

Nothing is written to the graph until steps 1-2 have passed: a task created early survives every check that later fails.

## 1. Hydrate

Call `/hydrate` on the objective, or on the task if you were given an id.

**Idempotency**: Search before creating new tasks. Update existing tasks with new criteria rather than minting duplicates. If a task is already completely specified, you may dispatch it directly without re-writing it.

- Given a task id: read it. If it already fills the template in step 3, go to step 4.
- If `/hydrate` flags an unfinished task with the same objective, carry on with that task instead of a new one.
- If it flags a task this objective needs done first, note it for a `depends_on` edge.
- You may update an existing task if you need to modify context, acceptance criteria, or instructions. This includes retrying failed tasks; do not create a new task for the same work.

## 2. Compose workflows

Call `/workflow-library` to weave together every workflow relevant to the task in context. A skill counts as a template: when one is composed, the Instructions tell the worker to invoke it by name, as one step or as all of them. Never copy its contents into the task; the skill is maintained where it lives.

- Combine template steps into a logical order (e.g., failing tests first, implementation, then QA).
- Base the assembly only on what is explicitly requested. Do not investigate, guess at scope, or ad-lib extra requirements. If the request is ambiguous, preserve that ambiguity.
- Resolve the finish template (e.g., `wf-finish`) to determine delivery route (target branch, PR requirements) and whether an independent QA follow-up is required.

**Halt when composition comes up short.** Create and change nothing; report to your caller what failed precisely.

## 3. Write each task

- Default to creating a single task with steps as a linear checklist; every extra cut costs a hand-off and loses context.
- Cut into separate leaves only when independent sessions are strictly required (e.g. forks, loops, independent reviews).
- If you must split a task, make each task as big as possible.
- Wire `depends_on` edges only where one unit genuinely requires another's output.
- Mint multi-task cuts using `pkb.decompose_task`.
- Write tasks with status `queued` immediately.

```markdown
## Goal

[ Concise description of the purpose of the task, describing the required end state, naming the repository or project and the objective. ]

## Context

[ only include decisions and facts the worker cannot find (omit if none) ]

## Acceptance

[ Write each Acceptance item so that it requires evidence sufficient to prove the criterion has been met in substance. Verifiable evidence must be recorded on the task because the task record is the only thing that comes back. ]

## Instructions

[ Each step the worker must follow, drawn only from the composed workflow templates. The workflow templates are the only source of truth for instructions, obligations, and required processes. Add none of your own, because the workflow is where that judgement is maintained. ]

## Output

[ Where the results of the task should be written. For feature branches, name the upstream repository and base branch to target per the project finish template. Outputs must not be left in the worker's local (volatile) environment. ]

## Report

[ Any special reporting requirements; default should be to update the task record with evidence of completion next to each acceptance criterion. Workers should not add timestamped logs or other ephemeral data to the task record. Rewrite the record rather than appending information, and delete any temporary notes or logs, any outdated or incorrect information, and any irrelevant instructions or steps. Leave only current state. ]
```

### Mint QA follow-up when required

Where the project finish template calls for QA review:

1. Mint an independent follow-up task with status `queued`.
2. Title: `QA: <primary task title>`.
3. Set parent to the primary task's parent.
4. Wire dependency: `depends_on: [<primary_task_id>]` so the QA task stays blocked until the primary worker completes.
5. Record the QA task ID in the primary task's `follow_up_tasks`.
6. Compose the designated QA template (`wf-qa`, `wf-signoff`, or `wf-fact-check`): instructions direct the reviewer to independently verify the PR deliverable and claims against literal acceptance criteria, and merge to the target branch when verified per the finish template.

### Requirements for writing tasks

- Give the worker the end state and the bounds; leave the method to it.
- Every heading is a prompt for you to fill, and there is no slot for restrictions or exclusions: say what has to be done, not what shouldn't.
- Keep each task under 150 words. Include only what the worker cannot find for itself.
- Assume the worker could run anywhere; never reference local paths, tools, or conventions.
- Leave out methods, tool names, runtime hints, notes on the worker's limits, summaries of linked notes, counts and history.
- Change an existing task only for a defect you can point to in its text; otherwise send it as written.
- It is valid for a task to call a skill as a step (even as the only step). Write `invoke /<skill-name>` as the step; do not repeat the skill's implementation in the task itself.

**Exclusions:**

- Omit execution methods, command scripts, or implementation hints.
- Omit summaries of linked notes; reference documents by pointer.
- Omit provenance, changelogs, session narratives, and perishable counts or SHAs.
- Do not create standalone decision tasks or file questions as tasks.
- Do not dispatch workers or begin execution.

## 4. Dispatch

A task is ready to dispatch when its status is `queued` and it has no open `depends_on` edges or incomplete children.

- You should dispatch multiple tasks in parallel where possible.
- Start workers through your project's specified dispatch pathway.
- Any minted QA follow-up task remains queued until its hard dependency completes.

## 5. Report

- Dispatch is 'fire-and-forget': you do not get a report back from the worker. Do not poll or wait for a worker to return.
- Output only a summary of tasks dispatched: one line per task, including title, id, and any identification of the worker assigned.
