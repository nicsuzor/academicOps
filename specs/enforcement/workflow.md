---
id: enforcement-workflow
title: Enforcement — The Workflow (Layer 3)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, workflow]
---

# Enforcement — The Workflow (Layer 3)

## aops — Workflow

A set of PKB tasks and subtasks that make up a more user-reviewable,
user-directed unit of work.

This is the first layer where the framework cares about _how_ the work is
done, not only the outcome — in contrast to the execution span inside a single
task, where the posture is trust-the-method.

### Mechanisms

- **`brief`-skill sizing and composition** (pauli's dispatch-time call),
  task-template conventions, and proof-of-compliance tool fields — the
  workflow is assembled compliant before the unit is dispatched.
- **The supervisor** ([sara.md](../agents/sara.md)) — the multi-tick
  delegate-and-verify loop that runs across a set of tasks.

## The five-step shape

A workflow is not a bespoke pipeline invented per task. It is one recursive
shape, applied at whatever granularity the `brief` skill cuts to — a single
unit, an epic, or a multi-epic release all run the same five steps. Within
this skeleton, pauli assembles the concrete workflow — the review lenses, the
required depth of independent review, the altitude — from composable rules at
brief time. A literature review, a paper critique, and a code change are the
same contract with different assembled workflows (different lenses: citation
verification, methodological soundness, container validation) — the assembled
workflow is the only differentiator; there is no separate research path.

1. **Contract** — the unit's premise, worth, and acceptance criteria are
   settled before compute is spent executing it, in pauli's one pre-hoc pass:
   `brief` establishes premise and worth on the graph (assumptions sorted, open
   forks named, the decision list the user reads), then settles shape and
   acceptance criteria. The user invoking `brief` is the promotion gate.
   `brief` emits the contract as a standing, early-blocking node
   in the epic's DAG, so the rest of the epic's work depends on it clearing. The
   previously separate standalone premise-gate concept — a two-judge
   hard-refuse ceremony run at the spend surfaces (`/pull`) — is
   retired; dispatch surfaces trust those passes without re-judging the premise
   themselves. `brief` plans only: it emits this task (and the
   boundary-check/QA-around tasks below) into the graph, it never dispatches or
   runs them itself.
2. **Execution** — the claimed agent does the work. This span is
   trust-the-method: no process-level enforcement, evidence-driven escalation
   only if something goes wrong.
3. **Boundary check** — rbg's lens: did the executing agent follow the rules?
   Reviews the task's contract and handback only — inputs and outputs, never
   the transcript. This is [task-contract.md](task-contract.md)'s
   `release_task` evidence gate (Layer 2) read against the acceptance criteria
   set in step 1.
4. **QA-around** — marsha's lens: does the delivered artifact actually do what
   step 1's contract asked, and does it do it well? Bar is excellent, not
   passing. Distinct from step 3: boundary check asks whether the rules were
   followed, QA-around asks whether the work is good.
5. **Principal sign-off** — [sign-off.md](sign-off.md) (Layer 4). Final review
   over the workflow as a whole unit, independent of whatever review happened
   inside it at steps 3–4.

Steps 3, 4, and 5 all read and produce claims in the same shape: see
[evidence-contract.md](evidence-contract.md), the canonical universal
task-boundary contract — every load-bearing claim at each step carries
checkable evidence or a stated failure reason, and the reviewer checks the
actual criterion was met, not merely that the right fields were filled in (see
[Substance over form](evidence-contract.md#substance-over-form)).

### Two signatures at the sign-off boundary

`done` carries two signatures, in this order. Neither substitutes for the
other.

1. **Certification — the dispatcher's, at unit completion.** It commissions the
   review machinery (the review obligations `brief` records on the task,
   executed through the review skills), reads the verdict, and writes that
   verdict onto the task record. What it certifies is mechanics, quality, and
   compliance with the brief. The dispatcher never supplies that judgment
   itself and never relays a worker's own claim of success in its place.
2. **Acceptance — the face's, against the user's intent.** The brief carries
   the ask; only the interactive face holds the ambition behind it. Work can be
   correctly built, cleanly reviewed, and still not be what was wanted — that
   is the failure this second signature exists to catch, and it is why
   acceptance is judged against intent rather than against the brief.

Certification without acceptance ships work nobody weighed against intent.
Acceptance without certification asks the face to vouch for mechanics it never
checked and cannot see.

### Review composition

Steps 3–5 are assembled by pauli from composable rules at brief time. Review
composition — the lenses, the depth, whether reviewers are independent from
authors — is structural rather than an agent-facing instruction. Base
workflows, living as PKB templates, set the default standard for these choices
and evolve over time. Any surface satisfying the assembled workflow's
requirements qualifies as an executor: an independent polecat session that
spins the container and validates with the marsha lens for code changes, or
dispatch-layer subagents running the rbg lens for textual/rules compliance.
Proof is always written to the PKB, typically as a review task plus receipt.
GitHub/GHA is one optional executor of code review, never the review system
itself.

### Recursion

A task decomposed into subtasks nests this shape: each subtask runs its own
contract → execution → boundary-check → QA-around cycle, and the parent
workflow's own step 4/5 read the aggregate of its children's outcomes rather
than re-deriving them. An epic is a workflow whose execution step (2) is
itself one or more nested workflows — the same five steps at a coarser grain,
with no separate contract for "epic-shaped" work.

### Risk-scaled review depth — pauli's call

How much of steps 3–4 run as standalone review subtasks versus how much the
executing agent self-assesses and hands back for one consolidated review is
pauli's call, made via the `brief` skill at dispatch time (step 1), based on
the task's risk and blast radius. Two ends of the same shape, not two
different contracts:

- **High-risk / wide blast radius** — per-chunk review subtasks, wired with
  `depends_on`, each running its own boundary-check and QA-around before the
  next chunk starts.
- **Low-risk / narrow blast radius** — workers self-assess against the
  exit-reflection checklist and hand back separate commits under one shared
  branch; a single consolidated boundary-check + QA-around pass runs once —
  a review pass whose receipt lands in the PKB. One final PR over the coupled
  set — never a spray of per-child PRs, per the return contract in
  [task-contract.md](task-contract.md) — is the PR-surface instance of that
  pass, and the GHA PR pipeline is one optional executor of it.

The invariant across the whole range: a complete set of steps 3–5 runs per the
assembled workflow before a workflow is marked done, regardless of how pauli
chose to distribute it. A unit may also legally terminate `partial` (see
[spec-partial-work-tight-loop-delivery.md](../polecat/spec-partial-work-tight-loop-delivery.md#the-partial-terminal-state)):
steps 3–5 then review the shipped chunk plus its declared-deferred
remainder, and draft → ready-for-the-principal still requires the
pauli-specified review.
