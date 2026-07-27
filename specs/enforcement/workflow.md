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

- **`decompose`-skill decomposition** (pauli's decomposition-time call),
  task-template conventions, and proof-of-compliance tool fields — the
  workflow is assembled compliant at task-creation time.
- **`cohesive-pr-epic`** — a coupled set of tasks shares one draft PR: the
  PR-surface instance of the general return contract — one claimed task, one
  deliverable, never a spray of per-child PRs — whose home is
  [task-contract.md](task-contract.md).
- **`/supervisor`** — the multi-tick delegate-and-verify loop that runs across a
  set of tasks.

## The five-step shape

A workflow is not a bespoke pipeline invented per task. It is one recursive
shape, applied at whatever granularity the `decompose` skill cuts to — a single
subtask, an epic, or a multi-epic release all run the same five steps. Within
this skeleton, pauli assembles the concrete workflow — the review lenses, the
required level of _independent_ review, the altitude — from composable rules
at decomposition time. A literature review, a paper critique, and a code
change are the same contract with different assembled workflows (different
lenses: citation verification, methodological soundness, container
validation) — the assembled workflow is the only differentiator; there is no
separate research path.

1. **Contract** — the unit's premise, worth, and acceptance criteria are
   settled _at decomposition time_, before compute is spent executing it.
   This is pauli's pre-hoc lens (premise/worth/shape). The `decompose` skill
   (see [`plugins/pkb/skills/decompose/SKILL.md`](../../plugins/pkb/skills/decompose/SKILL.md))
   always emits it as a standing, early-blocking task node in the epic's DAG
   — the rest of the epic's work depends on it clearing. The previously
   separate standalone premise-gate concept — a two-judge hard-refuse
   ceremony run at the spend surfaces (`/pull`, `/dispatch`) — is retired;
   dispatch surfaces trust pauli's decomposition without re-judging
   the premise themselves. The `decompose` skill plans only: it emits this
   task (and the boundary-check/QA-around tasks below) into the graph, it
   never dispatches or runs them itself.
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

### Review composition

Steps 3–5 are assembled by pauli from composable rules at decomposition time. Review composition (the lenses, the depth, and whether reviewers are independent from authors) is one design consideration among several, and is structural rather than an agent-facing instruction. Base workflows (living as PKB templates) set the default standard for these choices and evolve over time. Any surface satisfying the assembled workflow's requirements qualifies as an executor — an independent polecat session that spins the container and validates with the marsha lens for code changes, or dispatch-layer subagents running the rbg lens for textual/rules compliance. Proof is ALWAYS written to the PKB, typically as a review task plus receipt. GitHub/GHA is merely one _optional_ executor of code review — currently manual and deferred — never the review system itself.

### Recursion

A task decomposed into subtasks nests this shape: each subtask runs its own
contract → execution → boundary-check → QA-around cycle, and the parent
workflow's own step 4/5 read the aggregate of its children's outcomes rather
than re-deriving them. An epic is a workflow whose "execution" step (2) is
itself one or more nested workflows. There is no separate contract for
"epic-shaped" work — it is the same five steps at a coarser grain.

### Risk-scaled review depth — pauli's call

How much of steps 3–4 run as _standalone review subtasks_ versus how much
the executing agent self-assesses (per Layer 1's exit-reflection discipline)
and hands back for one consolidated review is not fixed by this spec — it is
pauli's call, made via the `decompose` skill at decomposition time (step 1),
based on the task's
risk and blast radius. Two ends of the same shape, not two different
contracts:

- **High-risk / wide blast radius** — per-chunk review subtasks, wired with
  `depends_on`, each running its own boundary-check and QA-around before the
  next chunk starts.
- **Low-risk / narrow blast radius** — workers self-assess against the
  exit-reflection checklist and hand back separate commits under one shared
  branch; a single consolidated boundary-check + QA-around pass runs once —
  a review pass whose receipt lands in the PKB. The final PR (the `cohesive-pr-epic`
  mechanism above) is the PR-surface instance of that pass, and the GHA PR
  pipeline is one optional executor of it.

The only invariant across the whole range: a complete set of
steps 3–5 runs per the assembled workflow before a workflow is marked done, regardless of how pauli
chose to distribute it. A unit may also legally terminate `partial` (see
[spec-partial-work-tight-loop-delivery.md §4](../polecat/spec-partial-work-tight-loop-delivery.md#4-the-partial-terminal-state)):
steps 3–5 then review the shipped chunk plus its declared-deferred
remainder, and draft → ready-for-the-principal still requires the
pauli-specified review.
