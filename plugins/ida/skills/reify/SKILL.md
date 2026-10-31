---
name: reify
description: Bind one node that is next to run to its executor and workflow -- hydrate, compose the workflow from templates, and write the task at `queued`. Use when a node is about to be dispatched and needs its task written or rewritten; the PKB custodian (Pauli) runs it. Exclude for expanding an objective into sub-objectives (use decompose) or starting workers on tasks already written (use dispatch).
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

Structure work as a single task by default. Cut into dedicated epics with child tasks or internal subtasks only when the composed workflow or execution boundaries require independent sessions, distinct review personas, or approval gates. Wire `needs` dependencies where one unit requires another's output. Write tasks with status `queued`.

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

## 4. Report

Stop once tasks are written to the graph; `/dispatch` starts their workers. Output one line per task written or confirmed ready: title, ID, status, and open `needs` dependencies.
