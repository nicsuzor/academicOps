---
description: "Crew: the custodian ranks ready tasks, the front agent puts them to the user with a recommendation each, and the dispatcher starts workers on the ones approved."
id: wf-dispatch-queue
tags:
  - wf-template
  - dispatch
  - queue
title: Dispatch queue
type: template
---

## What this step does

Moves ready work to workers on the user's approval. Writes no tasks and changes no ranking.

## Obligations

1. **Find (custodian)**: in the graph's flow order, list tasks that are `queued` with no open `needs`, no unfinished children, and a goal and acceptance criteria; list `ready` tasks passing the same checks separately; list failing ones with the check they fail. Leave out tasks assigned to the user, in `review`, or in progress.
2. **Recommend (front agent)**: `dispatch`, `hold` or `ask` per task, with a one-clause reason, in the custodian's order. If the user does not answer in session, put the list in today's daily note under `## With you`.
3. **Dispatch**: promote approved `ready` tasks to `queued`; the custodian reifies each just before dispatch; run `/dispatch`; report each as started or its failure verbatim.
4. **Record** on each task: who approved, and the worker started, or the hold reason.

## Must not

Start a task the user did not approve in this run; reorder the custodian's list; rewrite tasks; start a new run while an earlier list is unanswered.

## When to include

On the user's request, or when the queue is non-empty and workers are idle.
