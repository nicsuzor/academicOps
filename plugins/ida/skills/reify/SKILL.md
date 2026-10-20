---
name: reify
description: Turn an objective, or a task id, into complete dispatchable tasks on the graph -- hydrate, compose the workflow from templates, write each task at `queued`, and mint any QA follow-up. Use when work needs tasks written or an existing task rewritten before a worker can pull it. Exclude for starting workers on tasks already written (use /dispatch).
---

# /reify: compose dispatchable tasks from an objective

The task is the whole message to the worker. Write it once, keep it short, and leave it on the graph for `/dispatch`. Questions and lookups are answered directly by the session that receives them; the task dispatch pipeline is used only for real code changes. Never create tasks or compose workflows for questions or lookups.

A polecat is a short-running container: it gets in, does one unit of work it controls, records the evidence, and gets out cleanly. It never sees the whole objective through. Everything after its unit is a follow-up task on the graph, and the workflow decides what those follow-ups are.

Nothing is written to the graph until steps 1-2 have passed: a task created early survives every check that later fails.

## 1. Hydrate

Call `/hydrate` on the objective, or on the task if you were given an id.

**Idempotency**: Search before creating new tasks. Update existing tasks with new criteria rather than minting duplicates. A task that is already completely specified needs no rewrite; report it as ready.

- Given a task id: read it. If it already fills the template in step 3, go to step 4.
- If `/hydrate` flags an unfinished task with the same objective, carry on with that task instead of a new one.
- If it flags a task this objective needs done first, note it for a `needs` edge.
- You may update an existing task if you need to modify context, acceptance criteria, or instructions. This includes retrying failed tasks; do not create a new task for the same work.

## 2. Compose workflows

Call `/workflow-library` to weave together every workflow relevant to the task in context. The composed workflow draws on two kinds of component, and they enter the Instructions differently:

- **Workflow templates** (`type: template`, including every `wf-*`): the worker cannot invoke them. Read each one and interpret its stages into concise numbered imperative steps in the Instructions. Where a template names a stage or a class of workflow rather than a step, resolve it to the matching templates and write their steps in too. Do not copy narrative paragraphs, rationale, or explanatory prose from templates.
- **Skills**: the worker invokes them. Write `invoke /<skill-name>` as the step and leave its contents where the skill is maintained.

Then assemble the steps:

- Combine template steps into a logical order (e.g., test-first where the change modifies code that executes, build, then QA).
- Base the assembly only on what is explicitly requested. Do not investigate, guess at scope, or ad-lib extra requirements. If the request is ambiguous, preserve that ambiguity.
- Resolve the finish template (e.g., `wf-finish`) to determine delivery route (target branch, PR requirements) and whether an independent QA follow-up is required.

**Halt when composition comes up short.** Create and change nothing; report to your caller what failed precisely.

## 3. Write each task

- Default to a single task with steps as a linear checklist; every extra cut costs a hand-off and loses context.
- Cut into separate leaves only when independent sessions are strictly required (e.g. forks, loops, independent reviews).
- Make each task as big as possible within those cuts.
- Write each follow-up the workflow calls for as its own task. Never fold a follow-up into the primary task or into another follow-up.
- Wire `needs` edges only where one unit genuinely requires another's output.
- Mint multi-task cuts using `pkb.decompose_task`.
- Write tasks with status `queued` immediately.
- Close every task with an appendix section listing the workflow templates and skills it was composed from.

```markdown
## Ask

[ The verbatim ask or asks from the user or delegating agent that authorise this task, with message ids. Record once at intake; do not edit, paraphrase, or delete. ]

## Goal

[ Concise description of the purpose of the task, describing the end state of this unit of work (not the whole objective), naming the repository or project and the objective. Recompose the ask into a clear logical structure; never quote the user's words verbatim. ]

## Context

[ Decisions and facts the worker cannot find (omit if none). Cite message ids as pointers; never record or quote the user's words verbatim. The tracing hook preserves raw prompts. ]

## Acceptance

[ Number the items `AC1`, `AC2`, ...; each number gives the item its ask id (per the `premise-check` report form), which the worker's report argument answers. Write each Acceptance item so that it requires evidence sufficient to prove the criterion has been met in substance. Verifiable evidence must be recorded on the task because the task record is the only thing that comes back. Criteria name outcomes and the evidence that proves them, not where something is wired or how it is invoked. ]

## Instructions

[ Each step the worker must follow, drawn only from the composed workflow templates. The workflow templates are the only source of truth for instructions, obligations, and required processes. Add none of your own, because the workflow is where that judgement is maintained. The last step is the finish template's finish: deliver, record the evidence, release the task, and exit. ]

## Output

[ Where the results of the task should be written. For feature branches, name the upstream repository and base branch to target per the project finish template. Outputs must not be left in the worker's local (volatile) environment. ]

## Report

[ Any special reporting requirements; default should be the `/dump` handback, with evidence next to each acceptance criterion: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. Workers should not add timestamped logs or other ephemeral data to the task record. Rewrite the record rather than appending information, and delete any temporary notes or logs, any outdated or incorrect information, and any irrelevant instructions or steps; `## Ask` and the wording and numbers of the criteria stay as written. Leave only current state. ]

