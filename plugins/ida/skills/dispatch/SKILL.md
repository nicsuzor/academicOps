---
name: dispatch
description: Start isolated polecat containers via synchronous run_sync MCP calls or detached polecat_run_container dispatch on queued graph tasks. Use for bounded synchronous container prompts (keep_session / session_id continuation) or fire-and-forget epic (/ida:supervise) and leaf (/ida:pull) execution. Exclude for intake placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch: Choose Container Return Channel and Launch

The task or prompt is the whole contract to the container. Answer plain in-session questions and lookups directly without launching a container; for isolated execution, pick the return channel from duration and state durability (`specs/polecat/return-channels.md`):

- **Path 1 -- Synchronous MCP Dispatch (`run_sync`, with optional `keep_session`)**: Use for short, bounded single-turn questions/checks or interactive multi-turn follow-ups within the configured sync deadline (hard ceiling `85`s; omit `sync_timeout_s` to use server default). Returns `status`, `response`, and `session_id` in one tool call (`0` entries emitted to `polecat_events`). Set `keep_session: true` when follow-up turns reuse the stopped volume via returned `session_id` before idle TTL expiry (fails closed if missing, expired, or conflicting).
- **Path 2 -- Detached Task Dispatch (`polecat_run_container`)**: Use for durable queued graph deliverables:
  - **Repo-scoped epic tasks (`/ida:supervise <task-id>`)**: Container coordinator enriches via `/reify`, fans out subagents, and files graph follow-ups only for out-of-session work.
  - **Decomposed leaf tasks (`/ida:pull <task-id>`)**: Worker executes directly and mutates only its claimed task's state.

## 1. Check Preconditions Before Launch

- **Detached tasks**: Verify `status: queued`, explicit acceptance criteria on the PKB task, no open `needs` prerequisite blocking execution, and no overlapping container running on the same repository artifacts. Send underspecified tasks to `/reify`.
- **Synchronous turns**: Omit `session_id` on Turn 1 (provide `repo`, `prompt`, `runner`, optional `branch`, optional `sync_timeout_s`); supply exact returned `session_id` on Turn 2+ without conflicting `branch`, `repo`, or `runner`.

## 2. Launch the Container

- **Path 1 (`run_sync`)**: Invoke the synchronous MCP call once; receive `status`, `response`/`error`, `session_id`, `resumable`, and `expires_at` inline without status polling or detached queue overhead.
- **Path 2 (`polecat_run_container`)**: Launch one detached container per ready task in parallel with `/ida:supervise <task-id>` (epics) or `/ida:pull <task-id>` (leaf tasks). Never wait for or report asynchronous container starts; halt and report verbatim on any dispatch error.

## 3. Report and Stop (Fire-and-Forget for Detached Runs)

- **Detached dispatch**: Output one line per task (title, id, selected command, and launch/queue outcome) and end your turn immediately. Never call or block on `polecat_polecat_events`, status checks, sleep loops, or timers waiting for completion.
- **Synchronous `run_sync`**: Use or surface the returned `response` directly, retaining `session_id` only while follow-up turns remain within `expires_at`.

## 4. Act on a Completed Detached Container (Separate Turn)

Detached containers emit lifecycle telemetry to `polecat_events` (draining to `/api/daemon/instances/:instance/events`) and record deliverables (`status`, `completion_evidence`, `pr_url`) on the PKB task graph:

- **`done` (`exit_code=0`)**: Verify the `## Report` per `premise-check`, advance downstream tasks whose `needs` prerequisites cleared, and trigger `/verify` or `/reconcile`.
- **`partial` or `failed` (`exit_code!=0`)**: Inspect task `reason` and container logs; route remaining work via the graph engine or halt per fail-fast.
