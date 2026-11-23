---
name: reify
description: Bind a situated node or directive to its executor and composed workflow on a combined task body. Use inside container supervision (/supervise) or on planning requests to resolve templates across project, PKB, and universal tiers. Exclude for expanding objectives into sub-objectives (use /decompose) or starting workers on written tasks (use /dispatch).
---

# /reify -- Compose Dispatchable Workflow

Bind one situated node or directive to an executor class and current workflow templates inside `/supervise` or on an explicit planning request (`pauli` or lead executor). Given a parent container, reify only children ready to run. Write nothing to the graph until placement and composition pass; answer in-turn lookups without a task.

## 0. Verify Placement (`/q` Precondition)

A node must sit under an active parent container (`type: "task"`, never `type: "epic"`) wired per the Three-Purpose Taxonomy before workflow composition. Route unplaced asks or unparented task IDs through `/q` first (using custodian distilled conceptual searches).

## 1. Hydrate

Invoke `/hydrate` (via custodian when called by a non-custodian). Cite hydration findings before composing: update existing matching tasks instead of duplicating, continue unfinished matches, and wire `needs` for unfinished prerequisites.

## 2. Compose Workflows

- **Single-skill fast-path**: When a task's sole work is `invoke /<skill>`, skip template resolution and report ready.
- **Three-tier resolution** (`Project > PKB > Universal`; higher tiers shadow completely, never merge across tiers):
  - List PKB `type: "template"` IDs via `pkb_list_documents` (`limit >= 200`), then batch-read `pkb_get_document(..., detail: "summary")` to inspect `frontmatter.project`, `frontmatter.description`, and opening step summaries in one pass.
  1. _Project_: `frontmatter.project` matches the task's `project` (determine the shadowed slug by stripping an optional `<project>-` or `<project>_` prefix from `id` when present; otherwise use `id` directly; ignore foreign projects).
  2. _PKB_: `frontmatter.project` is absent or `null`.
  3. _Universal_: Core templates in `../workflow-library/workflows/*.md` enumerated and read via native file tools.
- **User direction & groundwork-first decisions**: User direction to perform, settle, or deliver work counts as approval across design, architecture, and delivery (`status: "queued"` for agent steps; `done` for already-shipped work once user-informed). Settle unknowns (PKB first, then repository host and traces) and select recommended routes directly without adding class-based holds; set `status: "review"` (`assignee: "user"`) with a recorded recommendation only when groundwork is complete and the work hits an invariant boundary (external audience, unruled merge, unbounded cost) or an explicitly user-reserved pre-action hold/choice.
- **Template interpretation**: Translate selected template stages into concise numbered imperative steps in `## Instructions` (never copy template prose). Invoke skills as `invoke /<skill-name>`; compose agent workflows rather than mechanical scripts for qualitative judgment. When composition has a gap, write nothing incomplete to the graph and ask the supervisor for clarification rather than declining the task.

## 3. Write Each Task

- **Combined body & two-task reviewed classes**: Default to one repo-scoped task body (50-150 words atomic, <=300 words composite, `## Ask` aside). Under `/supervise`, keep planning, in-session reviews, fan-out, and verification inside the single session. For task classes requiring independent graph-tracked review, mint two child tasks:
  1. **Work task**: Delivers artifact or opens draft PR (`gh pr create --draft`), records evidence, and releases `done`.
  2. **Review task** (`needs: [<work_task_id>]`): Runs independent review, marks `gh pr ready`, and releases `done` or `failed`.
     Unreviewed classes yield only the work task releasing `done`.
- **Splitting conditions**: Split beyond the work+review pair only when a workflow step explicitly requires (1) a different repository (one task per repo), (2) a different time/external wait, or (3) a workflow-mandated separate agent/session (such as independent review or closed-loop channel delivery via `needs`).
- **Topology**: Pass `type: "task"` (never `type: "epic"`), wire sequencing via `needs`, keep `serves -> target` exclusively on Strategic Value Carriers (zero leaf `serves` edges), cite pointers as PKB links (wikilinks) under `## Pointers`, and set `status: "queued"`.

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

Stop once tasks are written; `/dispatch` starts workers. Return each task's Title, ID, status, open `needs`, and composed workflows and skills as numbered premises in a compact prose Argdown block per `ida:premise-check` when replying to another agent (Markdown applies only to direct user replies).
