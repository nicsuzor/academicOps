---
id: spec-silent-failure-detection
title: "Polecat Silent Failure Detection: Launch Preflight & Exit Guarantees"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, failure-detection, auth, task-guard, observability]
---

# Polecat Silent Failure Detection: Launch Preflight & Exit Guarantees

Polecat worker containers execute headlessly with `detach=True` and `auto_remove=True` (`docker run -d --rm`), so a worker that fails to authenticate at startup, crashes before claiming its task, or exits while the PKB MCP transport is degraded vanishes without surfacing an error unless launch preflight, exit-time task guarding, durable exit-record harvesting, and reconciliation checks are enforced across every lifecycle boundary.

## User stories

### US-1 Fail-fast credential preflight at launch and container boot

As a dispatching supervisor, I want polecat launch and container boot to verify target-client authentication and writable credential storage before starting the agent CLI, so that an unauthenticated or read-only credential mount fails immediately with a recorded error rather than starting a headless worker that cannot authenticate or persist refreshed OAuth tokens.

- **AC-1.1** Given a polecat launch on either the MCP server route or the host launcher route, when host credentials are synced into the credential volume, then the launcher verifies that the target client's credential payload is non-empty and raises an immediate launch error if synchronization or verification fails.
- **AC-1.2** Given a polecat worker container booting for `claude` or `agy`, when the required client credential (`CLAUDE_CODE_OAUTH_TOKEN` for `claude`, or Google OAuth credentials for `agy`) is absent or empty, then the entrypoint aborts with exit code `1` before invoking the agent CLI.
- **AC-1.3** Given a polecat worker container mounting host credentials read-only at `/home/nic/.creds:ro`, when the entrypoint stages `antigravity-oauth-token` and `oauth_creds.json` for `agy`, then it copies them as writable files (`0600`) into `$HOME/.gemini/` rather than symlinking into the read-only mount, so silent OAuth token refresh writes succeed without `read-only file system` errors.

### US-2 Post-launch startup liveness and claim verification

As a dispatching supervisor, I want container dispatch to verify that a newly started worker survives its initial boot and claims its assigned task within the startup grace window, so that a container that exits during startup or drops its `/ida:pull` seed prompt is detected immediately rather than disappearing under `auto_remove=True`.

- **AC-2.1** Given a detached container launch for a target task, when the startup grace window elapses, then the launcher or healthcheck verifies that the container has not exited prematurely and that the target task has transitioned out of `queued` (or that an active session transcript has been created), surfacing a launch failure if the container died or failed to claim its task.

### US-3 Resilient exit-time task guard and durable run record

As a framework operator, I want the container entrypoint to trap all exit signals, retry PKB task-guard operations across transient MCP transport errors, handle unclaimed (`queued`) and error states on exit, and write a durable `run.json` and `console.log` to the harvested session directory before container removal, so that no worker exit leaves a task silently stranded in `in_progress` or `queued` without an auditable exit record.

- **AC-3.1** Given a running polecat worker container with a `TARGET_TASK`, when the agent CLI exits (with code `0` or non-zero) or the container receives `SIGTERM`/`SIGINT`, then an `EXIT`/`TERM`/`INT` trap executes the post-run task guard and session log harvest before container termination.
- **AC-3.2** Given the post-run task guard inspecting `TARGET_TASK` on worker exit, when the `services` MCP server returns a transient transport or HTTP `5xx` error, then the task guard retries with bounded exponential backoff before reporting an error.
- **AC-3.3** Given the post-run task guard inspecting `TARGET_TASK` on worker exit, when the task status is `in_progress`, `queued` (worker exited before claiming), or `error: ...` (MCP unreachable after retries), then the entrypoint forces a non-zero container exit code (`exit_code=1`), transitions `in_progress` or `queued` tasks to `partial` with the exit code and log path in `reason`, and writes the outcome to `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json` and `console.log`.
- **AC-3.4** Given multiple runs of the same `TARGET_TASK` on the same UTC date, when `harvest-session-logs.sh` copies transcripts and CLI logs to `/data/sessions/logs/<YYYYMMDD>/<task_id>/`, then it updates `transcript.jsonl`, `transcript_full.jsonl`, `cli.log`, `console.log`, and `run.json` to match the latest run while preserving session-UUID-prefixed files for every run.

### US-4 Immediate orphan detection on container exit and reconciliation

As a supervisory agent running reconciliation or monitoring dispatched workers, I want `in_progress` tasks assigned to polecat workers to be cross-checked against live running containers and container exit events, so that a worker whose container has already exited is detected immediately rather than waiting for a 24-hour staleness timeout.

- **AC-4.1** Given a task on the PKB graph with `status: in_progress` and a polecat/worker assignment, when reconciliation runs or a container exit event fires and no live container with label `task=<task_id>` is running, then the task is immediately transitioned to `partial` (or re-queued) with a pointer to `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json`, without waiting 24 hours.

---

