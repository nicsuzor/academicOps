---
name: dispatch
description: Start polecat containers on queued repo-scoped tasks or ready leaf tasks on the graph. Writes no tasks. Use for headless worker container execution and dispatching ready tasks. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch: Start Polecat Containers on Queued Tasks

The task record is the whole message to the container; dispatch ready tasks without rewriting them. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Questions and lookups that can be answered in-turn are answered directly without queueing tasks. Never dispatch questions or lookups to containers.

A polecat is an isolated container session: it gets in, executes its task, and gets out cleanly. Dispatched containers operate across two distinct modes:

- **Supervised Container Execution (`/ida:supervise <task-id>`)**: Default for repo-scoped tasks queued by `/q`, un-reified multi-stage tasks, or pre-reified composite tasks needing coordinator supervision or multi-agent fan-out. Launches the container coordinator (`james`) on a `coordinator` model calibrated to task complexity and importance. The container coordinator runs `/reify` in-session if un-reified (or takes the fast path if already composed), coordinates subagents to deliver everything possible in session, and leaves follow-up tasks on the graph only for out-of-session work.
- **Plain Leaf Execution (`/ida:pull <task-id>`)**: Fast-path execution for already-decomposed leaf tasks or single-skill runs without re-reifying. Plain leaf workers operate strictly under the worker state-only invariant: they mutate only their claimed task's own state and never mint follow-up tasks.

## 1. Check Each Task Is Ready

Read each task you were given; for a parent container, read its children and select ready tasks.

A task is ready for dispatch when its status is `queued` and it has no open `needs` edges or incomplete prerequisite dependencies. Dispatch invokes polecat containers directly with the repo-scoped task queued by `/q` without pre-dispatch reification or hunting for leaf tasks. When all open children under a composite task reach `done`, the composite task becomes `ready` for synthesis and sign-off managed by `/reconcile`.

- **Queue readiness**: A repo-scoped task queued by `/q` with no open `needs` is immediately ready for container dispatch.
- **Dependency satisfaction**: A dependent task or QA follow-up stays `queued` until its prerequisite releases `done`; once satisfied, it becomes ready for dispatch.
- **Deduplication and conflict check**: Verify that no container is already running on the same task ID before launching. If an unlinked task covers overlapping subsystem artifacts, start the worker as handed and send the overlap to the supervisor as a clarification.
- **Intake Contract & Satisfiability Gate**: Dispatched tasks carry explicit acceptance criteria on the PKB task before launching a container. Check every `queued` task's criteria, scope, and composition state before choosing a command, and always start a worker on the handed task:
  - _Gap or external/post-exit criterion_: If a criterion appears unreachable by the worker before releasing `done` (such as downstream independent review, PR merge, host deployment, or human approval) or the task has a gap, start the worker on the task it is handed and send the gap to the supervisor as a clarification -- never refuse to dispatch.
  - _Supervised container tasks (`/ida:supervise`)_: Tasks with container-satisfiable criteria that are un-reified (lacking `## Instructions` + `## Appendix: Sources` and not a single-skill `invoke /<skill>` directive) or are pre-reified composite/multi-stage tasks requiring container supervision or multi-agent fan-out: launch `/ida:supervise <task-id>`.
  - _Reified atomic leaf or single-skill tasks (`/ida:pull`)_: Single-skill directives (`invoke /<skill>`) or reified atomic leaf tasks (`## Instructions` + `## Appendix: Sources`) requiring no container supervision or fan-out whose criteria are all satisfiable by a single leaf worker before releasing `done`: launch `/ida:pull <task-id>`.

## 2. Start the Containers

Launch one polecat container per ready task, in parallel, through the project's dispatch pathway:

- **Supervised container tasks**: Launch the container coordinator (`james`) on an appropriate `coordinator` model (calibrated to the task's complexity or importance) with the command:
  ```bash
  /ida:supervise <task-id>
  ```
- **Reified atomic leaf or single-skill tasks**: Launch a worker container with the fast-path command:
  ```bash
  /ida:pull <task-id>
  ```

Containers launch asynchronously; callers are not notified when they start, and neither track nor report starts. Assume work proceeds unless an error comes back. A container dispatch failure is a halt: report the task ID and the failure verbatim.

## 3. Report and Stop (Fire-and-Forget)

Dispatch is fire-and-forget: the container records its result on the task graph. Once tasks are dispatched, output the dispatch report and end your turn immediately:

- Output one line per task: title, id, selected command (`/ida:supervise` or `/ida:pull`), and that the container is launched.
- Never wait for a container to finish in the dispatch turn, never wait for or report container starts, and never call or block on event-stream tools, status checks, sleep loops, or timers.

## 4. Act on a Completed Container (Separate Invocation or Turn)

Container outputs (`status`, `completion_evidence`, `pr_url`) return on the PKB task graph after the container exits. When a session is invoked in a separate turn to check or `/reconcile` a completed container:

- **Done (`status=done`, `exit_code=0`)**: Read the container's report on the task record and check it per `premise-check`. Read downstream tasks on the graph whose `needs` dependencies are now satisfied, and dispatch any that are ready. Trigger `/verify` on the deliverable or `/reconcile` as needed.
- **Partial or Failed (`status=partial` or `status=failed`, or `exit_code!=0`)**: Inspect the failure reason recorded on the task and container logs. If unfinished work remains, route follow-up tasks through the graph engine or escalate per fail-fast.
