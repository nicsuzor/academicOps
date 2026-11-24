---
name: dispatch
description: Start isolated worker containers on queued tasks via /crew:pull without rewriting them, stamping origin ownership on dispatch, and pull unhandled worker completions on a timer. Use for headless worker container dispatch and periodic completion sweeps. Exclude for intake and task placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch -- Dispatch Worker Containers & Pull Completions

The task record is the whole message to the isolated worker container; dispatch ready tasks without rewriting them. Use the task pipeline for durable deliverables (workflows, instructions, specifications, code); answer questions and lookups in-turn without queueing or dispatching containers.

Every dispatched worker container runs `/crew:pull <task_id>` against the task record.

## 1. Verify Readiness & Satisfiability

Read each named task (or ready children of a parent container). A task is ready when `status: queued`, no open `needs` dependencies remain, and no worker container is already running on the same task ID. If an unlinked task covers overlapping subsystem artifacts, start the handed worker and send the overlap to the supervisor as a clarification.

Start a worker on the handed task unless a constitutional halt binds (`closure`, `data-boundaries`, or `exercise-authority` Exceptions 1-4):

- **Gap or external post-exit criteria**: If a criterion appears unreachable before releasing `done` (independent review, PR merge, host deployment, user approval) or the task has a gap outside those constitutional halts, start the worker on the handed task and send the gap to the supervisor as a clarification -- never decline handed work.

## 2. Stamp Origin & Launch Containers

Stamp `origin_agent` on each ready PKB task (`pkb_update_task`) with the originating coordinator's stable handle before launching its container so returning work routes back to its owner without a completion race.

Launch one isolated worker container per ready task in parallel via `polecat_run_container`, passing `task_id`, `repo`, `image`, and `dispatcher` only (which runs `/crew:pull <task_id>`). Never pass `command` or a custom prompt, even if exposed by the tool schema; custom prompts are allowed only in crew containers launched manually by the user.

Containers start asynchronously; assume execution proceeds unless an immediate launch error returns (on failure, halt and report task ID and error verbatim).

## 3. Report and Stop (Fire-and-Forget)

Report each dispatched task (title, ID, `/crew:pull <task_id>`, launched) as atomic sourced premises in a compact prose Argdown block per `ida:premise-check` and end your turn immediately. Never wait for container completion, block on event streams, or spin in shell polling or `sleep` loops; completed returns are picked up asynchronously on a periodic timer (Section 4).

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
