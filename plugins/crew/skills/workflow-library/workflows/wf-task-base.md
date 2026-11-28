---
title: Task base
type: template
description: "Worker: the base every task carries -- goal, acceptance, where the output goes, and the report. Use alone for any task no narrower base fits."
tags: [base, task]
---

## What this step does

Sets the minimum every task needs. Add nothing to a task that its ask or another selected template does not require: the work is reviewed separately once it is handed back, so the task carries no review, sign-off, approval or delivery steps of its own.

## Task shape

- **Goal**: one sentence naming the end state.
- **Acceptance**: observable outcomes the worker itself delivers, one line each; never line numbers, mechanisms, or acts after hand-back (review, CI, merge, deployment, someone reading it).
- **Output**: where the result goes. One of: the answer itself, in the final report; commits on the working branch; a file at a shared location the task names. Never only in the container's own scratch space.
- **Report**: the final message states what was done and, for each acceptance item, the evidence (output, path, commit) or why it is unmet.

## Rules

- One task by default. Split only for a second repository or a wait on something outside the session.
- Read what you change in full before changing it.
- Needs no privileged access: no pushing, opening or merging pull requests, publishing, deploying, or sending anything to anyone. If the work cannot finish without such a step, stop there and say so in the report.
- A refusal at the container boundary is a stop, never a workaround.

## When to include

Every task.
