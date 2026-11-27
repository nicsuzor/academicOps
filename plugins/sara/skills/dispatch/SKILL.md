---
name: dispatch
description: Start isolated worker containers on queued, reified tasks without rewriting them, and stamping origin ownership on dispatch. Use for headless worker container dispatch. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch -- Dispatch Worker Containers

The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them. Use the task pipeline for durable deliverables (workflows, instructions, specifications, code); answer questions and lookups in-turn without queueing or dispatching containers.

Every dispatched worker container receives the full reified task as its prompt. The container has no plugins and no PKB access: the worker runs no `/pull`, `/reify`, or `/dump`, claims nothing, and writes no task status; as each container is reaped, the polecat service writes the completed task to the PKB.

## 1. Verify Readiness & Satisfiability

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, no worker container is already running on the same task ID, and the PKB custodian (`pauli`) has reified it (`/crew:reify`) just before this dispatch, so its body carries composed `## Instructions` the worker can complete from the prompt and its one repository alone. Send a task without composed instructions back to the supervisor as a clarification, for `pauli` to run `/crew:reify`. If an unlinked task covers overlapping subsystem artifacts, start the handed worker and send the overlap to the supervisor as a clarification.

Start a worker on the handed task unless a constitutional halt binds (`closure`, `data-boundaries`, or `exercise-authority` Exceptions 1-4):

- **Gap or external post-exit criteria**: If a criterion appears unreachable before releasing `done` (independent review, PR merge, host deployment, user approval) or the task has a gap outside those constitutional halts, start the worker on the handed task and send the gap to the supervisor as a clarification -- never decline handed work.

## 2. Stamp Origin & Launch Containers

Stamp `origin_agent` on each ready PKB task (`pkb_update_task`) with the originating coordinator's stable handle before launching its container so returning work routes back to its owner without a completion race.

Launch one isolated worker container per ready task in parallel via `polecat_run_container`, passing `task_id`, `repo`, `image`, and `dispatcher` only (the polecat service seeds the worker's prompt with the full task). Never pass `command` or a custom prompt, even if exposed by the tool schema; custom prompts are allowed only in crew containers launched manually by the user.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Report each dispatched task (title, ID, launched) as atomic sourced premises in a compact prose Argdown block per `ida:premise-check` and end your turn immediately. Never wait for container completion, block on event streams, or spin in shell polling or `sleep` loops; the polecat service writes each completed task to the PKB as its container is reaped, and this skill runs no completion sweep.
