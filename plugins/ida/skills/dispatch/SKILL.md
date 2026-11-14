---
name: dispatch
description: Start isolated polecat containers via synchronous run_sync MCP calls or detached polecat_run_container dispatch on queued graph tasks. Use for bounded synchronous container prompts (keep_session / session_id continuation) or fire-and-forget epic (/ida:supervise) and leaf (/ida:pull) execution. Exclude for intake placement (use /q) or interactive queue selection (use /dispatch-queue).
---

# /dispatch: Choose Container Return Channel and Launch

The task or prompt is the whole contract to the container. Answer plain in-session questions and lookups directly without launching a container; for isolated execution, pick the return channel from live MCP tool exposure, duration, and state durability (`specs/polecat/return-channels.md`):

- **Path 1 -- Synchronous MCP Dispatch (`run_sync`, with optional `keep_session`)**: Available **only when live MCP tool discovery (`portal_codemode_search`) exposes `polecat_run_sync` or `run_sync` alongside configured `runner` profiles**. When a caller explicitly requests synchronous `run_sync` while the live server does not expose it, **halt loudly and report the missing tool verbatim** -- never silently fall back to detached `polecat_run_container`. When exposed, use Path 1 for bounded single-turn questions/checks or interactive multi-turn follow-ups within the sync deadline (hard ceiling `85`s; omit `sync_timeout_s` to adopt the server default), receiving `status`, `response`, and `session_id` inline (`0` entries emitted to `polecat_events`). Set `keep_session: true` only when follow-up turns reuse the stopped volume via returned `session_id` before idle TTL expiry.
- **Path 2 -- Detached Task Dispatch (`polecat_run_container`)**: Default for durable queued graph deliverables (and for general isolated tasks while Path 1 is unexposed):
  - **Repo-scoped epic tasks (`/ida:supervise <task-id>`)**: Container coordinator enriches via `/reify` in-session, fans out subagents, and files graph follow-ups only for out-of-session work.
  - **Decomposed leaf tasks (`/ida:pull <task-id>`)**: Worker executes directly and mutates only its claimed task's state.

## 1. Check Preconditions Before Launch

- **Detached tasks**: Verify `status: queued`, explicit acceptance criteria on the PKB task, no open `needs` prerequisite blocking execution, and no overlapping container running on the same repository artifacts. Dispatch repo-scoped epics queued by `/q` directly to `/ida:supervise <task-id>` without pre-dispatch `/reify`, and already-decomposed leaf tasks to `/ida:pull <task-id>`.
- **Synchronous turns** (only when Path 1 is live-exposed): Omit `session_id` on Turn 1 (provide `repo`, `prompt`, `runner`, optional `branch`, optional `keep_session`, optional `sync_timeout_s`); supply exact returned `session_id` on Turn 2+ without conflicting `branch`, `repo`, or `runner`.

## 2. Launch the Container

- **Path 1 (`run_sync`, when live-exposed)**: Invoke the synchronous MCP call once; receive `status`, `response`/`error`, `session_id`, `resumable`, and `expires_at` inline without status polling or detached queue overhead.
- **Path 2 (`polecat_run_container`)**: Launch one detached container per ready task in parallel with `/ida:supervise <task-id>` (epics) or `/ida:pull <task-id>` (leaf tasks). Never wait for or report asynchronous container starts; halt and report verbatim on any dispatch error.

## 3. Report and Stop (Fire-and-Forget for Detached Runs)

- **Detached dispatch**: Output one line per task (title, id, selected command, and launch/queue outcome) and end your turn immediately. Never call or block on the `polecat_polecat_events` feed tool, status checks, sleep loops, or timers waiting for completion.
- **Synchronous `run_sync`**: Use or surface the returned `response` directly, retaining `session_id` only while follow-up turns remain within `expires_at`.

## 4. Act on a Completed Detached Container (Separate Turn)

Detached containers emit lifecycle telemetry to the `polecat_events` feed and record deliverables (`status`, `completion_evidence`, `pr_url`) on the PKB task graph:

- **`done` (`exit_code=0`)**: Verify the `## Report` per `premise-check`, advance downstream tasks whose `needs` prerequisites cleared, and trigger `/verify` or `/reconcile`.
- **`partial` or `failed` (`exit_code!=0`)**: Inspect task `reason` and container logs; route remaining work via the graph engine or halt per fail-fast.
