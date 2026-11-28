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

Ends a task. Output goes where the composed workflow and task specify and the report is honest; review, sign-off, approval, or delivery steps run only when the composed workflow includes them.

## Procedure

1. Put the output where the composed workflow and task specify (the report, the working branch, or a shared location). Nothing is left only in the container.
2. Tick each acceptance item only with its evidence; leave an unmet item unticked with the reason.
3. End with one outcome (recorded via the session's release mechanism, or stated in a worker container's final report for the dispatch service to record):
   - `done`: every in-scope item is met. Never wait for review, CI, merge or anyone to use it.
   - `partial`: in-scope work remains, or the next step needs access or approval the worker lacks; say which in the reason.
   - `failed`: the work cannot meet its criteria; give the cause.

Never release `review`, and never mint follow-up tasks.

## When to include

Every task (the default).
