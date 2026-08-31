---
id: enforcement-task-contract
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Work-Unit Contract (Layer 2)

## aops — Work-unit loop (the task contract)

Operative from PKB `claim_task` → `release_task`. That pair is the contract for
a single agent session's single unit of work: one claimed unit, released under
contract.

**The unified worker contract — this is its canonical home; other docs link
here.** Any fully-spec'd task — including one with children; an "epic" is just
a task with children, no special machinery — can be claimed by any worker on
any surface (polecat container, in-session subagent, agent team). Workers use
every harness feature they have, and with that comes the obligation to
demonstrate compliance and QA internally — how is the worker's business. The
return contract: **evidence + an output URL, written to the PKB task record.**
One deliverable per claimed task, never a spray of per-child PRs the principal
reviews individually. Task scope is one project/repo. Sync-wait versus
fire-and-forget is a dispatch-time cadence choice, not a contract difference.

**The task graph is the sole source of truth for completion.** `release_task` /
`complete_task` is the authoritative completion claim; a prose "done" that
never moves task state is cheap talk. Enforcement binds to the claim act, not
to the session, so it holds regardless of session class. Completion is not a
claim — it is a claim carrying verification: the release carries
independent-verification evidence bound to the artifact state of the work.

**A task body carries no history or meta-commentary.** It is a checklist of
work to be done, rewritten in place as items complete — per
[`synthesize-not-accrete`](../../lib/axioms/synthesize-not-accrete.md), which
this contract does not restate.

### Mechanisms

- **Premise judgment** happens before dispatch, in pauli's `brief` skill: it
  places and values the work, sorts its assumptions, names its open forks, then
  settles shape and acceptance criteria. Dispatch surfaces (`/pull`,
  `/dispatch`) trust that rather than re-judging the premise themselves.
- **Task-binding invariant** — no mutating work without a task bound to the
  session via `claim_task`, never an environment variable naming the task.
  One session claims exactly one task, possibly multiple subtasks of it. This
  is a design invariant the framework holds agents to by convention and
  review, not a code-level blocking check today.
- **Claim at launch** — a dispatch whose loss would matter beyond its own
  session has its claim written to the graph before the worker starts: who it
  went to, under which session and surface, and when. The worker's own
  `claim_task` still happens from inside its session and is what moves the
  status; the launch-time record exists so a worker that died before claiming
  is legible as an unanswered dispatch rather than as work nobody picked up.
  Cheap read-only probes are exempt — nothing is lost by running one again, so
  claiming for them buys graph noise instead of recoverability. A launch-time
  claim with no worker claim behind it is the stale-claim signal a reconcile
  sweep probes and, finding nothing, requeues to `ready`.
- **Evidence contract**, at `release_task` / `complete_task` — the completion
  claim carries independent-verification evidence bound to artifact state, or a
  stated failure reason. This is the primary enforcement point. Framed to
  agents as "land the plane": commit → push → `release_task` with either a
  completion claim or a `partial` handback, a legal terminal outcome per
  [spec-partial-work-tight-loop-delivery.md §4](../polecat/spec-partial-work-tight-loop-delivery.md).
  Only silent, undisclosed abandonment is garbage-collected — incentive-first,
  this machinery is the backstop, not the mechanism agents lean on. This is
  Layer 2's instantiation of the universal task-boundary contract; the
  field-by-field shape, the substance-over-form review requirement, and the
  grandfather cutover policy live once, canonically, in
  [evidence-contract.md](evidence-contract.md).
