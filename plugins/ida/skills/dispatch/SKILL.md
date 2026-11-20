---
name: dispatch
description: Start isolated worker containers on queued repo-scoped tasks or ready leaf tasks on the graph without rewriting them. Use for headless worker container dispatch. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch -- Start Worker Containers on Queued Tasks

The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them. Use the task pipeline for durable deliverables (workflows, instructions, specifications, code); answer questions and lookups in-turn without queueing or dispatching containers.

Dispatched worker containers operate in two modes:

- **Supervised container (`/ida:supervise <task-id>`)**: Default for repo-scoped tasks queued by `/q`, un-reified multi-stage tasks, or composite tasks needing coordination and fan-out. Launches the lead executor (`james`) calibrated by complexity tier; runs `/reify` in session if un-reified and leaves follow-ups only for out-of-session work.
- **Leaf container (`/ida:pull <task-id>`)**: Fast-path execution for already-decomposed leaf tasks or single-skill directives without re-reifying, strictly state-only on the claimed task.

## 1. Verify Readiness & Satisfiability

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, and no conflicting worker container is already running on the same subsystem artifacts.

Check acceptance criteria and composition state before launching:

- **Unsatisfiable post-exit criteria**: If any criterion demands an external post-exit act outside the container's scope that neither `/ida:supervise` nor `/ida:pull` can produce and verify before releasing `done` (independent review, PR merge, host deployment, user approval), halt dispatch for that task and report its ID and unreachable criterion for task repair.
- **Supervised (`/ida:supervise <task-id>`)**: Satisfiable tasks lacking `## Instructions` + `## Appendix: Sources` (and not `invoke /<skill>`), or composite/multi-stage tasks requiring supervision or fan-out.
- **Leaf (`/ida:pull <task-id>`)**: Satisfiable single-skill directives (`invoke /<skill>`) or reified atomic leaf tasks (`## Instructions` + `## Appendix: Sources`).

## 2. Launch Containers

Launch one isolated worker container per ready task in parallel via the project's dispatch pathway:

- Supervised tasks: launch lead executor (`james`) calibrated to task complexity with `/ida:supervise <task-id>`.
- Reified leaf or single-skill tasks: launch worker container with `/ida:pull <task-id>`.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Output one line per dispatched task (title, ID, selected command `/ida:supervise` or `/ida:pull`, launched) and end your turn immediately. Never wait for container completion, block on event streams, or poll with timers or sleep loops.

## 4. Act on Completed Containers (Separate Turn)

When invoked in a later turn on container completion (`status`, `completion_evidence`, `pr_url` on the PKB task):

- `done` (`exit_code=0`): Check the report per `ida:premise-check`, dispatch newly unblocked `needs` tasks, and trigger `/verify` or `/reconcile` as needed.
- `partial` or `failed` (`exit_code!=0`): Inspect the recorded failure reason and logs; route follow-ups on the graph or escalate per fail-fast.
