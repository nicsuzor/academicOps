---
name: dispatch
description: Start polecat workers on queued tasks already on the graph, given task ids or a parent whose ready tasks should run. Writes no tasks. Exclude for turning an objective into tasks or changing a task's text (use /reify).
---

# /dispatch: start polecat workers on queued tasks

The task record is the whole message to the worker. Start it as written. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Questions and lookups that can be answered in-turn are answered directly without queueing tasks. Never dispatch questions or lookups to workers.

A polecat is a short-running container: it gets in, does its task, and gets out cleanly. Follow-up lives on the task graph, where the workflow puts it, never in a worker waiting for it. Dispatched workers operate under the worker state-only invariant: a worker may only mutate that task's own state (checking off criteria, recording verifiable evidence, transitioning status). Workers never inspect or modify edges across other tasks, compute reverse dependencies, or mint follow-up verification tasks; unblocking and sequencing belong exclusively to the graph engine and dispatcher.

## 1. Check each task is ready

Read each task you were given; for a parent, read its children and take the ready ones.

A task is ready when its status is `queued`, it has no open `needs` edges or incomplete children, it fills the `/reify` task template (Goal, Acceptance, Instructions, Output), and its Instructions conclude with the composed workflow's release step. When all open children under a composite task (`parent`) reach `done`, the composite task does not automatically close if it contains substantive acceptance criteria; instead, it becomes `ready` for an explicit synthesis and sign-off pass managed by `/reconcile`.

- A QA follow-up stays queued until its primary task releases `done`; once the primary task releases `done`, the QA follow-up's `needs` dependency is satisfied and it becomes ready for immediate dispatch.
- A task that folds follow-ups into internal subtasks is ready when executable by the same agent in one session; only send to `/reify` when work requires independent sessions, personas, or approval gates that must be cut into an epic with child tasks.
- Send a task that is unready or underspecified to `/reify` with its id, because writing and rewriting tasks is that skill's job. Dispatch the rest.
- **Graph deduplication and premise check**: Verify that no conflicting or overlapping open task exists (query `pkb_list_tasks` for active sibling tasks under the parent container) and that a premise-check PASS was recorded on reification before dispatching. If an unlinked sibling covers identical subsystem artifacts, halt and resolve the overlap.
- **Intake Contract:** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

## 2. Start the workers

Start one polecat worker per ready task, in parallel, through the project's dispatch pathway. The worker's whole prompt is `/ida:pull <task-id>`, because the task carries everything else.

Workers queue asynchronously; callers are not notified when they start, and neither track nor report starts. Assume work proceeds unless an error comes back. A worker dispatch failure is a halt: report the task id and the failure verbatim.

## 3. Report and stop (fire-and-forget)

Dispatch is fire-and-forget: the worker records its result on the task graph. Once tasks are dispatched, output the dispatch report and end your turn immediately:

- Output one line per task: title, id, and that the task is queued for a worker, or the `/reify` hand-back and why.
- Never wait for a worker to finish in the dispatch turn, never wait for or report worker starts, and never call or block on event-stream tools (such as `polecat_polecat_events`), status checks, sleep loops, or timers.

## 4. Act on a completed worker (separate invocation or turn)

Worker outputs (`status`, `completion_evidence`, `pr_url`) return on the PKB task graph after the container exits. When a session is invoked in a separate turn or invocation to check or `/reconcile` a completed worker (or woken by an external completion notification):

- **Done (`status=done`, `exit_code=0`)**: Read the worker's report on the task record and check it per `premise-check`. Read downstream tasks on the graph whose `needs` dependencies are now satisfied, and dispatch any that are ready. Trigger `/verify` on the deliverable or `/reconcile` as needed.
- **Partial or Failed (`status=partial` or `status=failed`, or `exit_code!=0`)**: Inspect the failure reason recorded on the task and container logs. If unfinished work remains, route the follow-up through `/reify` or escalate per fail-fast.
