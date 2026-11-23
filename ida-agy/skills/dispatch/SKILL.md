---
name: dispatch
description: Start isolated worker containers on queued repo-scoped tasks or ready leaf tasks without rewriting them, stamping origin ownership on dispatch, and pull unhandled worker completions on a timer. Use for headless worker container dispatch and periodic completion sweeps. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch -- Dispatch Worker Containers & Pull Completions

The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them. Use the task pipeline for durable deliverables (workflows, instructions, specifications, code); answer questions and lookups in-turn without queueing or dispatching containers.

Dispatched worker containers operate in two modes:

- **Supervised container (`/ida:supervise <task-id>`)**: Default for repo-scoped tasks queued by `/q`, un-reified multi-stage tasks, or composite tasks needing coordination and fan-out. Launches the lead executor (`james`) calibrated by complexity tier; runs `/reify` in session if un-reified and leaves follow-ups only for out-of-session work.
- **Leaf container (`/ida:pull <task-id>`)**: Fast-path execution for already-decomposed leaf tasks or single-skill directives without re-reifying, strictly state-only on the claimed task.

## 1. Verify Readiness & Satisfiability

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, and no worker container is already running on the same task ID. If an unlinked task covers overlapping subsystem artifacts, start the handed worker and send the overlap to the supervisor as a clarification.

Check acceptance criteria and composition state before choosing a command, and start a worker on the handed task unless a constitutional halt binds (`closure`, `data-boundaries`, or `exercise-authority` Exceptions 1-4):

- **Gap or external post-exit criteria**: If a criterion appears unreachable before releasing `done` (independent review, PR merge, host deployment, user approval) or the task has a gap outside those constitutional halts, start the worker on the handed task and send the gap to the supervisor as a clarification -- never decline handed work.
- **Supervised (`/ida:supervise <task-id>`)**: Tasks lacking `## Instructions` + `## Appendix: Sources` (and not `invoke /<skill>`), or composite/multi-stage tasks requiring supervision or fan-out.
- **Leaf (`/ida:pull <task-id>`)**: Single-skill directives (`invoke /<skill>`) or reified atomic leaf tasks (`## Instructions` + `## Appendix: Sources`).

## 2. Stamp Origin & Launch Containers

Stamp `origin_agent` on each ready PKB task (`pkb_update_task`) with the originating coordinator's stable handle before launching its container so returning work routes back to its owner without a completion race.

Launch one isolated worker container per ready task in parallel via the project's dispatch pathway:

- Supervised tasks: launch lead executor (`james`) calibrated to task complexity with `/ida:supervise <task-id>`.
- Reified leaf or single-skill tasks: launch worker container with `/ida:pull <task-id>`.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Report each dispatched task (title, ID, selected command `/ida:supervise` or `/ida:pull`, launched) as atomic sourced premises in a compact prose Argdown block per `ida:premise-check` and end your turn immediately. Never wait for container completion, block on event streams, or spin in shell polling or `sleep` loops; completed returns are picked up asynchronously on a periodic timer (Section 4).

## 4. Pull and Handle Completed Tasks (Timer Sweep)

On a periodic timer (separate from the dispatch turn), pull unhandled worker completions from the PKB:

`pkb_list_tasks(status="done,partial,failed,cancelled", unhandled=true, sort="released_at_desc", limit=25)`

Apply ownership and adoption rules to each returned task before acting:

- **Own completions** (`origin_agent` matches this agent): handle immediately.
- **Ad-hoc completions** (blank or unset `origin_agent`): adopt and handle immediately.
- **Other agents' completions** (`origin_agent` names another agent): leave untouched during a 20-30 minute grace window after `released_at` so the owner can pick up its own return; adopt and handle once that grace window has elapsed with the task still unhandled.

Act on each eligible completion according to its recorded PKB state (`status`, `completion_evidence`, `pr_url`, `reason`, `## Report`):

- `done`: Evaluate the report on the face of the record per `ida:premise-check` (zero _de novo_ fact-checking), advance or report the outcome, dispatch newly unblocked `needs` tasks, and trigger `/verify` or `/reconcile` as needed.
- `partial` or `failed`: Inspect the recorded failure reason and report/logs; route follow-ups on the graph or escalate per fail-fast.
- `cancelled`: Confirm the recorded cancellation reason and update affected downstream dependents or user threads as needed.

Stamp `handled_at` (UTC ISO-8601 timestamp) and `handled_by` (this agent's handle) via `pkb_update_task` only after moving the return along (reported, routed, or closed out) so subsequent sweeps skip handled items without dropping returns still waiting on an owner's grace window or follow-up action.
