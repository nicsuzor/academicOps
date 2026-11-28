---
name: dispatch
description: Start isolated worker containers on queued tasks without rewriting them when the composed workflow routes work to a polecat container. Use for headless worker container dispatch. Exclude for task intake, placement, or interactive queue selection.
---

# /dispatch -- Dispatch Worker Containers

The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them when the composed workflow routes work here.

Every dispatched worker container receives the full task as its prompt. The container has no plugins and claims nothing or writes task status itself; as each container is reaped, the polecat service records completion and outputs where configured by the workflow and dispatch service.

## 1. Verify Readiness & Satisfiability

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, no worker container is already running on the same task ID, and its body carries composed `## Instructions` prepared by the composed workflow so the worker can complete it from the prompt and its one repository alone. Request missing composed instructions from the caller as a clarification. If an unlinked task covers overlapping subsystem artifacts, start the handed worker and report the overlap to the caller as a clarification.

Start a worker on the handed task unless a constitutional halt binds (`closure`, `data-boundaries`, or `exercise-authority` Exceptions 1-4):

- **Gap or external post-exit criteria**: If a criterion appears unreachable before releasing `done` (independent review, PR merge, host deployment, user approval) or the task has a gap outside those constitutional halts, start the worker on the handed task and send the gap to the caller as a clarification -- never decline handed work.

## 2. Launch Containers

Apply any ownership or return-routing fields specified by the composed workflow before launching containers; the composed workflow decides how completed work routes.

Launch one isolated worker container per ready task in parallel via `polecat_run_container`, passing `task_id`, `repo`, `dispatcher`, and the deployment's required `environment` settings only (omit `image` unless overriding the server default; the polecat service seeds the worker's prompt with the full task). Never pass `command` or a custom prompt, even if exposed by the tool schema; custom prompts are allowed only in crew containers launched manually by the user.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Report each dispatched task (title, ID, launched) and end your turn immediately. Never wait for container completion, block on event streams, or spin in shell polling or `sleep` loops; the polecat service records each completed task where configured by the workflow and dispatch service, and this skill runs no completion sweep.