## Forensic Analysis: Why Tonight's Runs (`2026-10-15`) Failed and Why the Framework Did Not Notice

### 1. Why the First Runs of `aops_6755f9bd` and `aops_af240b9e` Failed

Inspection of the harvested session logs under `/data/sessions/logs/20261015/aops_6755f9bd/` and `/data/sessions/logs/20261015/aops_af240b9e/` (mounted on `nicwin` at `/home/nic/src/sessions/logs/20261015/<task_id>/`) and Phoenix OpenTelemetry spans establishes that **neither run failed due to missing OAuth login or the `GeminiDir` startup error**. Instead, both runs authenticated, claimed their tasks, worked for 17–20 minutes, and failed at `/ida:dump` when the `services` MCP server (`https://mcp.suzor.com/mcp`) suffered a multi-minute `Internal Server Error` (`HTTP 500`/`502`) outage between `20:01:01Z` and `20:03:23Z`.

#### A. Why `cli.log` Looked Like an Authentication / `GeminiDir` Failure

Every `agy --print` container run in `polecat:latest` emits three misleading startup error/warning sequences in the first 2 seconds of `cli-*.log` before silent OAuth authentication succeeds:

1. **Background language-server cache warmers fire before `printmode.go` authenticates (`+0.3s`)**:
   - In `aops_6755f9bd` Run 1 (`/data/sessions/logs/20261015/aops_6755f9bd/cli-20261015_194458.log:6-7`):
     ```text
     W1015 19:44:58.842807      97 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
     E1015 19:44:58.842841      97 language_server_service.go:425] Failed to get user status: You are not logged into Antigravity.
     ```
   - In `aops_af240b9e` Run 1 (`/data/sessions/logs/20261015/aops_af240b9e/cli-20261015_194213.log:6-7`):
     ```text
     W1015 19:42:14.086109      90 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
     E1015 19:42:14.086153      90 language_server_service.go:425] Failed to get user status: You are not logged into Antigravity.
     ```
2. **Relative `GeminiDir ".gemini"` resolution error (`+0.35s`)**:
   - In `aops_6755f9bd` Run 1 (`/data/sessions/logs/20261015/aops_6755f9bd/cli-20261015_194458.log:85-87`):
     ```text
     I1015 19:44:58.910018       1 common.go:156] Launching CLI mode
     E1015 19:44:58.910042       1 launchsteps.go:86] Failed to resolve GeminiDir ".gemini": .gemini must be an absolute path: path is not absolute, falling back to default
     I1015 19:44:58.910091       1 common.go:178] CLI app data directory: /home/nic/.gemini/antigravity-cli
     ```
   - In `aops_af240b9e` Run 1 (`/data/sessions/logs/20261015/aops_af240b9e/cli-20261015_194213.log:85-87`):
     ```text
     I1015 19:42:14.129269       1 common.go:156] Launching CLI mode
     E1015 19:42:14.129297       1 launchsteps.go:86] Failed to resolve GeminiDir ".gemini": .gemini must be an absolute path: path is not absolute, falling back to default
     I1015 19:42:14.129315       1 common.go:178] CLI app data directory: /home/nic/.gemini/antigravity-cli
     ```
3. **Silent OAuth token refresh succeeds in memory, fails to persist to the read-only `/home/nic/.creds` symlink, and completes authentication (`+1.2s–4.0s`)**:
   - In `aops_6755f9bd` Run 1 (`/data/sessions/logs/20261015/aops_6755f9bd/cli-20261015_194458.log:159-180`):
     ```text
     I1015 19:44:59.808134       1 printmode.go:403] Print mode: not authenticated, trying silent auth
     I1015 19:44:59.808776     518 keyring.go:64] keyringAuth: loaded token, expiry=2026-10-15 23:49:09.329745581 +1000 +1000 expired=true
     I1015 19:45:00.255734     518 browser.go:265] token refreshed, new expiry=2026-10-15 20:44:59.255680963 +0000 UTC m=+3600.799114279
     W1015 19:45:00.255873     518 browser.go:267] Failed to save refreshed token: failed to write token to file: open /home/nic/.gemini/antigravity-cli/antigravity-oauth-token: read-only file system
     I1015 19:45:00.255901       1 auth.go:157] ChainedAuth: authenticated via keyring (effective: keyring)
     I1015 19:45:00.255919       1 server_oauth.go:209] OAuth: authenticated successfully as nic.suzor@gmail.com
     I1015 19:45:01.969422       1 printmode.go:405] Print mode: silent auth succeeded
     ```
   - In `aops_af240b9e` Run 1 (`/data/sessions/logs/20261015/aops_af240b9e/cli-20261015_194213.log:151-166`):
     ```text
     I1015 19:42:15.134265       1 printmode.go:403] Print mode: not authenticated, trying silent auth
     I1015 19:42:15.135562     431 keyring.go:64] keyringAuth: loaded token, expiry=2026-10-15 23:49:09.329745581 +1000 +1000 expired=true
     I1015 19:42:15.541944     431 browser.go:265] token refreshed, new expiry=2026-10-15 20:42:14.541925763 +0000 UTC m=+3600.816582680
     W1015 19:42:15.542067     431 browser.go:267] Failed to save refreshed token: failed to write token to file: open /home/nic/.gemini/antigravity-cli/antigravity-oauth-token: read-only file system
     I1015 19:42:15.542100       1 auth.go:157] ChainedAuth: authenticated via keyring (effective: keyring)
     I1015 19:42:15.542113       1 server_oauth.go:209] OAuth: authenticated successfully as nic.suzor@gmail.com
     I1015 19:42:18.172606       1 printmode.go:405] Print mode: silent auth succeeded
     ```

