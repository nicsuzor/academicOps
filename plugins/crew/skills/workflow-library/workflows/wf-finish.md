---
title: Task completion
type: template
id: wf-finish
alias: [wf-finish]
default: true
description: "Worker: how a task ends -- output where the task says, acceptance ticked with evidence, one release status."
tags: [wf-template, finish, lifecycle, default]
---

## What this step does

Ends a task. The work is reviewed separately after hand-back, so finishing means only that the output is where the task says and the report is honest.

## Procedure

1. Put the output where the task's Output names (the report, the working branch, or the shared location). Nothing is left only in the container.
2. Tick each acceptance item only with its evidence; leave an unmet item unticked with the reason.
3. End with one outcome (a crew session releases it via `/dump`; a worker container states it in its final report, which the dispatch service records):
   - `done`: every in-scope item is met. Never wait for review, CI, merge or anyone to use it.
   - `partial`: in-scope work remains, or the next step needs access or approval the worker lacks; say which in the reason.
   - `failed`: the work cannot meet its criteria; give the cause.

Never release `review`, and never mint follow-up tasks.

## When to include

Every task (the default).
