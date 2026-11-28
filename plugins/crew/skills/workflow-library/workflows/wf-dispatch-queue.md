---
description: "Crew: rank ready tasks, present them to the user with a recommendation each, and dispatch workers on the approved ones as the composed workflow assigns roles."
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

1. **Find**: as assigned by the composed workflow, list tasks in the graph's flow order that are `queued` with no open `needs`, no unfinished children, and a goal and acceptance criteria; list `ready` tasks passing the same checks separately; list failing ones with the check they fail. Leave out tasks assigned to the user, in `review`, or in progress.
2. **Recommend**: as assigned by the composed workflow, recommend `dispatch`, `hold` or `ask` per task, with a one-clause reason, preserving the ranked order. If the user does not answer in session, record the unanswered list where the composed workflow specifies.
3. **Dispatch**: promote approved `ready` tasks to `queued`; prepare and dispatch each per the composed workflow; report each as started or its failure verbatim.
4. **Record** on each task: who approved, and the worker started, or the hold reason.

## Must not

Start a task the user did not approve in this run; reorder the ranked list; rewrite tasks; start a new run while an earlier list is unanswered.

## When to include

On the user's request, or when the queue is non-empty and workers are idle.
