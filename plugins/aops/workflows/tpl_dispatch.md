---
id: tpl_dispatch
title: "dispatch-cycle"
type: template
created: 2026-08-27T02:32:23.654636871+00:00
modified: 2026-08-27T02:32:23.654636871+00:00
last_modified: 2026-08-27T02:32:23.654638995+00:00
alias:
  - "temp_72e491b9-dispatch-cycle"
  - "temp_72e491b9"
permalink: temp_72e491b9
parent: aops-fa32d0ba
tags:
  - wf-template
  - workflow
  - dispatch
  - polecat
  - loop
  - periodic
  - state-file
  - context-discipline
  - junior
---

## What this step does

Runs **one cycle** of a standing, host-side dispatch loop: reconcile what finished while nobody was watching, dispatch at most one or two queued tasks, write state, HALT. Select it for any periodic driver that turns a `status: queued` PKB queue into launched workers on a fixed interval.

**Do not select it** for a one-off dispatch, for deciding _what_ belongs in the queue (that is `brief`), or for a loop whose driver is expected to read, judge, or improve the work it dispatches.

## Shape — one cycle per invocation, then HALT

The driver runs exactly one cycle and exits. There is no internal `while`. Re-invocation on the interval is what makes it a loop; a cycle that "just does one more" is out of contract.

**Cadence: ~30 minutes.** This is a starting value chosen by Nic (2026-08-27), not a derived optimum. Changing it is an adjustment, not a violation — record the new value and move on.

There is no stopping condition. The loop is indefinite by design; it pauses (below), it does not finish.

## Order within a cycle: reconcile first, then dispatch

1. **Reconcile** — `/reconcile`, **Batch trigger only**. The skill bundles a Batch (scheduled) and an Engagement (on-return) trigger ([[aops_8e4cf0a6]]); a periodic driver wants the Batch half and must not fire the Engagement half every 30 minutes.
2. **Dispatch** — at most 1–2 tasks.

Reconcile runs **first**, for three independent reasons, and this ordering is not a copy of [[aops_2caf8f62]]'s `tpl_daily` precedent:

- The queue is only true after reconcile. A task that finished unwatched may still sit at `queued`; dispatching it again burns a container and puts two writers on one store.
- The cap is on _concurrent_ workers, so free capacity cannot be computed until last cycle's in-flight set is resolved.
- The consecutive-failure counter takes its input from last cycle's outcomes. Dispatching before establishing them ticks the loop blind.

## Batch cap — at most 1–2 dispatches per cycle

The cap is a **grain and a rate limit, never a merit filter**. The driver does not decide a task looks unworthy; `queued` already carried that decision ([[kb-778cc9bb]]). The rest keep their place and go next cycle.

- A queue of thirty queued items still dispatches ≤2. Draining faster is the failure mode, not the goal.

## Dispatch the biggest coherent unit, not its subtasks

Prefer the largest coherent thing standing at `queued` — an epic, or a whole task — over its decomposed children. **Where a parent and its own child are both `queued`, take the parent and leave the child.**

Grounded in [[mem_8b65488a]] (Nic, 2026-07-16): _"I don't want to be involved in this process once an epic has been decomposed, not until it's time to merge the PR."_ Dispatching leaves re-inserts the human at every seam, which is the thing that ruling closed.

## State file

`/home/nic/junior/dispatch/.agents/dispatch-state.json` — on the WSL host, `dispatch-state.json`. Create the directory on first cycle.

- This is a simple scratch file; if it doesn't exist or is stale, just re-create it.
- Load it manually, it's just for you to keep track of epics that are queued and ready to go, tasks that are in-flight, and stuff recently completed so you can report it.

Minimum fields: `host`, `cycle_n`, `last_cycle_at` (ISO-8601 UTC), `dispatched` (per entry: task id, project, session name, launched-at, outcome, run-record path), `in_flight` (dispatched, outcome not yet established), `consecutive_failed_cycles`, `paused` + `paused_reason`.

**Write state on every cycle, including an empty or aborted one.** A cycle that leaves no trace is indistinguishable from a cycle that never ran, and the loop then reports continuity it does not have. On entry, compare `last_cycle_at` against the interval: a gap of many intervals means the loop was **not** running, and the cycle says so rather than proceeding as if it had ticked all along.

**The PKB is authoritative on task state; the state file is authoritative only on what this loop did.** Where they disagree, the PKB wins and the state file is corrected. Never write task status from the state file.

## Context discipline — load-bearing, not advice

The driver must stay thin across an unbounded number of cycles. It reads state, spawns subagents, takes back short structured summaries, writes state, halts.

**It may hold:** the state file; the queue listing at the granularity `list_tasks` returns (id, title, status, project) — never bodies; one-line structured returns from subagents (task id, exit code, run-record path).

**It must delegate, and must never pull into its own context:** task bodies, worker transcripts, run logs, `run.json`, container stdout, PR diffs, or anything a worker produced. A subagent reads those and returns a line. The driver has not read the work and has no standing to characterise it.

## Failure handling

**A failed dispatch is not a failed task.** Infrastructure that would not start is an outage to report; a worker that ran and returned non-zero is a result. Reporting the second as the first sends someone to fix the wrong thing.

**Identical failures across one cycle are infrastructure by definition.** If every dispatch in a cycle fails with the same signature, it is a failed dispatch, not several failed tasks.

**Threshold: two consecutive cycles in which every dispatch failed** ⇒ set `paused`, stop dispatching, keep reconciling, and surface **once**. Do not surface again each interval; a loop that alarms every thirty minutes trains the reader to ignore it. Resume requires a human clearing `paused`.

Worked example: [[aops_c5d9a1b0]] — the one real end-to-end polecat dispatch launched a genuine container that died on auth (`Not logged in`, `apiKeySource: none`). That is a standing systemic fault, so _every_ dispatch fails identically until it is fixed. A loop wired today ticks straight into it and would otherwise burn a container every thirty minutes forever. **This is a gating blocker: it must be resolved before the cadence is switched on.**

**A cycle that cannot follow this process halts, CANCELS THE LOOP, and surfaces. It does not proceed in a modified form.**

## An empty queue is a normal, silent cycle

Nothing to dispatch, no new progress: nothing to report. Not a failure, and not an occasion for a capability check. State is still written.

## Exit conditions

**NO WORKAROUNDS, FAIL FAST AND LOUD!**

- HALT IMMEDIATELY on ANY infrastructure error.

**Normal loop exit:**

- Reconcile ran (Batch trigger) and its findings are written back to the graph.
- ≤2 tasks dispatched, each the largest coherent queued unit available.
- State file written, with this host's name, this cycle's outcomes, and the failure counter updated.
- Driver context holds no task body, transcript, or run log.
- One line per dispatch reported: what it was, whether it succeeded, where the output is.
- HALT. No second cycle.