#### B. Actual Cause of Run 1 Failure for `aops_6755f9bd` (Session `6e614a26-8f71-4ae3-8e73-cb6c76840e8c`)

1. **Claim and Execution (`19:45:04Z–20:01:02Z`)**:
   - Conversation `6e614a26-8f71-4ae3-8e73-cb6c76840e8c` was created at `19:45:04.748064` (`cli-20261015_194458.log:197`), claimed `aops_6755f9bd` via `pkb_claim_task` at `19:46:03Z` (`/data/sessions/logs/20261015/aops_6755f9bd/6e614a26-8f71-4ae3-8e73-cb6c76840e8c_transcript.jsonl:16-17`, Phoenix span `561043` / `e6e0120723b1786d`), and completed its investigation across 154 steps.
2. **Repeated `services` MCP `Internal Server Error` During `/ida:dump` (`20:01:02Z–20:02:05Z`)**:
   - When the worker attempted to read/update `aops_6755f9bd` and release it, **7 consecutive MCP tool calls** failed with `calling "tools/call": rejected by transport: sending "tools/call": Internal Server Error` in `/data/sessions/logs/20261015/aops_6755f9bd/6e614a26-8f71-4ae3-8e73-cb6c76840e8c_transcript.jsonl`:
     - `6e614a26-8f71-4ae3-8e73-cb6c76840e8c_transcript.jsonl:156` (`step_index: 155`, `20:01:02Z`):
       ```json
       {"step_index":155,"source":"MODEL","type":"GENERIC","status":"ERROR","error":"calling \"tools/call\": rejected by transport: sending \"tools/call\": Internal Server Error","created_at":"2026-10-15T20:01:02Z","content":"Created At: 2026-10-15T20:01:02Z\nCompleted At: 2026-10-15T20:01:03Z\nEncountered error in step execution: calling \"tools/call\": rejected by transport: sending \"tools/call\": Internal Server Error"}
       ```
     - Identical `Internal Server Error` failures recurred at `line 159` (`step_index: 158`, `20:01:13Z`), `line 162` (`step_index: 161`, `20:01:24Z`), `line 165` (`step_index: 164`, `20:01:36Z`), `line 168` (`step_index: 167`, `20:01:46Z`), `line 171` (`step_index: 170`, `20:01:57Z`), and `line 173` (`step_index: 172`, `20:02:05Z`).
3. **Worker Halt and Unreleased Exit (`20:02:06Z–20:03:15Z`)**:
   - At `6e614a26-8f71-4ae3-8e73-cb6c76840e8c_transcript.jsonl:174` (`step_index: 173`, `20:02:06Z`), following `halt-on-failure`, the agent emitted its final handover text:
     ```text
     ### BLOCKED — `services` MCP Server Unreachable (`Internal Server Error`) ... Because the `services` MCP server is down, `pkb_update_body` and `pkb_release_task` cannot be executed from this session; `aops_6755f9bd` remains claimed (`in_progress`, `session_id: 6e614a26-8f71-4ae3-8e73-cb6c76840e8c`).
     ```
   - `agy` exited `0` at `20:03:10.297982` (`cli-20261015_194458.log:374-378`).
   - At `20:03:13.031238Z`, `/usr/local/bin/polecat-entrypoint.sh:357` ran `polecat-task-guard check aops_6755f9bd` (Phoenix `mcp.get_task` span `563013` / `05d00cb46fae2e0b`), but the subsequent `polecat-task-guard release` call hit the resumed `20:03:11Z–20:03:23Z` `Internal Server Error` spike on `mcp.suzor.com/mcp` (independently recorded in concurrent session `/data/sessions/logs/20261015/aops_1d5b58fa/6abc9d7b-6414-4983-b69b-4009d230f571_transcript.jsonl:109,111`). Because `polecat-entrypoint.sh:357,361` suppresses errors with `2>/dev/null || true` and `|| true`, the release failure was swallowed and `aops_6755f9bd` remained `in_progress`.

#### C. Actual Cause of Run 1 Failure for `aops_af240b9e` (Session `62dc8e5d-dea3-4324-924a-fcb56e9fe640`)

