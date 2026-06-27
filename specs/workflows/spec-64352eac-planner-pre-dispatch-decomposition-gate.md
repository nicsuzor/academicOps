---
id: spec-64352eac
title: "Planner pre-dispatch decomposition gate"
type: spec
created: 2026-05-04T23:29:35.832461270+00:00
modified: 2026-05-04T23:29:35.832461270+00:00
alias:
  - "spec-64352eac-planner-pre-dispatch-decomposition-gate"
  - "spec-64352eac"
permalink: spec-64352eac
status: ready
tags:
  - spec
  - planner
  - decomposition
  - pre-dispatch
  - review-lens
  - framework
---

# Planner Pre-Dispatch Decomposition Gate

## Status

Spec — ready for implementation. Composes with [[mcp-decomposition-tools]], [[strategic-triage]], [[research-decomposition]], and [[supervisor]]. Sibling concern with `task-4cea5008` / `aops-e2d639e2` (repo-routing pre-flight in supervisor) — same pipeline, different responsibility.

## Motivation

Two converging signals:

1. **/insights review (2026-05-05)** — over-engineering and routing miscues land in dispatch. Stop-hook enforcement is the wrong layer; planner-side discipline is where vague tasks, missing acceptance criteria, and wrong-project assignments should be caught.
2. **Polecat #3 incident** (`task-4cea5008` body) — 137 wasted tool calls because a task entered dispatch with a vague AC and a `project` field that didn't match where the work lived. Supervisor inherited the failure; planner created it.

The framework already has the primitive (`decompose_task`) and the lens pattern (review tasks in the graph per [[vision]] §"composable review"). What's missing is **a structured, repeatable decomposition pass that is required before a task crosses from `inbox` to `ready`** and produces first-class artifacts (acceptance criteria, verification process, lens annotations) that downstream actors can rely on.

This spec does not propose new infrastructure. `decompose_task` + review-lens task creation already cover the mechanics. The spec defines **the discipline** — what the planner must produce, and what it means for a parent to be "ready".

## Design Decision: Gate Sits at `inbox → ready`

Per [[TAXONOMY]] §Status Values:

- `inbox` — captured but not yet triaged; unknown priority, unknown readiness
- `ready` — **decomposed to leaf tasks with all hard dependencies resolved**
- `queued` — user has manually marked this available for agent dispatch (human gate)

The taxonomy already locates the work: **`ready` is not just "I want to do this", it is "this has been decomposed and unblocked"**. That is a substantive claim, and today the framework lets agents assert it without producing any artifacts that justify the claim.

`ready → queued` is **already a human gate** — the user decides what enters the dispatch pool. Adding planner discipline at that transition would either (a) duplicate the human's review, or (b) bypass it. Neither is right.

So: **the decomposition gate sits at `inbox → ready`**. The `ready → queued` transition stays as the user's prerogative; the planner's job is to make sure that when a task enters the pool of things the user _could_ queue, the user has the artifacts they need to make that decision quickly and well.

**`inbox → ready` is a _computed_ graduation, not a manual planner write.** `ready` is set automatically once decomposition is complete and all hard dependencies are resolved (canonical: [[TAXONOMY]] §"Status Values and Transitions", and `TAXONOMY.md` "`ready` is set automatically…"). The gate below defines _what the planner must produce_ for that graduation to be earned — it does not authorise the planner to hand-write the `ready` band. The criteria are unchanged; only the act of stamping the status is the system's, not the agent's. `ready → queued` remains the user's manual gate.

Rationale summary:

- `inbox → ready` is already where the taxonomy says decomposition has happened. The gate makes the implicit promise auditable.
- `ready → queued` is the human-control gate; the planner should not pre-empt it.
- Repo-routing pre-flight (`aops-e2d639e2`) is a _supervisor_ concern at `queued → in_progress`, not a planner concern. They are sibling gates at adjacent transitions, not duplicates.

### Lifecycle map

```
inbox  ──[ planner decomposition gate ]──▶  ready
ready  ──[ user judgement ]─────────────▶  queued
queued ──[ supervisor pre-flight ]──────▶  in_progress
                                              │
                                              ▼
                                         merge_ready / review / done
```

Each gate has a single responsibility:

| Gate                   | Owner      | Question answered                                              |
| ---------------------- | ---------- | -------------------------------------------------------------- |
| `inbox → ready`        | planner    | Is this well-enough specified that _someone_ could pick it up? |
| `ready → queued`       | user       | Do I want this worked on next?                                 |
| `queued → in_progress` | supervisor | Does the work actually live where the task says?               |

## Required Outputs of the Decomposition Pass

