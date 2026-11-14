---
name: reify
description: Bind a situated node or directive to its executor and composed workflow on a combined task body. Use inside container supervision (/supervise) or on explicit planning requests to resolve templates across project, PKB, and universal tiers. Exclude for expanding objectives into sub-objectives (use decompose) or starting workers on tasks already written (use dispatch).
---

# /reify: Compose the Dispatchable Workflow for a Node or Directive

**Object: one node or directive, at execution or planning time.** Reifying binds the unit of work to an executor class and to the workflow templates current now. Run this skill inside container supervision (`/supervise`) or on an explicit planning request (executed by `pauli` or lead executor). Given a parent container, reify only the children ready to run.

The task is the whole message to the worker. Write it once, keep it short, and leave it on the graph. Questions and lookups answered in-turn need no task.
Nothing is written to the graph until placement and composition pass.

## 0. Verify Placement (/q Precondition)

Reifying binds an already situated node to execution. A node must be situated on the strategic graph under an active parent container (epic or project) and wired per the Three-Purpose Edge Taxonomy (ADR-0002) before it can be reified.

- **Unplaced Asks / Objectives**: If called with a raw natural-language ask or an unplaced objective lacking a parent container, do not write a task to the project root. Invoke `/q` first to search existing work, place the node under the active governing epic, and wire what it serves.
- **Unparented Existing Tasks**: If given an unparented task ID, search for its governing epic and update its parentage via `/q` placement before proceeding with workflow composition.

## 1. Hydrate

Call `/hydrate` on the objective, or on the task if given an ID. Proof of `/hydrate` execution (or citation of hydration findings) is required before proceeding to task composition.

- **Idempotency**: Search before creating tasks. Update existing tasks with new criteria rather than minting duplicates. A task already completely specified needs no rewrite; report it as ready.
- If `/hydrate` flags an unfinished task with the same objective, continue that task instead of creating a new one.
- If it flags an unfinished prerequisite, wire a `needs` dependency.

## 2. Compose Workflows

- **Single-Skill Fast-Path**: When a task's sole required work is invoking a single skill (`invoke /<skill>`), that skill sets the workflow. Skip further template resolution and report the task ready as written.
- **Three-Tier Template Resolution**: Enumerate composable workflow templates (`type: template`, including `wf-*`) dynamically in strict priority order:
  1. _Project_: PKB templates with `project: "<project>"` (strip `<project>-` prefix to get the shadowing slug). Scoped to the task's project; foreign-project templates are ignored during composition.
  2. _PKB_: Portable PKB templates with `project: null`.
  3. _Universal_: Core templates in the sibling `workflow-library/workflows/*.md` directory (`../workflow-library/workflows/*.md` relative to this skill; enumerate and read via native file tools rather than shell commands).
     Higher tiers shadow lower tiers completely; never merge text across tiers. Both PKB tiers resolve from the graph alone.
- **Groundwork-First Route Decisions Invariant**: An agent given a task does the groundwork and makes the decision itself; it never files the task back to the user as their decision (`assignee: user`) unless the user explicitly requested to make that decision themselves. Research tasks investigating design or implementation trade-offs evaluate alternatives and choose the recommended route directly.
- **Template Interpretation**: Read each selected template and translate its stages into concise, numbered imperative steps in `## Instructions`. Do not copy narrative rationale, explanatory prose, or background. Skills are invoked directly (`invoke /<skill-name>`). Where tasks involve qualitative judgment, curation, or evaluation, compose an agent workflow rather than specifying deterministic scripts or wrappers.

Halt when composition comes up short: create nothing and report precisely what failed.

## 3. Write Each Task

- **No-Split Default (Combined Task Body)**: Structure work as a single repository-scoped task body by default (up to 300 words for composite workflows, `## Ask` aside). Keep execution planning, in-session specialist subagent reviews, implementation fan-out, and verification internal to the single supervised session.
- **Strict Splitting Conditions**: Splitting into separate tasks is prohibited by default and permitted **only** when a workflow step explicitly insists on:
  1. _Different repository_: Strictly one task per repository.
  2. _Different time_: A distinct external wait or execution window.
  3. _Different agent/session_: A workflow-mandated external agent or session, including closed-loop user-channel delivery dependent on container tasks via `needs`.
- **Graph Topology & Edge Invariants**: Never pass `type: "epic"` to `pkb_create_task` (epics are organizational containers, not task types). Where splitting is explicitly required, wire execution gating via `needs: [<task_id>]`. Top-level deliverable tasks wire `serves` to priced targets or to existing epics that serve priced targets; subtasks never carry redundant `serves` edges (single injection invariant). Contextual references are plain markdown `[[wikilinks]]` under `## Pointers`. Write tasks with status `queued`.

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

- Composed from: [ One-line list of workflow templates and skills this task was composed from. ]
```

### Requirements for Writing Tasks

- Filter incoming mechanism prescriptions and translate them into observable outcome criteria. Line numbers, line ranges, and narrow code slice prescriptions are strictly forbidden in `Goal`, `Acceptance`, and `Instructions`. Give the worker the end state and the bounds; leave the method to it.
- Record the asker's own words once, in `## Ask`, with their ids, and never rewrite them: the task carries the ask as an immutable referent. Link asks to prior context, recompose into a clear logical structure, and cite message ids. Restate terse, fragmented words into clear, complete criteria, judged by fidelity to meaning and distinctions.
- State the Goal and each criterion over the whole class the request covers. When asked what broke a mechanism, compose the debugging workflow and preserve the full failure question in Acceptance across its lifecycle rather than narrowing to a single symptom.
- Every heading is a prompt to fill without restriction slots: say what has to be done, not what shouldn't.
- Keep each task strictly concise: 50–150 words for atomic tasks, up to 300 words for multi-stage composite workflows, `## Ask` aside. Include only what the worker cannot find for itself.
- Interpret workflow template stages into concise numbered imperative steps; never paste template narrative, rationale, or explanatory background.
- Assume the worker could run anywhere; never reference local paths, tools, or conventions. Leave out methods, command scripts, tool names, runtime hints, limits, summaries of linked notes, provenance, changelogs, session narratives, counts, SHAs, and history.
- Change an existing task only for a defect in its text; never rewrite its `## Ask` or renumber its criteria.
- A skill may be a step (`invoke /<skill-name>`). A workflow template is never a step; its steps are.
- Close every task with a one-line appendix section listing the workflow templates and skills it was composed from: `## Appendix: Sources` followed by `- Composed from: <workflows and skills>.`
- Do not create standalone decision tasks or file questions as tasks. Groundwork-first route decisions invariant applies. Competing candidate options stay inside the body of the scoping task or ADR until chosen. Model unknowns as empirical probes (`classification: probe`) wired via `needs: [<probe_task_id>]`.
- Worker state-only vs container supervision boundary: plain leaf workers (`/pull`) mutate only their claimed task's own state and never mint follow-up tasks; container coordinators (`/supervise`) enrich their claimed task via `/reify` and create follow-up tasks solely under the strict out-of-session splitting conditions above.
- Reify plans, roadmaps, and designs as tasks on the PKB task graph.

## 4. Report

Stop once tasks are written to the graph; `/dispatch` starts their workers. For each task written or confirmed ready, output:

- Title, ID, status, and open `needs` dependencies.
- Composed sources in the identical one-line format appended to the task body under `## Appendix: Sources` (e.g. `- Composed from: wf-feature, /craft`).