1. **Claim and Execution (`19:42:20Z–20:00:50Z`)**:
   - Conversation `62dc8e5d-dea3-4324-924a-fcb56e9fe640` was created at `19:42:20.362036` (`cli-20261015_194213.log:181`), claimed `aops_af240b9e` at `19:43:28Z` (`/data/sessions/logs/20261015/aops_af240b9e/62dc8e5d-dea3-4324-924a-fcb56e9fe640_transcript.jsonl:14-15`, Phoenix span `560695` / `70e4b492f75bb743`), hit an initial `Error: Server error: HTTP 502` at `19:57:01Z` (`line 142`), and filed GitHub issue `nicsuzor/academicOps#2935` at `20:00:50Z` (`lines 175-176`).
2. **Repeated `services` MCP `Internal Server Error` During `/ida:dump` (`20:01:01Z–20:02:06Z`)**:
   - When the worker attempted to update `aops_af240b9e` and release it as `done`, **6 consecutive MCP calls** to `services` failed with `Internal Server Error` in `/data/sessions/logs/20261015/aops_af240b9e/62dc8e5d-dea3-4324-924a-fcb56e9fe640_transcript.jsonl`:
     - `62dc8e5d-dea3-4324-924a-fcb56e9fe640_transcript.jsonl:178` (`step_index: 177`, `20:01:01Z`):
       ```json
       {"step_index":177,"source":"MODEL","type":"GENERIC","status":"ERROR","error":"calling \"tools/call\": rejected by transport: sending \"tools/call\": Internal Server Error","created_at":"2026-10-15T20:01:01Z","content":"Created At: 2026-10-15T20:01:01Z\nCompleted At: 2026-10-15T20:01:02Z\nEncountered error in step execution: calling \"tools/call\": rejected by transport: sending \"tools/call\": Internal Server Error"}
       ```
     - Identical `Internal Server Error` failures recurred at `line 180` (`step_index: 179`, `20:01:15Z`), `line 182` (`step_index: 181`, `20:01:26Z`), `line 184` (`step_index: 183`, `20:01:37Z`), `line 186` (`step_index: 185`, `20:01:47Z`, `calling "resources/list": rejected by transport: sending "resources/list": Internal Server Error`), and `line 190` (`step_index: 189`, `20:02:06Z`).
3. **Worker Halt and Task-Guard Release to `partial` (`20:02:08Z–20:03:10Z`)**:
   - At `62dc8e5d-dea3-4324-924a-fcb56e9fe640_transcript.jsonl:191` (`step_index: 190`, `20:02:08Z`), the agent halted per `halt-on-failure`, emitting `## Session Handover (/ida:dump — Halted on services MCP Infrastructure Failure)`, and `agy` exited `0` at `20:02:59.901027` (`cli-20261015_194213.log:365-369`).
   - `/usr/local/bin/polecat-entrypoint.sh:357-361` then invoked `/usr/local/bin/polecat-task-guard`, whose `check` (`20:03:06.436992Z`, Phoenix span `563007` / `a9099c3571ae522c`) and `release` (`20:03:10.469022Z`, Phoenix span `563010` / `2a1390378bcc9ddb`) landed during a 4-second recovery window on `mcp.suzor.com/mcp`, releasing `aops_af240b9e` as `partial` with `reason: "Headless polecat runner exited with task unreleased (academicOps#2847)"`.

---

### 2. Every Point Where Silent Failure Could Have Been Detected (with `file:line`)

The table below lists every lifecycle point across `nicsuzor/dotfiles` (`@bfe6b3d`, installed at `/usr/local/bin/` inside `polecat:latest`) and `nicsuzor/academicOps` (`@c3249656`) where a launch, authentication, runtime, or exit failure could have been detected, why it went unnoticed, and the exact check, execution surface, and alert target required by this design.

