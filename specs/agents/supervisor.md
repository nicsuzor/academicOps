---
id: agents-e4ca3ecd
title: Supervisor Architecture
type: spec
description: What the supervisor is, when it's invoked, and its contract
status: ready
tier: polecat
depends_on: [polecat-system]
tags: [spec, polecat, architecture, supervisor]
created: 2026-03-11
---

# Supervisor Architecture

The supervisor is the framework's delegate-and-verify process: a stateless tick that
selects or creates work, dispatches it to workers, evaluates the results, and persists
state for the next tick. It operates at every scale — a single epic, a multi-epic
release, or conversational orchestration of background workers — using the same
discipline at each.

## User Story

As an orchestrator (human or agent) with work to get done by other agents, I want a
single process I invoke rather than hand-roll, so that every delegated task is proven
before I trust it — not just claimed complete.

## When It's Invoked

Any orchestrator that delegates work and must verify it gets done invokes the
`supervisor` skill — never hand-rolled inline. This covers:

- Epic-level orchestration (one PKB epic, state in the epic body)
- Portfolio/release supervision (many epics, state in the release task body)
- Conversational orchestration of background workers (e.g. "don't get involved
  yourself, make sure it gets done")

The supervisor is driven tick-by-tick by `/loop`; cross-tick state lives entirely in
the task body, so any instance can resume from where a prior one left off.

## Contract

Every supervisor tick performs the same four concerns:

| Concern      | What it does                                 | Who decides           |
| ------------ | -------------------------------------------- | --------------------- |
| **Select**   | Choose which tasks to work on next           | Agent (LLM judgment)  |
| **Dispatch** | Send tasks to workers                        | `polecat run -t <id>` |
| **Evaluate** | Judge whether worker output is acceptable    | Agent (LLM judgment)  |
| **Persist**  | Record state for recovery across invocations | Task body (PKB)       |

Evaluation yields one of three outcomes: **Accept** (meets criteria, move on),
**Revise** (specific problems found, create a new worker task with feedback), or
**Fail** (fundamental issues or retry budget exhausted, escalate to a human).

The supervisor stays responsible for the work until it reaches a terminal state — it
checks progress on every tick, it does not fire-and-forget.

## Relationship to `/pull` and `/dispatch`

`/pull`, `/dispatch`, and `/supervisor` are three verbs over the same queue, differing
in where work runs and whether they loop:

| Verb              | Where work runs                      | Loops?                         |
| ----------------- | ------------------------------------ | ------------------------------ |
| **`/pull`**       | Inline, this interactive session     | No — one task                  |
| **`/dispatch`**   | Background worker (polecat/subagent) | No — one dispatch step         |
| **`/supervisor`** | Background workers, across ticks     | Yes — stateless tick + `/loop` |

`/pull` and `/dispatch` share one Select+Gates spine, implemented once in the
`task-lifecycle` skill: `/pull` claims the task and runs it inline (with licence to
ask the user questions); `/dispatch` routes it to a worker and halts.

The supervisor does **not** call `task-lifecycle`. Its own Dispatch phase applies the
same premise and pre-flight gates independently, then adds the proof, ledger, and
escalation discipline that spans multiple ticks — `task-lifecycle` has no concept of
"across ticks." `/dispatch` is a thin one-shot slice of a single supervisor dispatch
step.

A `/supervisor` invoked interactively schedules its own next tick when work remains
and it is not at a terminal state, so one invocation visibly keeps going without the
user manually wiring `/loop`. It stops self-arming at the terminal state.

## Status Lifecycle

```
queued → in_progress → merge_ready → done
                │              │
                │              └→ review (engineer review or merge failed)
                └→ blocked (dependency, failure)
```

See [[aops-core/skills/remember/references/TAXONOMY.md#status-values-and-transitions]]
for canonical status definitions. The supervisor uses the canonical set without
extensions.

## Related

- [[specs/polecat-system.md]] — Worktrees, bare mirrors, task claiming that the
  supervisor dispatches onto
- `aops-core/skills/supervisor/SKILL.md` — The operative skill (orient → act →
  checkpoint loop, proof discipline, evaluation protocol)
- `aops-core/skills/task-lifecycle/SKILL.md` — The Select+Gates spine shared by
  `/pull` and `/dispatch`
