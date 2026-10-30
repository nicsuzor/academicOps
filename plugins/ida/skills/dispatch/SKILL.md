---
name: dispatch
description: Start polecat workers on queued tasks already on the graph, given task ids or a parent whose ready tasks should run. Writes no tasks. Exclude for turning an objective into tasks or changing a task's text (use /reify).
---

# /dispatch: start polecat workers on queued tasks

The task record is the whole message to the worker. Start it as written. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Questions and lookups that can be answered in-turn are answered directly without queueing tasks. Never dispatch questions or lookups to workers.

A polecat is a short-running container: it gets in, does its task, and gets out cleanly. Follow-up lives on the task graph, where the workflow puts it, never in a worker waiting for it.

## 1. Check each task is ready

Read each task you were given; for a parent, read its children and take the ready ones.

A task is ready when its status is `queued`, it has no open `needs` edges or incomplete children, it fills the `/reify` task template (Goal, Acceptance, Instructions, Output), and its Instructions conclude with the composed workflow's release step.

- A QA follow-up stays queued until its primary task releases `done`; once the primary task releases `done`, the QA follow-up's `needs` dependency is satisfied and it becomes ready for immediate dispatch.
- A task that folds follow-ups into internal subtasks is ready when executable by the same agent in one session; only send to `/reify` when work requires independent sessions, personas, or approval gates that must be cut into an epic with child tasks.
- Send a task that is unready or underspecified to `/reify` with its id, because writing and rewriting tasks is that skill's job. Dispatch the rest.
- **Intake Contract:** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

## 2. Start the workers

Start one polecat worker per ready task, in parallel, through the project's dispatch pathway. The worker's whole prompt is `/ida:pull <task-id>`, because the task carries everything else.

Confirm each worker started. A worker that failed to start is a halt: report the task id and the failure verbatim.

## 3. Receive completion events

Do not poll workers or wait on a timer (no status checking loops, no sleep loops, no cron timers). Container termination is recorded by the Docker exit listener, exported as OpenTelemetry `polecat.container.exit` spans, and queued in `polecat_events`. The dispatching session learns of worker completion from notifications delivered across the operational dashboard daemon bridge rather than direct socket pushes or client polling loops.

## 4. Act on completion

When a completion notification arrives, act on it immediately:

- **Done (`status=done`, `exit_code=0`)**: The worker delivered. Read downstream tasks on the graph (e.g. QA follow-up or review task) whose `needs` dependencies are now satisfied, and dispatch any that are ready. Trigger `/verify` on the deliverable or `/reconcile` as needed.
- **Partial or Failed (`status=partial` or `status=failed`, or `exit_code!=0`)**: Inspect the failure reason recorded on the task and container logs. If unfinished work remains, route the follow-up through `/reify` or escalate per fail-fast.

## 5. Report

Output one line per task: title, id, and the worker started (container name), or the `/reify` hand-back and why.
