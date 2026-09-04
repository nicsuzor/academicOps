---
id: supervisor-spec
title: Supervisor Architecture
type: spec
description: What the supervisor is, when it's invoked, and its contract
status: ready
tier: dispatch
depends_on: [dispatch-system]
tags: [spec, dispatch, architecture, supervisor]
---

# Supervisor Architecture

The supervisor is the framework's delegate-and-verify process: a stateless tick that
selects or creates work, dispatches it to workers, evaluates the results, and persists
state for the next tick. It operates at every scale -- a single epic, a multi-epic
release, or conversational orchestration of background workers -- using the same
discipline at each.

## User Story

As a researcher delegating work to agents, I want a single supervision process I
invoke -- never hand-rolled -- that takes an epic off my hands, dispatches its work,
and guarantees every delegated piece of work leaves a trace I can inspect -- a task
record, the worker's commits, and a recorded verdict -- so that work is proven
before it is trusted and nothing is ever fire-and-forgotten.

## One surface

Every dispatched task goes into an `sbx` sandbox with its own git clone
([[specs/dispatch/dispatch-system.md]]). There is no surface decision to make and
no branch in the logic: one task, one sandbox, one clone. Eligibility and
deliverable shape are the same whatever the work is -- the deliverable is whatever
output URL the assembled workflow specifies, over one unified worker contract
([[specs/enforcement/task-contract.md]]). A literature review and a code change
are the same contract with different assembled workflows.

Review steps carry a pauli-specified lens set fixed at decomposition and run per
the assembled workflow (see [[specs/enforcement/workflow.md]]). A task that is
not dispatchable -- missing inputs, or blocked on something outside the epic --
gets a block note and is deferred, not dispatched.

## Observability Guarantee

Every delegation MUST leave an inspectable trace; nothing is fire-and-forgotten.
Three artifacts, all of which outlive the sandbox that produced them:

- **Task record**: every dispatch is recorded on a PKB task (status, assignee,
  dispatch note, and on completion the evidence + output URL -- the PR URL where
  the surface is code).
- **The worker's commits**: fetched from the sandbox's own git remote,
  `sandbox-<name>`, and landing on the host under `refs/sandboxes/<name>/`. This
  is the durable record of what the worker actually did, and it must be fetched
  before the sandbox is removed -- `sbx rm -f` destroys the clone and the daemon
  serving it.
- **Verdict**: the supervisor's evaluation outcome is recorded on the task or epic
  ledger, so any later reader can see what was accepted and why.

The client's own transcript is written inside the container and is reachable
while the sandbox is alive (`sbx exec <name>`). It dies with the sandbox, so
nothing load-bearing is left there: what has to survive is committed or written to
the task.

## When It's Invoked

Supervision covers:

- Epic-level orchestration (one PKB epic -- an epic is just a task with children --
  state in the epic body)
- Portfolio/release supervision (many epics, state in the release task body)
- Conversational orchestration of background workers (e.g. "don't get involved
  yourself, make sure it gets done")

The supervisor is driven tick-by-tick by `/loop`, and cross-tick state lives
entirely in the task body, so any instance can resume from where a prior one left
off.

That is not a licence to stop after one wave. A healthy tick dispatches a wave,
collects it, merges what came back, and dispatches the next -- round after round,
until the epic is drained or what remains is blocked on something outside it --
and only then persists and exits. The two halves are not in tension: the tick is
resumable because its state is durable, not because it is short. Paying a fresh
session per wave is the failure mode, not the design.

## Contract

Every supervisor tick performs the same four concerns:

| Concern      | What it does                                 | Who decides          |
| ------------ | -------------------------------------------- | -------------------- |
| **Select**   | Choose which tasks to work on next           | Agent (LLM judgment) |
| **Dispatch** | Send tasks to workers, one sandbox each      | The `dispatch` skill |
| **Evaluate** | Judge whether worker output is acceptable    | Agent (LLM judgment) |
| **Persist**  | Record state for recovery across invocations | Task body (PKB)      |

Evaluation yields one of four outcomes: **Accept** (meets criteria, move on),
**Accept-partial** (the handed-back `partial` chunk passes its clauses -- see
[[specs/polecat/spec-partial-work-tight-loop-delivery.md]] §3 -- refused choices
are surfaced as decisions and continue tasks carry the remainder; the supervisor
accepts the chunk and routes the remainder rather than treating it as Revise or
Fail), **Revise** (specific problems found, create a new worker task with
feedback), or **Fail** (fundamental issues or retry budget exhausted, escalate to
a human).

The supervisor stays responsible for the work until it reaches a terminal state -- it
does not fire-and-forget. Responsibility is not polling: a tick is woken by a worker
terminating or by a bound the supervisor set at dispatch, and it establishes state by
reading durable evidence, never by asking a running worker how it is going.

## Status Lifecycle

```
queued → in_progress → merge_ready → done (deliverable accepted)
                │              │
                │              └→ review (needs human judgment; finish/merge failed)
                ├→ partial (terminal: chunk handed back, remainder carried by
                │           continue tasks -- see
                │           [[specs/polecat/spec-partial-work-tight-loop-delivery.md]] §4)
                └→ blocked (external dependency -- derived from directed `blocks` edges, not stored in frontmatter)
```

`blocked` is a derived status computed from directed `blocks` edges on blocking tasks, never stored directly in frontmatter. `done` means the deliverable was accepted -- evidence + output URL recorded on the
PKB task; a merged PR is the code-surface instance of this.

The canonical status set is mem's `VALID_STATUSES`, mirrored in this repository
at [[tests/policy.toml]] under `[aops.taxonomy]` and enforced against every
shipped skill by [[tests/test_skill_status_vocabulary.py]]. The supervisor uses
that set without extensions (`partial` is part of it).

## Related

- [[specs/dispatch/dispatch-system.md]] -- Isolated task workspaces and the delivery
  guarantees the supervisor dispatches onto
- `plugins/aops/skills/pull/SKILL.md` -- The operative skill: claiming a unit,
  working it, and carrying it to a terminal state.
- `plugins/aops/skills/dispatch/SKILL.md` -- The launcher that puts a worker in front of a unit.
  It launches containers; it makes no eligibility or ordering decision about which
  of an epic's children go next.
