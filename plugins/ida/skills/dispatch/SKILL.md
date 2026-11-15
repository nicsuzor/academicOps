---
name: dispatch
description: Start isolated polecat containers on queued repo-scoped epic tasks (/ida:supervise) or ready leaf tasks (/ida:pull) via detached polecat_run_container dispatch, with a provisional gated path for synchronous run_sync container calls when exposed by live MCP tool discovery. Exclude for intake placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch: Launch Isolated Polecat Containers

A polecat is an isolated container session: it gets in, executes its task, and gets out cleanly. The task or prompt is the whole contract to the container. Answer plain questions and lookups answerable in-turn directly in-session without launching a container.

- **Detached Task Dispatch (`polecat_run_container` -- Primary Default)**: Production-verified default for durable queued graph deliverables:
  - **Repo-scoped epic tasks (`/ida:supervise <task-id>`)**: Container coordinator enriches via `/reify` in-session, fans out subagents, and files graph follow-ups only for out-of-session work.
  - **Decomposed leaf tasks (`/ida:pull <task-id>`)**: Worker executes directly and mutates only its claimed task's state.
- **Provisional Synchronous Dispatch (`run_sync`, gated on live MCP tool discovery)**: Provisional until [`specs/polecat/return-channels.md`](../../../../specs/polecat/return-channels.md) leaves `draft`. Available **only when live MCP tool discovery exposes `run_sync` or `polecat_run_sync`**. When a caller explicitly requests synchronous execution while live tool discovery does not expose `run_sync` / `polecat_run_sync`, **halt loudly and report the missing tool verbatim** -- never silently fall back to detached `polecat_run_container`. When exposed, scope synchronous calls strictly to bounded isolated container checks or multi-turn container continuation (`keep_session` / `session_id`), taking all parameters and timeout ceilings directly from the live tool schema.

## 1. Check Preconditions Before Launch

- **Detached tasks (`polecat_run_container`)**: Verify `status: queued`, explicit acceptance criteria on the PKB task, no open `needs` prerequisite blocking execution, and no overlapping container running on the same repository artifacts. Dispatch repo-scoped epics queued by `/q` directly to `/ida:supervise <task-id>` without pre-dispatch `/reify`, and already-decomposed leaf tasks to `/ida:pull <task-id>`.
- **Provisional synchronous turns (`run_sync`, only when live-exposed)**: Supply Turn 1 and Turn 2+ parameters (`session_id` continuation on existing workspace state without conflicting overrides) strictly according to the live MCP tool schema.

## 2. Launch the Container

- **Detached dispatch (`polecat_run_container`)**: Launch one detached container per ready task in parallel with `/ida:supervise <task-id>` (epics) or `/ida:pull <task-id>` (leaf tasks). Never wait for or report asynchronous container starts; halt and report verbatim on any dispatch error.
- **Provisional synchronous dispatch (`run_sync`, when live-exposed)**: Invoke the synchronous MCP call once and receive the inline result and session continuation metadata without status polling or detached queue overhead.

## 3. Report and Stop (Fire-and-Forget for Detached Runs)

- **Detached dispatch**: Output one line per task (title, id, selected command, and launch/queue outcome) and end your turn immediately. Never call or block on the `polecat_polecat_events` feed tool, status checks, sleep loops, or timers waiting for completion.
- **Provisional synchronous `run_sync`**: Use or surface the returned response directly, retaining `session_id` only while follow-up turns remain within the returned expiry window.

## 4. Act on a Completed Detached Container (Separate Turn)

Detached containers emit lifecycle telemetry to the `polecat_events` feed and record deliverables (`status`, `completion_evidence`, `pr_url`) on the PKB task graph:

- **`done` (`exit_code=0`)**: Verify the `## Report` per `premise-check`, advance downstream tasks whose `needs` prerequisites cleared, and trigger `/verify` or `/reconcile`.
- **`partial` or `failed` (`exit_code!=0`)**: Inspect task `reason` and container logs; route remaining work via the graph engine or halt per fail-fast.
