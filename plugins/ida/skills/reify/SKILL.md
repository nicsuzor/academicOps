---
name: reify
description: Bind a situated node or directive to its executor and composed workflow on a combined task body. Use inside container supervision (/supervise) or on planning requests to resolve templates across project, PKB, and universal tiers. Exclude for expanding objectives into sub-objectives (use /decompose) or starting workers on written tasks (use /dispatch).
---

# /reify -- Compose Dispatchable Workflow

Bind one situated node or directive to an executor class and current workflow templates inside `/supervise` or on an explicit planning request (`pauli` or lead executor). Given a parent container, reify only children ready to run. Write nothing to the graph until placement and composition pass; answer in-turn lookups without a task.

## 0. Verify Placement (`/q` Precondition)

A node must sit under an active parent container (`type: "task"`, never `type: "epic"`) wired per the Three-Purpose Taxonomy before workflow composition. Route unplaced asks or unparented task IDs through `/q` first (using custodian distilled conceptual searches).

## 1. Hydrate

Invoke `/hydrate` (via custodian when called by a non-custodian) using short (5-15 word) distilled conceptual queries per topic facet, never raw composite prompts. Cite hydration findings before composing: update existing matching tasks instead of duplicating, continue unfinished matches, and wire `needs` for unfinished prerequisites.

## 2. Compose Workflows

- **Single-skill fast-path**: When a task's sole work is `invoke /<skill>`, skip template resolution and report ready.
- **Three-tier resolution** (`Project > PKB > Universal`; higher tiers shadow completely, never merge across tiers):
  1. _Project_: PKB `type: "template"` with `project: "<project>"` (strip `<project>-` prefix to get the shadowing slug; ignore foreign projects).
  2. _PKB_: PKB `type: "template"` with `project: null`.
  3. _Universal_: Core templates in `../workflow-library/workflows/*.md` enumerated and read via native file tools.
- **Groundwork-first route decisions**: Settle unknowns (PKB first, then repository host and traces) and select recommended routes directly (`status: "queued"`). Close (`done`) already-shipped work once user-informed; set `status: "review"` (`assignee: "user"`) only when groundwork and a reasoned recommendation are recorded and the item genuinely waits on the user's decision or host action.
- **Template interpretation**: Translate selected template stages into concise numbered imperative steps in `## Instructions` (never copy template prose). Invoke skills as `invoke /<skill-name>`; compose agent workflows rather than mechanical scripts for qualitative judgment. Halt and report if composition fails.

## 3. Write Each Task

- **Combined body & two-task reviewed classes**: Default to one repo-scoped task body (50-150 words atomic, <=300 words composite, `## Ask` aside). Under `/supervise`, keep planning, in-session reviews, fan-out, and verification inside the single session. For task classes requiring independent graph-tracked review, mint two child tasks: (1) work task (delivers artifact or opens draft PR via `gh pr create --draft`, records evidence, releases `done`) and (2) review task (`needs: [<work_task_id>]`, runs review, marks `gh pr ready`, releases `done` or `failed`). Unreviewed classes yield only the work task releasing `done`.
- **Splitting conditions**: Split beyond the work+review pair only when a workflow step explicitly requires (1) a different repository (one task per repo), (2) a different time/external wait, or (3) a workflow-mandated separate agent/session (such as independent review or closed-loop channel delivery via `needs`).
- **Topology**: Pass `type: "task"` (never `type: "epic"`), wire sequencing via `needs`, keep `serves -> target` exclusively on Strategic Value Carriers (zero leaf `serves` edges), cite pointers as markdown wikilinks under `## Pointers`, and set `status: "queued"`.

Fill the canonical structure:

```markdown
## Ask

[ Verbatim authorising ask with message IDs. Immutable referent; never edit. ]

## Goal

[ End state naming target repo/system and objective, faithful to meaning. ]

## Context

[ Facts/decisions the worker cannot discover itself (omit if none). ]

## Acceptance

[ Numbered observable outcomes (AC1, AC2, ...) bounded to executor deliverables, zero line numbers or narrow code slices. ]

## Instructions

[ Numbered imperative steps from composed templates ending with delivery, evidence recording, and release. ]

## Output

[ Destination repository and target branch or artifact path. ]

## Report

[ Handback contract; default /dump with evidence per acceptance criterion. ]

## Appendix: Sources

- Composed from: [ One-line list of workflow templates and skills. ]
```

### Task Writing Invariants

- **Worker-satisfiable outcomes**: Exclude line numbers, narrow code slices, and external post-exit acts (independent review, CI, merge, host deployment, user installation/deployment) unless that stage is the unit's authorized scope.
- **Ask & generality**: Keep `## Ask` verbatim with IDs; restate terse asks faithfully; express Goal and criteria over the full class of the ask. Omit local paths, scripts, tool names, counts, SHAs, and historical provenance.
- **Decisions & state-only boundary**: Keep competing options in the scoping task or ADR; model empirical unknowns as `classification: probe` tasks wired via `needs`. Leaf workers (`/pull`) mutate only claimed task state; coordinators (`/supervise`) enrich via `/reify` and mint follow-ups only under strict splitting rules.

## 4. Report

Stop once tasks are written; `/dispatch` starts workers. Output each task's Title, ID, status, open `needs`, and `- Composed from: <workflows and skills>.` line.