## Appendix: Sources

[ List the workflow templates and skills this task was composed from (e.g. wf-task-base + wf-finish + wf-qa). ]
```

### Mint QA follow-up when required

Where the project finish template calls for QA review:

- **Low-risk internal changes (chiefly bugfixes)**: Test whether the task is a low-risk internal change, chiefly a bugfix. If so, it gets no separate verification run. Instead, look for a blocked task waiting on the fix (`blocks` or inbound `needs` / `depends_on`):
  - **Blocked dependent exists**: Mint a follow-up task with status `queued`, same parent as the primary task, and `needs: [<blocked_task_id>]` that judges the fix by reviewing that blocked task's next run once it runs. Record the follow-up ID in the primary task's `follow_up_tasks`.
  - **No blocked dependent exists**: Mint no verification follow-up task; the fix finishes without a separate verification run.
- **Other changes requiring QA**:
  1. Mint an independent follow-up task with status `queued`.
  2. Title: `QA: <primary task title>`.
  3. Set parent to the primary task's parent.
  4. Wire dependency: `needs: [<primary_task_id>]` so the QA task stays blocked until the primary task is `done`.
  5. Record the QA task ID in the primary task's `follow_up_tasks`.
  6. Compose the review follow-up task drawing its brief from the shared review briefing in `wf-review` and the designated review template (`wf-qa`, `wf-rbg`, `wf-strategic-fit`, `wf-signoff`, or `wf-fact-check`): instructions direct the reviewer to independently verify the deliverable and claims against literal acceptance criteria; confirm tier against the taxonomy; for verified Tier 1 PRs, merge to base branch on a verified pass; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off without releasing to review. A reviewer that changes code delivers it through the finish template and hands off for independent review.

### Requirements for writing tasks

- Give the worker the end state and the bounds; leave the method to it.
- Record the asker's own words once, in `## Ask`, with their ids, and never rewrite them: the task carries the ask as an immutable referent that the worker's argument answers. The no-verbatim rule below governs the rest of the body, not `## Ask`.
- Never quote or record the user's words verbatim in Goal, Context, or instructions. Make sense of asks in context, link them to prior context, recompose into a clear logical structure, and cite message ids.
- State the Goal and each criterion over the whole class the request covers: "the user's messages", not a named person's or today's channels and formats. Instances the request names are cases to test, not the boundary of the work. When asked what broke a mechanism (such as authentication, a token, or a service), compose the debugging workflow and preserve the full failure question in Acceptance so the run examines why the mechanism or token stopped working across its lifecycle rather than narrowing to a single startup symptom.
- Every heading is a prompt for you to fill, and there is no slot for restrictions or exclusions: say what has to be done, not what shouldn't.
- Keep each task under 150 words, `## Ask` aside. Include only what the worker cannot find for itself.
- Interpret workflow template stages into concise numbered imperative steps; never paste template narrative, rationale, or explanatory background.
- Assume the worker could run anywhere; never reference local paths, tools, or conventions.
- Leave out methods, command scripts, tool names, runtime hints, notes on the worker's limits, summaries of linked notes (point to them instead), provenance, changelogs, session narratives, counts, SHAs and history.
- Change an existing task only for a defect you can point to in its text; otherwise leave it as written. Never rewrite its `## Ask` or renumber its criteria: a new criterion takes the next number, and no number is reused.
- A skill may be a step, even the only step: write `invoke /<skill-name>` and leave its implementation to the skill. A workflow template is never a step; its steps are.
- Close every task with an appendix section listing the workflow templates and skills it was composed from.
- Do not create standalone decision tasks or file questions as tasks.

## 4. Report

Stop once the tasks are on the graph; `/dispatch` starts their workers.

Output one line per task written or confirmed ready: title, id, status, and its open `depends_on` edges.
