---
description: Dispatch queue -- the PKB custodian finds and ranks ready tasks, the front agent presents them with one recommendation per task for user approval, and the dispatcher starts workers on approved tasks.
id: wf-dispatch-queue
tags:
  - wf-template
  - dispatch
  - queue
title: Dispatch queue
type: template
---

## What this step does

Moves ready work from the graph to workers via user approval: finds ready tasks, presents them ranked with recommendations, and dispatches what the user approves. Authors no tasks and alters no ranking. Three roles in order: PKB custodian finds and ranks, front agent shows and asks, dispatcher starts workers.

## Obligations

1. **Find candidates (custodian)**: Query the graph alone in flow order (hard-deadline lane first, then gain and loss averted), emitting one line per task (`id`, `title`, `project`, `status`, what it unblocks):
   - _Dispatchable now_: `status: queued`, no open `needs`, no incomplete children, explicit goal and acceptance criteria (including repo-scoped epics queued by `/q` without pre-dispatch `/reify`).
   - _Awaiting promotion_: `status: ready` passing the same checks; listed separately for user approval.
   - _Not ready_: `queued` or `ready` tasks failing a check, reported with the failing check and withheld from dispatch. Never run pre-dispatch `/reify` (worker `/supervise` runs `/reify` in-session). Exclude tasks assigned to the user, in `review`, or `in_progress`.
2. **Recommend and show (front agent)**: For each candidate write `dispatch`, `hold`, or `ask` with a one-clause reason (standing user ruling, unmodeled dependency, disproportionate cost, or in-flight conflict). Present the list in the graph's exact order with recommendation first via multi-select (`dispatch all recommended` first; on single-choice channels, one decision per message). If unanswered in-session, write the list to today's daily note under `## With you` and end.
3. **Dispatch (`sara`)**: Pass approved IDs with the user's words and dispatch reason (no method instructions) to `sara`, promoting approved `ready` tasks to `queued` first. `sara` runs `sara:dispatch` fire-and-forget (`/ida:supervise` or `/ida:pull` by complexity, model calibrated from `fast` default) and reports per task either launched confirmation or failure verbatim. Leave held tasks in place with the hold reason recorded.
4. **Record**: Record worker, time, and user approval on each dispatched task, and hold reasons on held tasks; write nothing else to the daily note except an unanswered list.

## Must not

- Start a worker on any task not shown to and approved by the user in this run, or dispatch from a stored list.
- Reorder, filter, or re-rank the custodian's list (express disagreements via `hold` or `ask`).
- Author, rewrite, or decompose task definitions, promote `inbox` work, or tell the dispatcher how/where to run.
- Send bare task IDs without task name and purpose, or start a new run while an earlier run's list remains unanswered (re-show that list instead).

## Output Contract

Emit one synthesized report naming IDs for every touched task (no bare counts): (1) list shown (`id`, `title`, `status`, recommendation, reason, in order), (2) user's verbatim answer or daily-note deferral, (3) per approved task queued status or verbatim failure, (4) per held task recorded hold reason, and (5) not-ready tasks with failing checks.

## When to Include

On user request, after graph truth maintenance mints rework tasks, at session start, or when worker capacity is idle and the queue is non-empty.
