---
name: dispatch
description: Launch isolated polecat worker containers fire-and-forget on queued repo-scoped tasks or ready leaf tasks without rewriting them; owned exclusively by Sara. Use for headless polecat container dispatch. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch -- Launch Polecat Workers Fire-and-Forget

The headless dispatcher (`sara`) owns this skill; other agents delegate polecat dispatch to `sara` rather than launching containers directly. The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them.

Dispatched polecat containers run fire-and-forget in exactly two modes, chosen by task complexity:

- **Supervised polecat (`/ida:supervise <task-id>`)**: Complex, composite, multi-stage, or un-reified tasks requiring coordination, workflow composition (`/reify`), or subagent fan-out under `james`.
- **Leaf polecat (`/ida:pull <task-id>`)**: Atomic, already-decomposed leaf tasks or single-skill directives executed straight to completion without re-reifying, strictly state-only on the claimed task.

## 1. Verify Readiness & Select Mode

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, and no worker container is already running on the same task ID. If an unlinked task covers overlapping subsystem artifacts, start the handed worker and send the overlap to the supervisor as a clarification.

Select mode and start a worker on the handed task unless a constitutional halt binds (`closure`, `data-boundaries`, or `exercise-authority` Exceptions 1-4):

- **Gap or external post-exit criteria**: If a criterion appears unreachable before releasing `done` (independent review, PR merge, host deployment, user approval) or the task has a gap outside those constitutional halts, start the worker on the handed task and send the gap to the supervisor as a clarification -- never decline handed work.
- **Supervised (`/ida:supervise <task-id>`)**: Tasks lacking `## Instructions` + `## Appendix: Sources` (and not `invoke /<skill>`), or composite/multi-stage tasks requiring supervision or fan-out.
- **Leaf (`/ida:pull <task-id>`)**: Single-skill directives (`invoke /<skill>`) or reified atomic leaf tasks (`## Instructions` + `## Appendix: Sources`).

## 2. Select Model & Launch Fire-and-Forget

Select a suitable model calibrated to task complexity on every polecat launch, **defaulting to the `fast` tier** and escalating to `mid-tier` or `flagship` only when multi-constraint synthesis, architecture, or complex supervision demands it. Name the concrete model explicitly at polecat launch (never omit it or rely on server defaults).

Launch one isolated worker container per ready task in parallel via the project's polecat dispatch pathway:

- Supervised tasks: launch polecat with `/ida:supervise <task-id>` and calibrated model.
- Leaf or single-skill tasks: launch polecat with `/ida:pull <task-id>` and calibrated model.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Output one line per dispatched task (title, ID, selected command `/ida:supervise` or `/ida:pull`, selected model, launched) and end your turn immediately. Never wait for container completion, block on event streams, or poll with timers or sleep loops.

## 4. Act on Completed Containers (Separate Turn)

When invoked in a later turn on container completion (`status`, `completion_evidence`, `pr_url` on the PKB task):

- `done` (`exit_code=0`): Evaluate the report on the face of the record per `ida:premise-check` (zero _de novo_ fact-checking), dispatch newly unblocked `needs` tasks, and trigger `/verify` or `/reconcile` as needed.
- `partial` or `failed` (`exit_code!=0`): Inspect the recorded failure reason and logs; route follow-ups on the graph or escalate per fail-fast.
