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
- **Intake Contract:** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

## 2. Start the workers

Start one polecat worker per ready task, in parallel, through the project's dispatch pathway. The worker's whole prompt is `/ida:pull <task-id>`, because the task carries everything else.

Confirm each worker started. A worker that failed to start is a halt: report the task id and the failure verbatim.

## 3. Receive completion events

Do not poll workers or wait on a timer (no status checking loops, no sleep loops, no cron timers). The dispatching session learns that a polecat has finished from polecat-mcp's completion event delivered over the event route or cross-session bus:

`[polecat-exit] task=<task-id> container=<container-name> exit_code=<code|0> status=<review|done|partial|failed> pr_url=<url> duration=<seconds>s`

## 4. Act on completion

When the completion event arrives, act on it immediately:

- **Review or Done (`status=review` or `status=done`, `exit_code=0`)**: The worker delivered. Trigger `/verify` on the deliverable or `/reconcile` to process the PR and update task state. Read downstream tasks on the graph whose `needs` dependencies are now satisfied, and dispatch any that are ready.
- **Partial or Failed (`status=partial` or `status=failed`, or `exit_code!=0`)**: Inspect the failure reason recorded on the task and container logs. If unfinished work remains, route the follow-up through `/reify` or escalate per fail-fast.

## 5. Report

Output one line per task: title, id, and the worker started (container name), or the `/reify` hand-back and why.
