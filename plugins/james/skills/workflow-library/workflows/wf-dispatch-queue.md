---
description: Dispatch queue -- the PKB custodian finds the tasks ready to run and ranks them, the front agent shows the user that list with one recommendation per task and takes their choice, and the dispatcher starts workers on the tasks the user approved.
id: wf-dispatch-queue
tags:
  - wf-template
  - dispatch
  - queue
title: wf-dispatch-queue
type: template
---

## What this step does

Moves ready work from the graph to workers through the user's choice: finds what is ready, shows it to the user ranked with a recommendation on each, and dispatches what the user approves. Authors no tasks and changes no ranking. Complements graph truth maintenance, which mints rework tasks but starts no worker.

Three roles, in order: the PKB custodian finds and ranks; the front agent shows and asks; the dispatcher starts the workers. Any capable agent may hold a role.

## Obligations

1. **Find the candidates (custodian)**: The front agent asks the custodian for every task that could be dispatched now. The custodian answers from the graph alone, in the graph's own flow order (hard-deadline lane first, then by gain and loss averted), with one line per task: id, title, project, status, and what it unblocks.
   - _Dispatchable now_: `status: queued`, no open `needs`, no incomplete children, and explicit goal/acceptance criteria on the task (covering repo-scoped epic tasks queued on the PKB without requiring pre-dispatch workflow expansion or leaf splitting).
   - _Awaiting promotion_: `status: ready` that otherwise passes the same checks. Listed separately; the user's approval is the promotion.
   - _Not ready_: a `queued` or `ready` task that fails a check (such as open `needs` or missing acceptance criteria). Reported with the failing check; it is not offered for dispatch. Tasks are not pre-expanded before dispatch, as `/james:supervise` composes workflows inline in-session.
   - Tasks assigned to the user, held in `review` by the user, or `in_progress` under a live claim are never candidates.
2. **Recommend and show (front agent)**: For each candidate the front agent writes one recommendation, `dispatch`, `hold`, or `ask`, with its reason in one clause: a standing ruling by the user that settles it, a dependency the graph does not carry, a cost out of proportion to the task's worth, or a conflict with work in flight (same file, same branch, same reviewer). The list goes to the user in the graph's order, unchanged, with the recommendation first on each line; the whole list is one question, answered by multi-select, with `dispatch all recommended` as its first option. On a channel that cannot carry a multi-select, one decision per message, in order. If the user does not answer in the session, the list is written to today's daily note under `## With you`, and the step ends.
3. **Dispatch through the dispatcher (dispatcher)**: On the user's answer the front agent sends the dispatcher the approved ids and, for each, the user's words and the reason it is being dispatched, nothing on method. Approving a `ready` task promotes it to `queued` on the record before it is sent. The dispatcher launches workers on the set and answers with, per task, that the task was queued for a worker or the failure verbatim. Tasks the user held stay where they are, with the user's reason recorded on the task.
4. **Record**: Each dispatched task carries the dispatch on its record (worker, time, the user's approval). Each held task carries the hold reason. The daily note receives nothing but the unanswered list under `## With you`.

## Must not

- Must not start a worker on a task the user has not approved in this run, or on a task not shown to the user.
- Must not reorder, filter, or re-rank the custodian's list; a disagreement with the order is a `hold` or `ask` recommendation with its reason, never a different order.
- Must not author, rewrite, or decompose task definitions; the only other writes are the `ready` to `queued` promotion and the dispatch and hold records of obligations 3 and 4. Must not promote `inbox` work.
- Must not tell the dispatcher how to dispatch, which worker to use, or where output goes.
- Must not send the user a bare id: every line names the task and what it is for.
- Must not run while a dispatch from an earlier run of this step is still unanswered by the user; show that list again instead.
- Must not dispatch from a stored list; the candidates are found afresh on each run.

## Output contract

Emit one synthesized result:

1. The list as shown to the user: for each candidate its id, title, status, recommendation and reason, in the order shown.
2. The user's answer verbatim, or that none came and the list went to the daily note.
3. Per approved task: that the task was queued for a worker or the failure verbatim from the dispatcher.
4. Per held task: the hold reason recorded.
5. Tasks identified as not ready, with the failing check.
6. Name ids for every touched task (no bare counts).

## When to include

On the user's request, after a graph truth-maintenance pass has minted rework tasks, at the start of a working session, or whenever worker capacity is idle and the queue is not empty.
