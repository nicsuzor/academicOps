---
name: reify
description: Bind one node that is next to run to its executor and workflow -- hydrate, compose the workflow from templates, write the task at `queued`, and mint any QA follow-up. Use when a node is about to be dispatched and needs its task written or rewritten; the PKB custodian (Pauli) runs it. Exclude for expanding an objective into sub-objectives (use decompose) or starting workers on tasks already written (use dispatch).
---

# /reify: compose the dispatchable task for a node that is next to run

**Object: one node, at dispatch time.** Reifying binds the node to an executor class and to the workflow templates current now; both change, so a task reified before it can run goes stale on the graph. Reify a node when `/dispatch` is about to take it or the user directs it to be written, and leave a node blocked on an external condition unreified until that clears. Given a parent, reify only the children ready to run. The PKB custodian (Pauli) runs this skill; callers send the node or objective and receive task IDs.

The task is the whole message to the worker. Write it once, keep it short, and leave it on the graph for `/dispatch`. Questions and lookups answered in-turn need no task.

Nothing is written to the graph until steps 1-2 pass: a task created early survives checks that later fail.

## 1. Hydrate

Call `/hydrate` on the objective, or on the task if given an ID.

- **Idempotency**: Search before creating tasks. Update existing tasks with new criteria rather than minting duplicates. A task already completely specified needs no rewrite; report it as ready.
- If `/hydrate` flags an unfinished task with the same objective, continue that task instead of creating a new one.
- If it flags an unfinished prerequisite, wire a `needs` dependency.

## 2. Compose workflows

Call `/workflow-library` to select the modular workflow templates (`type: template`, including `wf-*`) and skills that govern the requested work. Workflows come from workflow templates: templates define the obligations, stages, reviews, and criteria. Do not add restrictions, follow-up gates, or verification processes outside those defined by the composed workflow templates.

- **Workflow templates**: The worker cannot invoke templates directly. Read each selected template and interpret its stages into concise, numbered imperative steps in `## Instructions`. Do not copy narrative rationale, explanatory prose, or background.
- **Skills**: The worker invokes skills. Write `invoke /<skill-name>` as the step and leave its procedure where the skill is maintained.
- **Agentic-first**: Where a task involves qualitative judgment, sampling, curation, classification, or recommendation, compose an agent workflow rather than specifying deterministic scripts or wrappers.

Halt when composition comes up short: create nothing and report precisely what failed.

## 3. Write each task

Structure work as a single task by default. Cut into dedicated epics with child tasks or internal subtasks only when the composed workflow or execution boundaries require independent sessions, distinct review personas, or approval gates (`wf-task-base`). Wire `needs` dependencies where one unit requires another's output. Write tasks with status `queued`.

- **QA follow-ups**: Where the composed workflow warrants an independent review pass for pull request deliverables, `/reify` mints an independent downstream `QA: <task>` child task under the dedicated epic (`needs: [<primary_task_id>]`).
- **Non-PR QA child rule**: Mint a separate `QA: <primary task title>` child task under the dedicated epic (`needs: [<primary_task_id>]`) only where the composed workflow warrants an independent verification check (such as empirical analyses requiring numerical replication, high-impact specification or policy changes, or multi-step qualitative audits). Workflows that do not warrant an additional verification pass mint no QA child. Across all non-PR tasks, worker self-release to `done` remains standard upon fulfilling frozen acceptance criteria with concrete evidence; workers are not held in `review`.

Fill the canonical task structure:

```markdown
## Ask

[ Verbatim authorising ask from the user or delegating agent with message IDs. Immutable referent; do not paraphrase or edit. ]

## Goal

[ Concise description of the unit's end state, naming target repo/system and objective. Restate asks by meaning and distinctions, not wording. ]

## Context

[ Decisions and facts the worker cannot discover for itself (omit if none). ]

## Acceptance

[ Numbered criteria (AC1, AC2, ...). Criteria state observable outcomes and verifiable evidence proving substantive completion, not line numbers, line ranges, or narrow slice prescriptions. ]

## Instructions

[ Concise numbered imperative steps drawn solely from the composed workflow templates, ending with deliverable delivery, evidence recording, and task release. ]

## Output

[ Destination repository and target branch or artifact path per the workflow. ]

## Report

[ Handback reporting contract; default is /dump with evidence next to each acceptance criterion. ]

## Appendix: Sources

[ List of workflow templates and skills this task was composed from. ]
```

### Requirements for writing tasks

- Filter incoming mechanism prescriptions and translate them into observable outcome criteria. Line numbers, line ranges, and narrow code slice prescriptions are strictly forbidden in `Goal`, `Acceptance`, and `Instructions`. Give the worker the end state and the bounds; leave the method to it.
- Record the asker's own words once, in `## Ask`, with their ids, and never rewrite them: the task carries the ask as an immutable referent that the worker's argument answers and that checkers read to test the restatement for fidelity, completeness, and overreach. The no-verbatim rule below governs the rest of the body, not `## Ask`.
- Restate the user's terse, fragmented words into clear, complete tasks and notes, judged by fidelity to their meaning and distinctions, not by wording. Keeping exact words in PKB outputs is not a goal. Fault a restatement only for lost, added, or distorted meaning. Link asks to prior context, recompose into a clear logical structure, and cite message ids.
- State the Goal and each criterion over the whole class the request covers: "the user's messages", not a named person's or today's channels and formats. Instances the request names are cases to test, not the boundary of the work. When asked what broke a mechanism (such as authentication, a token, or a service), compose the debugging workflow and preserve the full failure question in Acceptance so the run examines why the mechanism or token stopped working across its lifecycle rather than narrowing to a single startup symptom.
- Every heading is a prompt for you to fill, and there is no slot for restrictions or exclusions: say what has to be done, not what shouldn't.
- Keep each task strictly concise: 50–150 words for atomic tasks, up to 300 words for multi-stage composite workflows, `## Ask` aside. Include only what the worker cannot find for itself.
- Interpret workflow template stages into concise numbered imperative steps; never paste template narrative, rationale, or explanatory background.
- Assume the worker could run anywhere; never reference local paths, tools, or conventions.
- Leave out methods, command scripts, tool names, runtime hints, notes on the worker's limits, summaries of linked notes (point to them instead), provenance, changelogs, session narratives, counts, SHAs and history.
- Change an existing task only for a defect you can point to in its text; otherwise leave it as written. Never rewrite its `## Ask` or renumber its criteria: a new criterion takes the next number, and no number is reused.
- A skill may be a step, even the only step: write `invoke /<skill-name>` and leave its implementation to the skill. A workflow template is never a step; its steps are.
- Close every task with an appendix section listing the workflow templates and skills it was composed from.
- Do not create standalone decision tasks or file questions as tasks, with the exception of design research tasks: any research task on a design question gets, by default, a decision task assigned to the user (assignee: user) that depends on the research results, in which the user chooses the implementation route.

## 4. Report

Stop once tasks are written to the graph; `/dispatch` starts their workers. Output one line per task written or confirmed ready: title, ID, status, and open `needs` dependencies.
