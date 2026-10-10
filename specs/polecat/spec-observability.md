---
id: polecat-observability
title: "Polecat Observability: Real-Time Monitoring Across Dispatch Surfaces"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, observability, telemetry, mcp, tmux, phoenix]
---

# Polecat Observability: Real-Time Monitoring Across Dispatch Surfaces

How an operator or supervisory agent observes a running polecat container in real time.
Umbrella architecture: [`polecat-system.md`](polecat-system.md); interactive driving: [`tmux-interactive-driving.md`](tmux-interactive-driving.md); operational debug guide: [`../../.agents/skills/debug/SKILL.md`](../../.agents/skills/debug/SKILL.md).

## Dispatch Surfaces & Observability Models

Polecat execution occurs over two distinct operational routes, each with different visibility characteristics and tooling:

| Attribute               | MCP Server Route (`polecat_run_container`)                     | Host Launcher Route (`scripts/polecat`)                           |
| :---------------------- | :------------------------------------------------------------- | :---------------------------------------------------------------- |
| **Execution model**     | Standalone detached Docker container (`detach=True`)           | Direct `docker run`, optionally wrapped in `tmux`                 |
| **Interactive TTY**     | No TTY / no tmux session                                       | Real TTY inside tmux with `-i`                                    |
| **Stdout/Stderr**       | Captured by Docker daemon (`docker logs -f` / `stream-json`)   | Attached to terminal or piped to host stdout                      |
| **Log stream tool**     | MCP `polecat_fetch_container_logs` / `docker logs -f`          | `tmux attach` / `tmux capture-pane` / session dir                 |
| **Host mount for logs** | `$AOPS_SESSIONS` mounted to `/data/sessions:rw` (auto)         | `$AOPS_SESSIONS` mounted to `/data/sessions:rw` (auto)            |
| **OTel / Phoenix**      | Forwarded via `nicwin_polecat_workers` network                 | Forwarded via host env allowlist                                  |

## 1. MCP Server Dispatch Route

When a task is dispatched programmatically through the Docker MCP server behind the `services` gateway (`polecat_run_container`):

### Container Lifecycle & No-Tmux Architecture

The MCP server invokes `docker.models.containers.ContainerCollection.run` with `detach=True`. **No tmux session is created.** Commands like `tmux attach` or `tmux capture-pane` do not apply.

### Real-Time Surfaces

1. **Container Log Streaming (`polecat_fetch_container_logs` / `docker logs -f`)**:
   - The MCP server exposes `polecat_fetch_container_logs(container_id="<id>", tail=100)`.
   - On the host, the equivalent stream is `docker logs -f <container_name_or_id>`.
   - **Real-Time Streaming (`agy`)**: `polecat-entrypoint.sh` automatically injects `--output-format stream-json` when `agy` runs non-interactively or with `--print` (unless an explicit `--output-format` is supplied). This ensures incremental NDJSON events (`init`, `step_update`, tool calls) stream continuously to stdout and the Docker daemon logs rather than buffering until turn completion.
2. **Persistent Session Logs & Transcripts (`harvest-session-logs.sh`)**:
   - Both `polecat-mcp` (`server.py`) and `scripts/polecat` automatically bind-mount the host sessions folder (`$AOPS_SESSIONS` or `$HOME/src/sessions`) to `/data/sessions:rw` with container environment `AOPS_SESSIONS=/data/sessions`.
   - On container exit (handled via bash traps in `polecat-entrypoint.sh`), `harvest-session-logs.sh` copies `~/.gemini/antigravity-cli/log/cli-*.log` and `~/.gemini/antigravity-cli/brain/**/transcript*.jsonl` to `/data/sessions/logs/<date>/<task_id>/`.
   - Diagnostic evidence survives container termination even when `auto_remove: true` cleans up the container.
3. **Authoritative OpenTelemetry Telemetry (Phoenix)**:
   - The MCP server attaches workers to the compose network (`nicwin_polecat_workers`) and forwards `GENAI_ENGINE_TRACE_ENDPOINT` via its environment allowlist.
   - Spans for LLM calls, tool executions, and subagent chains stream live over the network to Phoenix.
   - Active spans can be queried live using the `services` portal (`phoenix_execute` / `executeSql`) or inspected in the Phoenix web UI.
4. **Container State & Health (`polecat_list_containers`)**:
   - Query container state via `polecat_list_containers(filters={"id": "<short_id>"})` to inspect execution state (`running`, `exited`), health, and exit code.
5. **Task Graph State**:
   - The worker claims its assigned task in the PKB (`in_progress`) and releases it (`done` or `partial`; `review` only for a decision only the user can make) with verified delivery evidence.

## 2. Host Script Launcher Route

When an operator or supervisor launches a worker directly on the host using `scripts/polecat` (typically wrapped in a tmux session per `tmux-interactive-driving.md`):

### Live Interactive UI (tmux)

- **Attach to session**: `tmux attach -t <session_name>` lets an operator watch the terminal interface (TUI, prompt boxes, streaming tokens, interactive tools) live.
- **Capture pane buffer**: `tmux capture-pane -t <session_name> -p -S -2000` extracts scrollback into scripts or test harnesses without manual intervention.

### Logging Architecture & Persistence Boundaries

- `scripts/polecat` mounts `$WORKSPACE_DIR:/workspace`, credential stores (`niccreds`), and bind-mounts `$AOPS_SESSIONS:/data/sessions:rw` with container env `AOPS_SESSIONS=/data/sessions`.
- Entrypoint flags automatically enable real-time `--output-format stream-json` streaming for non-interactive `agy` invocations.
- Container-internal session files (`~/.claude/projects/`, `~/.gemini/antigravity-cli/brain/`) are harvested to `/data/sessions/logs/<date>/<task_id>/` upon container exit before the container is removed.
- Output written to stdout/stderr is captured in the Docker daemon log (`docker logs -f`).

### Telemetry (Phoenix)

Forwards the OpenTelemetry contract to Phoenix via `GENAI_ENGINE_TRACE_ENDPOINT` on network `nicwin_polecat_workers`. Tool calls, agent spans, and LLM completions stream live to Phoenix.

## Observability Matrix & Failure Signals

| Observation Need                       | MCP Route                                                                                | Host Launcher Route                                         |
| :------------------------------------- | :--------------------------------------------------------------------------------------- | :---------------------------------------------------------- |
| **Is the container alive?**            | `polecat_list_containers`                                                                | `tmux has-session -t <name>` / `docker ps`                  |
| **What is the agent printing?**        | `polecat_fetch_container_logs` (stream-json) or `docker exec` tailing agy log/transcript | `tmux capture-pane` or attached terminal                    |
| **Which tool is executing right now?** | Phoenix span store query (`executeSql`)                                                  | Phoenix span store query (`executeSql`)                     |
| **Why did the worker fail?**           | `polecat.exit_code` / `polecat_fetch_container_logs` / `$AOPS_SESSIONS/logs/<date>/<task_id>/` | Terminal text / `$AOPS_SESSIONS/logs/<date>/<task_id>/` / Phoenix trace |