For a node to graduate from `inbox` to `ready`, the planner must produce all of the following. None are optional. Until every one is present the node stays in `inbox`; once they are all in place, `ready` is **computed automatically** — the planner does not hand-write the band (see the computed-graduation note above).

### 1. Subtask breakdown (or explicit "leaf" assertion)

Either:

- The node has children that together cover the parent's scope, each with `uncertainty < 0.3` (per [[TAXONOMY]] task-range) and clear AC; **or**
- The node is asserted to be a leaf (single-session, no decomposition needed). Leaf assertion must be in the parent body, not implicit.

Decomposition uses `decompose_task` per [[mcp-decomposition-tools]]. No new tooling.

### 2. Project / source-location field, verified

`project: <name>` on the parent and on every subtask. The planner must:

- Confirm the project value matches a known project in `.agents/CORE.md` Component Topology (planner SKILL.md §capture step 0 already enforces this for new captures — extend it to apply on the decomposition gate).
- Where the work touches files, name at least one file or symbol the work will modify. This becomes the supervisor's repo-routing grep target downstream (`aops-e2d639e2`).

This is **not** a duplicate of the supervisor pre-flight. The planner _names_ the file/symbol; the supervisor _greps_ for it. Same fact, two checks at different points.

### 3. Acceptance criteria — first-class, on the node body

Acceptance criteria are not a bullet list buried in prose. They are a `## Acceptance Criteria` H2 block with each criterion as a discrete, falsifiable statement. The planner refuses to mark `ready` if criteria are vague ("works correctly", "handles edge cases") or absent.

This is normative, not a tool-enforced rule — the planner skill checks; if the criteria don't pass, the planner halts and asks. (Per [[mcp-decomposition-tools]] §Architectural Principle: judgment in agent, deterministic checks in code. Whether a criterion is "falsifiable" is a judgment call.)

### 4. Verification task — separate node, linked

Every parent that crosses the gate must have a **verification subtask** as a child node, not as a body section. The verification task carries:

- `## Acceptance Standards` — the falsifiable criteria from the parent, restated as pass/fail checks
- `## Qualitative Verification Process` — prose describing _how_ a reviewer (human or agent) would actually verify each criterion: what to read, what to run, what to look at, what an acceptable answer looks like

Linkage:

- `parent: <parent-id>` — verification is a child of the work it verifies
- `depends_on: [<all-execution-children>]` — verification cannot run until the work is done
- Tag: `lens: verification`

This makes the verification process **addressable, schedulable, and auditable** in the graph. It is not a checklist that gets diffed-out later. (Per CORE.md "Externalise follow-up action items as separate linked tasks".)

### 5. Review-lens annotations — RBG (axioms) + Pauli (alignment)

This is where lens-based review composes with the planner pass. **Lenses are signals, not gates** ([[vision]] §"composable review", "merge gate not permission gate" axiom).

For every parent crossing `inbox → ready`, the planner creates two review-lens subtasks:

- `lens: rbg-axiom-check` — RBG reviews the decomposition against AXIOMS.md. Looks for axiom violations in the task plan itself (e.g., a task that proposes manual workarounds where dogfooding requires fixing the tool; a task that bypasses the merge gate; etc.).
- `lens: pauli-alignment-check` — Pauli reviews the decomposition for alignment with the parent's stated purpose, vision-fit, and strategic coherence (questions the question, identifies misframing, flags rabbit holes).

