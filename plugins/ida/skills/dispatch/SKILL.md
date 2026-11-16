---
name: dispatch
description: Start polecat containers on queued repo-scoped epic tasks or ready leaf tasks on the graph. Writes no tasks. Use for headless worker container execution and dispatching ready tasks. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch: Start Polecat Containers on Queued Tasks

The task record is the whole message to the container. Start it as written. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Questions and lookups that can be answered in-turn are answered directly without queueing tasks. Never dispatch questions or lookups to containers.

A polecat is an isolated container session: it gets in, executes its task, and gets out cleanly. Dispatched containers operate across two distinct modes:

- **Supervised Container Execution (`/ida:supervise <task-id>`)**: Default for repo-scoped epic tasks queued by `/q`. Launches the container coordinator (`james`) on a `coordinator` model calibrated to task complexity and importance. The container coordinator enriches its claimed task via `/reify` in-session, composes the workflow, fans out across subagents to deliver everything possible in session, and leaves follow-up tasks on the graph only for out-of-session work.
- **Plain Leaf Execution (`/ida:pull <task-id>`)**: Fast-path execution for already-decomposed leaf tasks or single-skill runs without re-reifying. Plain leaf workers operate strictly under the worker state-only invariant: they mutate only their claimed task's own state and never mint follow-up tasks.

## 1. Check Each Task Is Ready

Read each task you were given; for a parent container, read its children and select ready tasks.

A task is ready for dispatch when its status is `queued` and it has no open `needs` edges or incomplete prerequisite dependencies. Dispatch invokes polecat containers directly with the repo-scoped epic task queued by `/q` without pre-dispatch reification or hunting for leaf tasks. When all open children under a composite task reach `done`, the composite task becomes `ready` for synthesis and sign-off managed by `/reconcile`.

- **Queue readiness**: A repo-scoped epic task queued by `/q` with no open `needs` is immediately ready for container dispatch.
- **Dependency satisfaction**: A dependent task or QA follow-up stays `queued` until its prerequisite releases `done`; once satisfied, it becomes ready for dispatch.
- **Deduplication and conflict check**: Verify that no conflicting or overlapping running container exists before dispatching. If an unlinked task covers identical subsystem artifacts, halt and resolve the overlap before launching.
- **Intake Contract**: Dispatched tasks carry explicit acceptance criteria on the PKB task before container execution begins.

## 2. Start the Containers

Launch one polecat container per ready task, in parallel, through the project's dispatch pathway:

- **Repo-scoped epic tasks**: Launch the container coordinator (`james`) on an appropriate `coordinator` model (calibrated to the task's complexity or importance) with the command:
  ```bash
  /ida:supervise <task-id>
  ```
- **Already-decomposed leaf tasks**: Launch a worker container with the fast-path command:
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
