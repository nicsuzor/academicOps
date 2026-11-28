---
name: reify
description: Bind a situated node or directive to its executor and composed workflow on a combined task body. Use just before dispatching a task to a worker container, in-session during /pull, or on planning requests to resolve templates across project, PKB, and universal tiers. Exclude for expanding objectives into sub-objectives (use /decompose) or starting workers on written tasks (use /dispatch).
---

# /reify -- Compose Dispatchable Workflow

Bind one situated node or directive to an executor class and current workflow templates just before `/dispatch` sends it to a worker container (`pauli`, on a dispatching surface), inside `/pull` (lead executor), or on an explicit planning request (`pauli`). Given a parent container, reify only children ready to run. Write nothing to the graph until placement and composition pass; answer in-turn lookups without a task.

## 0. Verify Placement (`/q` Precondition)

A node must sit under an active parent container (`type: "task"`, never `type: "epic"`) wired per the Three-Purpose Taxonomy before workflow composition. Route unplaced asks or unparented task IDs through `/q` first (using custodian distilled conceptual searches).

## 1. Hydrate

Invoke `/hydrate` (via custodian when called by a non-custodian). Cite hydration findings before composing: update existing matching tasks instead of duplicating, continue unfinished matches, and wire `needs` for unfinished prerequisites.

## 2. Compose Workflows

- **Compose the least that serves the ask**: Fast, small tasks are the default. Select only the templates the task's class needs (usually the task base plus at most one narrower base) and write only the steps the ask and those templates require. Never add a step, stage, check, test, review, approval, sign-off, summary or delivery the ask or a selected template does not name, and never "for safety". Handed-back work is always reviewed in a separate process, so a work task carries no review or verification stage of its own. No step delivers anything to the user.
- **Single-skill fast-path**: When a task's sole work is `invoke /<skill>`, skip template resolution and report ready.
- **Three-tier resolution** (`Project > PKB > Universal`; higher tiers shadow completely, never merge across tiers):
  1. _Project_: PKB `type: "template"` with `project: "<project>"` (strip `<project>-` prefix to get the shadowing slug; ignore foreign projects).
  2. _PKB_: PKB `type: "template"` with `project: null`.
  3. _Universal_: Core templates in `../workflow-library/workflows/*.md` enumerated and read via native file tools.
     A slug also resolves through a template's `alias` list. Each description opens with who runs it: `Worker:` templates suit a worker container; `Crew:` templates need privileged access and never go to one; `Review:` templates belong to the separate review of handed-back work; `Planning:` templates shape decomposition, not a single task.
- **User direction & groundwork-first decisions**: User direction to perform, settle, or deliver work counts as approval across design, architecture, and delivery (`status: "queued"` for agent steps; `done` for already-shipped work once user-informed). Settle unknowns (PKB first, then repository host and traces) and select recommended routes directly without adding class-based holds; set `status: "review"` (`assignee: "user"`) with a recorded recommendation only when groundwork is complete and the work hits an invariant boundary (external audience, unruled merge, unbounded cost) or an explicitly user-reserved pre-action hold/choice.
- **Template interpretation**: Translate selected template stages into concise numbered imperative steps in `## Instructions` (never copy template prose). Invoke skills as `invoke /<skill-name>`; compose agent workflows rather than mechanical scripts for qualitative judgment. When composition has a gap, write nothing incomplete to the graph and ask the supervisor for clarification rather than declining the task.
- **Worker-container executor**: A dispatched worker container has no plugins, no PKB access, and usually no right to push or publish; the full task arrives as its prompt. Compose only `Worker:` templates. Write every step out in full with zero `invoke /<skill>` steps, zero PKB lookups, zero claim, status, or release steps, and zero privileged steps (push, opening or merging a PR, publishing, deploying, sending). Its `## Output` is the answer in its final message, commits on its working branch, or a file at a shared location the task names, never only its own container. Put every fact the work depends on in `## Context`, and set `## Report` to the worker's final output message, which the polecat service writes to the task as the container is reaped. Keep the instructions short: the worker is capable, and its work is checked on hand-back.

## 3. Write Each Task

- **One task, one body**: Write one repo-scoped task (50-150 words atomic, <=300 words composite, `## Ask` aside). Never mint a review task alongside it; review of handed-back work is a separate process.
- **Splitting conditions**: Split only when the work needs (1) a different repository (one task per repo) or (2) a wait on something outside the session.
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

[ The fewest numbered imperative steps the composed templates require, ending with where the output goes. ]

## Output

[ The final report, the working branch, or a named shared location. ]

## Report

[ Handback contract; default /dump with evidence per acceptance criterion (worker container: final output message with that evidence). ]

## Appendix: Sources

- Composed from: [ One-line list of workflow templates and skills. ]
```

### Task Writing Invariants

- **Worker-satisfiable outcomes**: Exclude line numbers, narrow code slices, and acts after hand-back (review, CI, merge, deployment, delivery to the user, user installation) unless that act is itself the task's ask. Add no test requirement unless the repository keeps a test suite and the change is to code that executes.
- **Ask & generality**: Keep `## Ask` verbatim with IDs; restate terse asks faithfully; express Goal and criteria over the full class of the ask. Omit local paths, scripts, tool names, counts, SHAs, and historical provenance.
- **Decisions & splitting boundary**: Keep competing options in the scoping task or ADR; model empirical unknowns as `classification: probe` tasks wired via `needs`. Mint follow-ups only under the splitting conditions above.

## 4. Report

Stop once tasks are written; `/dispatch` starts workers. Return each task's Title, ID, status, open `needs`, and composed workflows and skills as numbered premises in a compact prose Argdown block per `ida:premise-check` when replying to another agent (Markdown applies only to direct user replies).