Each lens task is a **child of the parent being reviewed**, with `depends_on: []` (lenses don't block the parent — they annotate it) and tag `lens: <name>`. Status starts at `inbox`, transitions to `done` when the lens completes its review, with the verdict written to the lens task body.

The planner waits for both lens tasks to reach `done` before treating the parent as ready-eligible (the lens tasks are themselves part of "decomposition complete", so until they resolve `ready` is not yet computed). The lens verdicts are inputs to the planner's readiness decision — they don't auto-block. If RBG flags an axiom violation, the planner reads the verdict, decides whether to revise the decomposition, the AC, the AC verification, or to overrule (with rationale recorded). Same for Pauli.

**This is the concrete answer to "feedback from rbg/pauli before ready"**: lens tasks are created, executed, and resolved; their verdicts inform the planner's decision; the planner records the decision; once the required outputs are complete the parent graduates to `ready` automatically (the planner does not hand-write the band).

The user can override at any point — the planner reports lens findings to the user as part of the promotion proposal, and the user can say "ship it anyway" if they disagree with a lens.

## Composition With the Supervisor Pre-Flight Gate

These two gates are **siblings, not duplicates**:

| Concern             | Planner gate (this spec)                                                  | Supervisor gate (`aops-e2d639e2`)                              |
| ------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------- |
| When                | `inbox → ready`                                                           | `queued → in_progress`                                         |
| Who                 | planner skill                                                             | supervisor skill                                               |
| Question            | "Is this well-specified?"                                                 | "Does the stated work actually live where the task claims?"    |
| Output              | AC, verification task, lens annotations                                   | grep-confirmation that named file/symbol exists in stated repo |
| Failure mode caught | Vague AC, missing decomposition, axiom violation in plan, alignment drift | Wrong-repo dispatch, pkb→public privacy leak                   |

The planner _names_ the file/symbol the supervisor will later grep for. That is the only handoff between the two gates.

## What This Does NOT Add

- **No new statuses.** The taxonomy is unchanged.
- **No new MCP tools.** `decompose_task` + `create_task` (for lens children) cover everything.
- **No new agent.** Lens reviews use existing rbg and pauli agents, invoked as task assignees.
- **No hooks.** Per [[vision]] "review lenses are tasks in the graph, not hooks".
- **No auto-block.** Lens verdicts inform the planner; the planner-with-user decides.
- **No infrastructure.** This is a discipline spec — instructions for the planner skill, plus the verification-task and lens-task patterns.

## Implementation Surface

- **Planner SKILL.md** — add a `decompose` mode subsection: "Promotion gate: inbox → ready". Codify the five required outputs above.
- **Planner workflow `decompose.md`** — extend with steps 13–16: create verification task, create rbg-lens task, create pauli-lens task, wait for lens completion, record promotion decision.
- **Lens task templates** — short markdown templates for the RBG and Pauli lens tasks (what they review, what verdict format looks like, where to write findings). Lives in `planner/references/lens-templates/`.
- **Verification task template** — likewise, in `planner/references/verification-template.md`.

No code. No MCP changes. No taxonomy changes.

## Relationship to the RBG Stop-Hook Epic (`epic-9fa15948`)

`epic-9fa15948` proposes a Stop-hook RBG advisory pass — checking responses for "inference presented as fact" before they reach the user. **It is complementary, not redundant.** Different scope:

- This spec: planner-side, pre-dispatch, axiom-check on the _task plan_ (does the decomposition violate axioms?)
- `epic-9fa15948`: response-time, post-execution, hedging-check on the _response_ (is the agent presenting inference as fact?)

Both can land. They cover different failure modes and different points in the pipeline. Neither makes the other redundant.

## Relationship to `task-4cea5008` / `aops-e2d639e2`

Already covered above (sibling concerns). This spec **does not subsume them**. The supervisor pre-flight catches "task says it lives in repo X but the work isn't there" — that's a different question from "is the task well-decomposed". A task can be well-decomposed _and_ have a wrong project field; only the supervisor grep catches the latter.

## Acceptance Criteria for This Spec

- [ ] Planner SKILL.md decompose mode names the five required outputs; a node does not graduate to `ready` (computed) without them, and the planner does not hand-write the band.
- [ ] Verification task template exists and is linked from the planner workflow.
- [ ] RBG-lens and Pauli-lens task templates exist; planner creates these on every gate crossing.
- [ ] Lens verdicts are recorded as task body content; planner reads them before promoting.
- [ ] Dogfood: re-run a recent inbox→ready promotion under this gate; verify the gate caught at least one issue (vague AC, axiom drift, or alignment miss) that the previous discipline missed. If it catches nothing, the gate is theatre — pull back.
- [ ] No new MCP tools, statuses, or hooks introduced.

## Open Questions

- **Latency**: lens reviews take time. Is the `inbox → ready` transition allowed to span multiple sessions (planner pauses, lens tasks queue up, planner resumes when lenses complete)? Default: yes — `inbox` is fine to dwell in. Document this.
- **Lens conflict**: what happens when RBG and Pauli disagree (e.g., RBG says decomposition is over-specified, Pauli says it's under-specified)? Default: planner reports both verdicts to user; user decides. Don't build conflict-resolution logic.
- **Cheap-path bypass**: should trivial inbox tasks (one-line bug fixes, single-line doc edits) require the full gate? Provisional answer: yes — the cost of running two lens reviews on a one-line fix is small, and skipping creates a "trivial" loophole. Revisit if dogfood shows the cost is real.

## References

- [[TAXONOMY]] §Status Values, §Compression Model
- [[vision]] §"composable review" + §"merge gate not permission gate"
- [[mcp-decomposition-tools]] — primitives this spec uses
- [[research-decomposition]] — domain extension that will inherit from this gate
- [[supervisor]] — sibling pre-flight gate
- `task-4cea5008`, `aops-e2d639e2` — supervisor-side concerns
- `epic-9fa15948` — Stop-hook RBG validation (complementary)
- /insights review 2026-05-05 (aops-state log)
