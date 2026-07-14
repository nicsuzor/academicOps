---
id: enforcement-workflow
title: Enforcement — The Workflow (Layer 3)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, workflow]
---

# Enforcement — The Workflow (Layer 3)

> **Numbering note.** `Layer 3` here belongs to the **module-boundary layer model** (`Layer 0`–`Layer 4`: the trust-the-method intra-task/turn span, [task-contract.md](task-contract.md), this file, [sign-off.md](sign-off.md)) — a different axis from any pipeline/pyramid numbering that may appear elsewhere.

## aops — Workflow

A set of PKB tasks and subtasks that make up a more user-reviewable,
user-directed unit of work.

This is the first layer where the framework cares about _how_ the work is done,
not only the outcome — in contrast to Layer 0, where the posture is
trust-the-method.

### Mechanisms

- **`/planner` decomposition**, task-template conventions, and proof-of-compliance
  tool fields — the workflow is composed compliant at task-creation time.
- **`cohesive-pr-epic`** — a coupled set of tasks shares one draft PR; a
  workflow-level invariant that constrains the shape of the whole set, not one
  task.
- **`/supervisor`** — the multi-tick delegate-and-verify loop that runs across a
  set of tasks.

## The five-step shape

A workflow is not a bespoke pipeline invented per task. It is one recursive
shape, applied at whatever granularity `/planner` decomposes to — a single
subtask, an epic, or a multi-epic release all run the same five steps:

1. **Contract** — the unit's premise, worth, and acceptance criteria are
   settled _at decomposition time_, before compute is spent executing it.
   This is pauli's pre-hoc lens (premise/worth/shape). The `decompose` skill
   (see [`aops/skills/decompose/SKILL.md`](../../aops/skills/decompose/SKILL.md))
   always emits it as a standing, early-blocking task node in the epic's DAG
   — the rest of the epic's work depends on it clearing. The previously
   separate standalone premise-gate concept — a two-judge hard-refuse
   ceremony run at the spend surfaces (`/pull`, `/dispatch`) — is retired;
   dispatch surfaces trust the planner's decomposition without re-judging
   the premise themselves. `/planner` plans only: it emits this task (and
   the boundary-check/QA-around tasks below) into the graph, it never
   dispatches or runs them itself.
2. **Execution** — the claimed agent does the work. This span is
   trust-the-method: no process-level enforcement, evidence-driven
   escalation only if something goes wrong.
3. **Boundary check** — rbg's lens: did the executing agent follow the
   rules? Reviews the task's contract and handback only — inputs and
   outputs — never the transcript. This is [task-contract.md](task-contract.md)'s
   `release_task` evidence gate (Layer 2) read against the acceptance
   criteria set in step 1.
4. **QA-around** — marsha's lens: does the delivered artifact actually do
   what step 1's contract asked, and does it do it _well_? Bar is
   excellent, not passing. Distinct from step 3: boundary check asks "were
   the rules followed," QA-around asks "is the work good."
5. **Principal sign-off** — [sign-off.md](sign-off.md) (Layer 4). Final
   review over the workflow as a whole unit, independent of whatever review
   happened inside it at steps 3–4.

Steps 3, 4, and 5 all read and produce claims in the same shape: see
[evidence-contract.md](evidence-contract.md), the canonical universal
task-boundary contract — every load-bearing claim at each of these steps
carries checkable evidence or a stated failure reason, and the reviewer
checks the actual criterion was met, not merely that the right fields were
filled in (see [Substance over form](evidence-contract.md#substance-over-form)).

### Recursion

A workflow composed of subtasks nests this shape: each subtask runs its own
contract → execution → boundary-check → QA-around cycle, and the parent
workflow's own step 4/5 read the aggregate of its children's outcomes rather
than re-deriving them. An epic is a workflow whose "execution" step (2) is
itself one or more nested workflows. There is no separate contract for
"epic-shaped" work — it is the same five steps at a coarser grain.

### Risk-scaled review depth — the planner's call

How much of steps 3–4 run as _standalone review subtasks_ versus how much
the executing agent self-assesses (per Layer 1's exit-reflection discipline)
and hands back for one consolidated review is not fixed by this spec — it is
chosen by `/planner` at decomposition time (step 1), based on the task's
risk and blast radius. Two ends of the same shape, not two different
contracts:

- **High-risk / wide blast radius** — per-chunk review subtasks, wired with
  `depends_on`, each running its own boundary-check and QA-around before the
  next chunk starts.
- **Low-risk / narrow blast radius** — workers self-assess against the
  exit-reflection checklist and hand back separate commits under one shared
  branch; a single boundary-check + QA-around pass runs once, at the final
  PR (the `cohesive-pr-epic` mechanism above, and the GHA PR pipeline that
  instantiates sign-off in git).

The only invariant across the whole range: a complete, independent set of
steps 3–5 runs before a workflow is marked done, regardless of how the
planner chose to distribute it.