| # | Lifecycle Point & `file:line` | Why It Was Not Detected (Current Code) | Design Fix: Check, Where It Runs, and Who It Alerts |
| :--- | :--- | :--- | :--- |
| **1** | **Host Credential Sync (MCP & CLI Launch)**<br>- `nicsuzor/dotfiles`: `containers/nicwin/polecat-mcp/server.py:257-322` (`_sync_host_credentials`)<br>- `nicsuzor/dotfiles`: `scripts/polecat:296-304` | `server.py:257-267,316-317` catches `docker.errors.NotFound` and `Exception` and logs a message without raising; `scripts/polecat:296-304` appends `2>/dev/null \|\| true` to the `alpine` credential copy container. Neither verifies that `/creds/gemini/antigravity-oauth-token` or `oauth_creds.json` exists and is non-empty before starting the worker container. | - **Check**: Assert that the credential sync succeeded and that the required credential for the target client (`CLAUDE_CODE_OAUTH_TOKEN` for `claude`; non-empty `antigravity-oauth-token` or `oauth_creds.json` containing a `refresh_token` in `niccreds` for `agy`) is present before calling `containers.run` / `docker run`.<br>- **Where it runs**: `containers/nicwin/polecat-mcp/server.py:_sync_host_credentials()` and `scripts/polecat` on the host.<br>- **Who it alerts**: Returns an immediate MCP tool error (`RuntimeError`) from `polecat_run_container` to the calling dispatcher (Sara / Ida Prime) or exits `1` on stderr for a CLI caller before any container is created. |
| **2** | **Detached `auto_remove=True` Container Launch**<br>- `nicsuzor/dotfiles`: `containers/nicwin/polecat-mcp/server.py:114-143, 430-499` (`run_container`)<br>- `nicsuzor/academicOps`: `plugins/ida/skills/dispatch/SKILL.md:26-30` | `server.py:115,143,431` defaults to `detach=True, auto_remove=True`. Under `detach=True`, `_orig_containers_run` (`line 464`) returns immediately upon container creation (`lines 489-499`); `except docker.errors.ContainerError` (`lines 465-480`) never triggers for detached containers. When the container exits with `auto_remove=True`, Docker deletes the container and its `docker logs` immediately, while `dispatch/SKILL.md:26-30` instructs the dispatcher not to poll or wait. | - **Check**: After `containers.run(..., detach=True)`, wait a short startup window (e.g. `3s`) or inspect container state to confirm `container.status == "running"` and `State.ExitCode == 0`, and attach a background waiter / Docker `die` event listener that captures the exit code before removal (or disables `auto_remove` until `polecat-mcp` records the exit event).<br>- **Where it runs**: `containers/nicwin/polecat-mcp/server.py` (`run_container` and container-exit listener) on `nicwin`.<br>- **Who it alerts**: If the container exits during startup, `polecat_run_container` raises an immediate error to the dispatching agent (Sara / Ida Prime); on post-startup exit, the exit listener alerts the dispatcher or updates the PKB task record. |
| **3** | **Entrypoint Client Auth Validation & Writable Token Staging**<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-entrypoint.sh:211-244`<br>- `nicsuzor/dotfiles`: `containers/nicwin/polecat-mcp/server.py:378` (`niccreds:/home/nic/.creds:ro`) | 1. `/usr/local/bin/polecat-entrypoint.sh:211-213` only prints `polecat: WARNING: CLAUDE_CODE_OAUTH_TOKEN is not set — claude will not authenticate` instead of exiting `1`.<br>2. `/usr/local/bin/polecat-entrypoint.sh:242-244` only prints `polecat: WARNING: no host Google OAuth credentials in /home/nic/.creds/gemini — agy will not authenticate` instead of exiting `1`.<br>3. `/usr/local/bin/polecat-entrypoint.sh:219-224` symlinks (`ln -sfn`) `antigravity-oauth-token` and `oauth_creds.json` to `/home/nic/.creds/gemini/*`, which is mounted read-only (`server.py:378`), causing `agy` (`browser.go:267`) to fail with `open /home/nic/.gemini/antigravity-cli/antigravity-oauth-token: read-only file system` on every token refresh. | - **Check**: (a) Copy (`cp -f` + `chmod 600`) `antigravity-oauth-token` and `oauth_creds.json` from `/home/nic/.creds/gemini/` into `$HOME/.gemini/antigravity-cli/` and `$HOME/.gemini/` instead of symlinking to the read-only mount. (b) When `CMD_NAME` is `claude` and `CLAUDE_CODE_OAUTH_TOKEN` is unset (in worker mode), or when `CMD_NAME` is `agy` and neither `antigravity-oauth-token` nor `oauth_creds.json` is non-empty, abort with `exit 1` and record the fatal error via the exit trap.<br>- **Where it runs**: `/usr/local/bin/polecat-entrypoint.sh` inside the polecat container before executing `"$@"`.<br>- **Who it alerts**: Triggers the entrypoint `EXIT` trap (`polecat-task-guard` transitions `TARGET_TASK` to `partial` with reason `"Fatal auth preflight failure"` and writes `run.json`), alerting the dispatcher / reconciliation pass on the PKB graph and failing the container launch check. |
| **4** | **Entrypoint MCP Fallback Credentials**<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-entrypoint.sh:259-265`<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-task-guard:35-47` | `/usr/local/bin/polecat-entrypoint.sh:265` runs `unset PKB_MCP_TOKEN POLECAT_MCP_TOKEN` after running `mcp-services-config.sh`. If `~/.gemini/config/mcp_config.json` is absent or corrupted, `/usr/local/bin/polecat-task-guard:35-47` falls back to `CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET` (never set) instead of a valid bearer token. | - **Check**: Verify that `/usr/local/bin/mcp-services-config.sh` produced a readable `services` entry with non-empty `Authorization` header in `~/.gemini/config/mcp_config.json` and `$CLAUDE_CONFIG_DIR/.claude.json` before unsetting `PKB_MCP_TOKEN`/`POLECAT_MCP_TOKEN`, and halt with `exit 1` if missing.<br>- **Where it runs**: `/usr/local/bin/polecat-entrypoint.sh:259-265` inside the container.<br>- **Who it alerts**: Halts container startup via the `EXIT` trap, writing `run.json` and alerting the dispatcher (`polecat_run_container`). |
| **5** | **Container Healthcheck (`polecat-healthcheck`)**<br>- `nicsuzor/dotfiles`: `containers/nicwin/nicdev/Dockerfile:344`<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-healthcheck:89-175` | `/usr/local/bin/polecat-healthcheck:94-136` only checks whether `~/.gemini/antigravity-cli/log/cli-*.log` was modified within `300s`. It never checks whether `agy` logged a fatal auth failure, whether `claude` is the active runner, or whether `TARGET_TASK` was claimed (`in_progress`) after `startup_grace` (`60s`), and nothing on `nicwin` subscribes to `health_status: unhealthy` Docker events. | - **Check**: Extend `/usr/local/bin/polecat-healthcheck` so that after `startup_grace` (`60s`), it checks (a) client log/transcript activity for both `agy` and `claude`, (b) absence of unrecovered auth failure in `cli-*.log`, and (c) that an active conversation transcript exists in `brain/` or `~/.claude/projects/`.<br>- **Where it runs**: `/usr/local/bin/polecat-healthcheck` via Docker `HEALTHCHECK` every `30s` inside the container, polled by `polecat_list_containers` / Docker event monitor.<br>- **Who it alerts**: Marks the container `unhealthy` in Docker (`polecat_list_containers`), alerting Sara's check-in / the `polecat-mcp` health monitor to inspect or terminate the wedged container. |
| **6** | **Signal Trapping & Post-Run Task Guard (`polecat-task-guard`)**<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-entrypoint.sh:349-366`<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-task-guard:50-135` | 1. **No `trap`**: `/usr/local/bin/polecat-entrypoint.sh` has `0` `trap` statements; `SIGTERM`/`SIGINT` or an early `exit 1` skips lines `353-370` entirely.<br>2. **No MCP retry**: `/usr/local/bin/polecat-task-guard:69-80, 122-135` performs a single un-retried MCP call. When `mcp.suzor.com/mcp` returned `Internal Server Error` at `20:03:13Z`, `aops_6755f9bd`'s release failed.<br>3. **Error swallowing & unclaimed-task blindness**: `/usr/local/bin/polecat-entrypoint.sh:357-365` runs `final_status="$(python3 "$TASK_GUARD_SCRIPT" check "$TARGET_TASK" 2>/dev/null \|\| true)"` and only branches on `if [ "$final_status" = "in_progress" ]` with `release ... \|\| true`. If `final_status` is `"queued"` (worker died before claiming) or `"error: ..."` (MCP outage during `check`), or if `release` fails, the entrypoint silently exits `0`! | - **Check**: (a) Register `trap on_exit EXIT INT TERM` in `/usr/local/bin/polecat-entrypoint.sh` before launching the agent. (b) Add bounded exponential backoff (e.g. 4 attempts: `1s, 2s, 4s, 8s`) to `check_task` and `release_task` in `/usr/local/bin/polecat-task-guard`. (c) In `on_exit`, handle all non-terminal task states:<br>  - `final_status == "in_progress"`: release as `partial` with `exit_code` and session log path, set `exit_code=1`.<br>  - `final_status == "queued"`: worker failed before claiming `TARGET_TASK`; claim-and-release or transition `TARGET_TASK` to `partial` with `reason: "Polecat worker exited (code $exit_code) before claiming task"` and set `exit_code=1`.<br>  - `final_status == "error: ..."` or `release` returns non-zero: set `exit_code=1` and record `"task_guard_error": "$final_status"` in `run.json`.<br>- **Where it runs**: `/usr/local/bin/polecat-entrypoint.sh` (`on_exit` trap) and `/usr/local/bin/polecat-task-guard` inside the container on exit.<br>- **Who it alerts**: Updates the PKB task status to `partial` with the failure reason on the graph (alerting Sara, Pauli, and `/ida:reconcile`) and writes `task_guard_error` to `run.json` when the PKB MCP server is unreachable. |
| **7** | **Durable Exit Record (`run.json`), Console Stream, and Transcript Harvest**<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/polecat-entrypoint.sh:351, 368-370`<br>- `nicsuzor/dotfiles` / container `/usr/local/bin/harvest-session-logs.sh:39-61` | 1. `/usr/local/bin/polecat-entrypoint.sh:351` runs `"$@"` without teeing stdout/stderr to `/data/sessions/logs/<YYYYMMDD>/<task_id>/console.log`, so all entrypoint warnings/errors and stream-json output vanish when `auto_remove=True` removes the container.<br>2. Neither `polecat-entrypoint.sh` nor `harvest-session-logs.sh` writes `run.json` (container ID, timestamps, `agent_exit_code`, `final_task_status`, `task_guard_result`).<br>3. `/usr/local/bin/harvest-session-logs.sh:57-59` uses `if [ ! -f "$DEST_DIR/$base_name" ]`, leaving `transcript.jsonl` and `transcript_full.jsonl` pointing to Run 1 (`19:42Z`/`19:44Z`) while `cli.log` (`line 40`) is overwritten by Run 2 (`20:07Z`).<br>4. `harvest-session-logs.sh` only harvests `~/.gemini/antigravity-cli`, ignoring `~/.claude/projects/`. | - **Check**: (a) Tee container stdout/stderr to `/data/sessions/logs/<YYYYMMDD>/<task_id>/console.log` from entrypoint start. (b) In `harvest-session-logs.sh`, always overwrite the unprefixed `transcript.jsonl` and `transcript_full.jsonl` with the newest run's transcript (matching `cli.log`), harvest `~/.claude/projects/**/*.jsonl` when present, and write `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json` recording `container_id`, `task_id`, `started_at`, `finished_at`, `agent_exit_code`, `final_task_status`, and `task_guard_outcome`.<br>- **Where it runs**: `/usr/local/bin/polecat-entrypoint.sh` and `/usr/local/bin/harvest-session-logs.sh` writing to `/data/sessions/logs/<YYYYMMDD>/<task_id>/`.<br>- **Who it alerts**: Supervisory agents (Sara, Ida Prime, `/ida:reconcile`) and operators inspecting `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json` and `console.log`. |
| **8** | **Supervisory Reconciliation Cross-Check**<br>- `nicsuzor/academicOps`: `plugins/ida/skills/workflow-library/workflows/wf-reconcile.md:33`<br>- `nicsuzor/academicOps`: `specs/workflows/reconcile.md:48`<br>- `nicsuzor/academicOps`: `plugins/ida/agents/sara.md:15-21` | `wf-reconcile.md:33` states: `6. No orphans: Stale in_progress tasks with no live claim (>24h unmodified) reset to queued.` When `aops_6755f9bd`'s task guard failed during the `20:03:13Z` MCP outage, `aops_6755f9bd` remained `in_progress` with no running container; under the `>24h` rule, automated orphan recovery would ignore it for 24 hours unless a human or supervisor manually checked `polecat_list_containers`. | - **Check**: Cross-check all `in_progress` tasks assigned to `james` / `polecat` against active containers returned by `polecat_list_containers` (matching label `task=<task_id>`) and `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json`. If no container is running for an `in_progress` polecat task, treat the claim as dead immediately (0-minute wait after container exit), inspect `run.json` / harvested transcripts, and transition the task to `partial` or `queued`.<br>- **Where it runs**: `/ida:reconcile` (`wf-reconcile.md` Obligation 6) and Sara's supervision check-in.<br>- **Who it alerts**: Transitions the task on the PKB graph and surfaces the failed run in the reconciliation / supervision report to Sara or Ida Prime. |

---

## Design

### 1. Launch-Time Credential & Liveness Contract

1. **Fail-Closed Host Credential Sync (`polecat-mcp/server.py`, `scripts/polecat`)**:
   - Before starting a worker container, the launcher syncs credentials from the source container into `niccreds` and validates the target client's credential material:
     - For `agy`: `/creds/gemini/antigravity-oauth-token` or `/creds/gemini/oauth_creds.json` exists, is non-empty, and parses as JSON containing a non-empty token/refresh token.
     - For `claude`: `CLAUDE_CODE_OAUTH_TOKEN` (or `AOPS_CC_OAUTH_TOKEN`) is non-empty in the environment passed to the worker.
   - Any failure in credential sync or validation raises a fatal launch error immediately; errors are never swallowed with `|| true` or `logger.debug`.
2. **Entrypoint Auth Preflight & Writable Token Copy (`/usr/local/bin/polecat-entrypoint.sh`)**:
   - Instead of symlinking `antigravity-oauth-token` and `oauth_creds.json` to the read-only `/home/nic/.creds/gemini/` mount, `polecat-entrypoint.sh` copies them as regular writable files (`cp -f` + `chmod 0600`) into `$HOME/.gemini/antigravity-cli/antigravity-oauth-token` and `$HOME/.gemini/oauth_creds.json`. When `agy` refreshes an expired access token at startup (`browser.go:265`), it persists the refreshed token cleanly to the container filesystem.
   - After resolving `CMD_NAME` (`agy` or `claude`), `polecat-entrypoint.sh` enforces a fail-fast preflight check:
     - If `CMD_NAME == "claude"` (in worker mode, `CREW=0`) and `CLAUDE_CODE_OAUTH_TOKEN` is empty: print `FATAL: CLAUDE_CODE_OAUTH_TOKEN is not set` and `exit 1`.
     - If `CMD_NAME == "agy"` and both `$HOME/.gemini/antigravity-cli/antigravity-oauth-token` and `$HOME/.gemini/oauth_creds.json` are missing or empty (`! -s`): print `FATAL: no Google OAuth credentials staged for agy` and `exit 1`.
     - Verify that `/usr/local/bin/mcp-services-config.sh` wrote a valid `services` MCP entry before unsetting `PKB_MCP_TOKEN` and `POLECAT_MCP_TOKEN`.
3. **Post-Launch Startup Liveness Check (`polecat-mcp/server.py`)**:
   - When `polecat_run_container` starts a container with `detach=True`, it waits briefly (`2–3s`) and re-inspects the container (`container.reload()`). If the container has already exited (`status != "running"`), `polecat_run_container` reads `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json` (or `console.log`) and raises a `RuntimeError` containing the exit code and stderr output so the dispatching agent learns of the launch failure synchronously in the tool response.

### 2. Exit-Time Trap, Resilient Task Guard, and Durable Harvest Contract

1. **Mandatory Exit Trap (`/usr/local/bin/polecat-entrypoint.sh`)**:
   - Immediately after resolving `TARGET_TASK` and creating `/data/sessions/logs/<YYYYMMDD>/<task_id>/`, `polecat-entrypoint.sh` registers `trap on_exit EXIT INT TERM`.
   - All entrypoint and agent stdout/stderr is teed to `/data/sessions/logs/<YYYYMMDD>/<task_id>/console.log` (with URL/token redaction) so diagnostic output survives `auto_remove=True`.
2. **Task Guard with Retry & Complete State Coverage (`/usr/local/bin/polecat-task-guard`)**:
   - Both `check_task` and `release_task` wrap their `fastmcp.client.Client` calls in a retry loop with exponential backoff (`4` attempts over `1s, 2s, 4s, 8s`) on transport/5xx errors so a brief `services` MCP blip (such as the `20:03:11Z–20:03:23Z` window that stranded `aops_6755f9bd`) does not drop the task-guard release.
   - On container exit (`on_exit`), `polecat-entrypoint.sh` inspects `final_status` of `TARGET_TASK`:
     - **`done` / `review` / `partial` / `cancelled` / `failed`**: The worker released its own task cleanly; `task_guard_outcome="worker_released"`.
     - **`in_progress`**: The worker claimed the task but exited without releasing it. The task guard calls `release_task(TARGET_TASK, status="partial", reason=f"Headless polecat runner exited (code {exit_code}) with task still in_progress; logs: /data/sessions/logs/{date}/{TARGET_TASK}/")`, sets `exit_code=1`, and records `task_guard_outcome="guard_released_from_in_progress"`.
     - **`queued` / `ready`**: The worker container exited before `/ida:pull` even claimed `TARGET_TASK` (e.g. startup crash, auth failure, or dropped prompt). The task guard claims and immediately releases `TARGET_TASK` as `partial` (or updates `status="partial"` with `reason=f"Polecat worker exited (code {exit_code}) before claiming task; logs: /data/sessions/logs/{date}/{TARGET_TASK}/"`), sets `exit_code=1`, and records `task_guard_outcome="guard_released_from_queued"`.
     - **`error: ...` (or `release` failure after all retries)**: The PKB MCP server remained unreachable across all backoff retries. The entrypoint sets `exit_code=1` and writes `task_guard_outcome="mcp_unreachable"` with the verbatim error into `run.json`.
3. **Durable `run.json` and Latest-Run Transcript Harvest (`/usr/local/bin/harvest-session-logs.sh`)**:
   - `harvest-session-logs.sh` copies both `agy` logs/transcripts (`~/.gemini/antigravity-cli/{log,brain}`) and `claude` transcripts (`~/.claude/projects/`).
   - When writing unprefixed convenience files (`transcript.jsonl`, `transcript_full.jsonl`, `cli.log`), `harvest-session-logs.sh` always updates them to the most recent session's files while preserving `<session_uuid>_transcript.jsonl` and `cli-<timestamp>.log` for every run.
   - Finally, the exit handler writes `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json`:
     ```json
     {
       "schema_version": 1,
       "container_id": "<HOSTNAME>",
       "task_id": "<TARGET_TASK>",
       "client": "agy | claude",
       "started_at": "2026-10-15T19:44:58Z",
       "finished_at": "2026-10-15T20:03:15Z",
       "agent_exit_code": 0,
       "exit_code": 1,
       "final_task_status": "in_progress",
       "task_guard_outcome": "guard_released_from_in_progress | guard_released_from_queued | worker_released | mcp_unreachable",
       "task_guard_error": null
     }
     ```

### 3. Supervisory & Reconciliation Contract

1. **Zero-Wait Live Container Cross-Check (`wf-reconcile.md`)**:
   - During `/ida:reconcile` (Obligation 6) and supervisory check-ins, any PKB task with `status: in_progress` and `assignee: james` (or a `polecat/*` branch/tag) is cross-checked against `polecat_list_containers`.
   - If no running container carries label `task=<task_id>`, the task is immediately recognised as an exited polecat run (without waiting for the 24-hour staleness threshold). The reconciling agent reads `/data/sessions/logs/<YYYYMMDD>/<task_id>/run.json` and transitions the task to `partial` (recording the failure reason from `run.json`) or resets it to `queued` for re-dispatch.
