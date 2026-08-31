---
id: supervisor-spec
title: Supervisor Architecture
type: spec
description: What the supervisor is, when it's invoked, and its contract
status: ready
tier: polecat
depends_on: [polecat-system]
tags: [spec, polecat, architecture, supervisor]
---

# Supervisor Architecture

The supervisor is the framework's delegate-and-verify process: a stateless tick that
selects or creates work, dispatches it to workers, evaluates the results, and persists
state for the next tick. It operates at every scale — a single epic, a multi-epic
release, or conversational orchestration of background workers — using the same
discipline at each.

## User Story

As a researcher delegating work to agents, I want a single supervision process I
invoke — never hand-rolled — that decides for me when a piece of work should run as a
quick local subagent in my session and when it should be dispatched as a polecat
(isolated workspace, background, full lifecycle), and that guarantees every delegated
piece of work leaves a trace I can inspect — a task record, a transcript, and a
recorded verdict — so that work is proven before it is trusted and nothing is ever
fire-and-forgotten.

## Routing: Surface and Cadence

Routing is a cadence-and-placement choice over one unified worker contract
([[specs/enforcement/task-contract.md]]); the user does not have to specify. The
orchestrator picks the surface (in-session subagent | polecat | agent team) and
the cadence (wait vs fire-and-forget) for latency and isolation convenience;
eligibility and deliverable shape are surface-agnostic — the deliverable is
whatever output URL the assembled workflow specifies. A literature review and a
code change are the same contract with different assembled workflows.

Placement heuristics:

- **Isolation**: repo-scoped work that mutates files benefits from a **polecat**'s
  isolated workspace and branch; the PR is the code-surface instance of the
  deliverable, not a routing determinant.
- **Review steps**: carry a pauli-specified lens set at decomposition, and run per the assembled
  workflow (see [[specs/enforcement/workflow.md]]).
- **Findings returned inline**: research or synthesis whose output the current
  conversation needs suits a **local subagent** (a wait-cadence choice).
- **User in the loop (preference, not a rule)**: route inline via `/pull` when a
  blocking judgment call is known up-front; otherwise a background worker
  legitimately attempts everything derivable and hands back `partial` with the
  refused decisions surfaced.
- **Not dispatchable**: missing inputs or blockers → record a block note and defer.

This routing is implemented in the `/dispatch` command. Weighing
expected duration/effort in the routing decision is a target requirement, not yet
implemented.

## Observability Guarantee

Every delegation MUST leave an inspectable trace; nothing is fire-and-forgotten:

- **Task record**: every dispatch is recorded on a PKB task (status, assignee,
  dispatch note, and on completion the evidence + output URL — the PR URL where
  the surface is code).
- **Transcript**: the worker's run is retained and locatable (polecat lifecycle
  events at `$POLECAT_HOME/transcripts/<task-id>.jsonl`; session transcripts under
  `$AOPS_SESSIONS`). Where a surface does not yet persist transcripts automatically,
  this is a target requirement, not yet enforced.
- **Verdict**: the supervisor's evaluation outcome is recorded on the task or epic
  ledger, so any later reader can see what was accepted and why.

## When It's Invoked

Supervision covers:

- Epic-level orchestration (one PKB epic — an epic is just a task with children —
  state in the epic body)
- Portfolio/release supervision (many epics, state in the release task body)
- Conversational orchestration of background workers (e.g. "don't get involved
  yourself, make sure it gets done")

The supervisor is driven tick-by-tick by `/loop`; cross-tick state lives entirely in
the task body, so any instance can resume from where a prior one left off.

## Contract

Every supervisor tick performs the same four concerns:

| Concern      | What it does                                 | Who decides          |
| ------------ | -------------------------------------------- | -------------------- |
| **Select**   | Choose which tasks to work on next           | Agent (LLM judgment) |
| **Dispatch** | Send tasks to workers (routing rules above)  | Polecat or subagent  |
| **Evaluate** | Judge whether worker output is acceptable    | Agent (LLM judgment) |
| **Persist**  | Record state for recovery across invocations | Task body (PKB)      |

Evaluation yields one of four outcomes: **Accept** (meets criteria, move on),
**Accept-partial** (the handed-back `partial` chunk passes its clauses — see
[[specs/polecat/spec-partial-work-tight-loop-delivery.md]] §3 — refused choices
are surfaced as decisions and continue tasks carry the remainder; the supervisor
accepts the chunk and routes the remainder rather than treating it as Revise or
Fail), **Revise** (specific problems found, create a new worker task with
feedback), or **Fail** (fundamental issues or retry budget exhausted, escalate to
a human).

The supervisor stays responsible for the work until it reaches a terminal state — it
does not fire-and-forget. Responsibility is not polling: a tick is woken by a worker
terminating or by a bound the supervisor set at dispatch, and it establishes state by
reading durable evidence, never by asking a running worker how it is going.

## Status Lifecycle

```
queued → in_progress → merge_ready → done (deliverable accepted)
                │              │
                │              └→ review (needs human judgment; finish/merge failed)
                ├→ partial (terminal: chunk handed back, remainder carried by
                │           continue tasks — see
                │           [[specs/polecat/spec-partial-work-tight-loop-delivery.md]] §4)
                └→ blocked (external dependency)
```

`done` means the deliverable was accepted — evidence + output URL recorded on the
PKB task; a merged PR is the code-surface instance of this.

Canonical status definitions were documented at
[[plugins.disabled/skills.disabled/graph-maintenance/references/taxonomy.md#status]];
that skill is retired and excluded from the build, so treat the file as
historical reference. The supervisor uses the canonical set without
extensions (`partial` is part of that canonical set).

## Related

- [[specs/polecat/polecat-system.md]] — Isolated task workspaces and the delivery
  guarantees the supervisor dispatches onto
- `plugins/aops/skills/pull/SKILL.md` — The operative skill: claiming a unit,
  working it, and carrying it to a terminal state.
- `plugins/orchestrate/agents/pc.md` — The launcher that puts a worker in front of a unit.
  It launches containers; it makes no eligibility or ordering decision about which
  of an epic's children go next.
