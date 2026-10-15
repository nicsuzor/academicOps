---
name: dispatch
description: Start polecat workers on queued tasks already on the graph, given task ids or a parent whose ready tasks should run. Writes no tasks. Exclude for turning an objective into tasks or changing a task's text (use /reify).
---

# /dispatch: start polecat workers on queued tasks

The task record is the whole message to the worker. Start it as written.

A polecat is a short-running container: it gets in, does its task, and gets out cleanly. Follow-up lives on the task graph, where the workflow puts it, never in a worker waiting for it.

## 1. Check each task is ready

Read each task you were given; for a parent, read its children and take the ready ones.

A task is ready when its status is `queued`, it has no open `needs` edges or incomplete children, and it fills the `/reify` task template (Goal, Acceptance, Instructions, Output), and its Instructions end with the finish template's finish step.

- A QA follow-up stays queued until its hard dependency completes; it is not ready yet.
- A task that folds follow-ups into itself is not ready: send it to `/reify` to be cut.
- Send a task that is unready or underspecified to `/reify` with its id, because writing and rewriting tasks is that skill's job. Dispatch the rest.

## 2. Start the workers

Start one polecat worker per ready task, in parallel, through the project's dispatch pathway. The worker's whole prompt is `/ida:pull <task-id>`, because the task carries everything else.

Confirm each worker started. A worker that failed to start is a halt: report the task id and the failure verbatim.

## 3. Report

Dispatch is fire-and-forget: the worker records its result on the task, so do not poll or wait for it.

Output one line per task: title, id, and the worker started (container name), or the `/reify` hand-back and why.
