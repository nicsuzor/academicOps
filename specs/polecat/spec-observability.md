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

| Attribute               | MCP Server Route (`polecat_run_container`)            | Host Launcher Route (`scripts/polecat`)           |
| :---------------------- | :---------------------------------------------------- | :------------------------------------------------ |
| **Execution model**     | Standalone detached Docker container (`detach=True`)  | Direct `docker run`, optionally wrapped in `tmux` |
| **Interactive TTY**     | No TTY / no tmux session                              | Real TTY inside tmux with `-i`                    |
| **Stdout/Stderr**       | Captured by Docker daemon / streamed via MCP          | Attached to terminal or piped to host stdout      |
| **Log stream tool**     | MCP `polecat_fetch_container_logs` / `docker logs -f` | `tmux attach` / `tmux capture-pane` / session dir |
| **Host mount for logs** | Only if caller explicitly maps volumes                | `$AOPS_SESSIONS/logs/<date>/<session>/workspace/` |
| **OTel / Phoenix**      | Forwarded via `nicwin_polecat_workers` network        | Forwarded via host env allowlist                  |

## 1. MCP Server Dispatch Route

When a task is dispatched programmatically through the Docker MCP server behind the `services` gateway (`polecat_run_container`):

### Container Lifecycle & No-Tmux Architecture

The MCP server invokes `docker.models.containers.ContainerCollection.run` with `detach=True`. **No tmux session is created.** Commands like `tmux attach` or `tmux capture-pane` do not apply.

### Real-Time Surfaces

1. **Container Log Streaming (`polecat_fetch_container_logs`)**:
   - The MCP server exposes `polecat_fetch_container_logs(container_id="<id>", tail=100)`.
   - On the host, the equivalent stream is `docker logs -f <container_name_or_id>`.
   - _Gotcha (`agy`)_: In headless print mode, `--output-format text` buffers the entire response and flushes only upon turn completion (yielding 0 stdout bytes while processing). Two options provide real-time visibility:
     - **Stream JSON via stdout**: Invoking with `--output-format stream-json` streams output in real time, emitting NDJSON events (`init`, `step_update`, tool calls) incrementally as the model generates and executes.
     - **Tail the concurrent log file**: `agy` concurrently writes execution logs to `~/.gemini/antigravity-cli/log/cli-<timestamp>.log` (or an explicit path specified by `--log-file <path>`), and records incremental session events in `~/.gemini/antigravity-cli/brain/<uuid>/.system_generated/logs/transcript.jsonl`. An observer can tail either file in real time via `docker exec <container> tail -f ...` or by mounting the log directory to the host.
2. **Authoritative OpenTelemetry Telemetry (Phoenix)**:
   - The MCP server attaches workers to the compose network (`nicwin_polecat_workers`) and forwards `GENAI_ENGINE_TRACE_ENDPOINT` via its environment allowlist.
   - Spans for LLM calls, tool executions, and subagent chains stream live over the network to Phoenix.
   - Active spans can be queried live using the `services` portal (`phoenix_execute` / `executeSql`) or inspected in the Phoenix web UI.
3. **Container State & Health (`polecat_list_containers`)**:
   - Query container state via `polecat_list_containers(filters={"id": "<short_id>"})` to inspect execution state (`running`, `exited`), health, and exit code.
4. **Task Graph State**:
   - The worker claims its assigned task in the PKB (`in_progress`) and releases it (`done` or `review`) with verified delivery evidence.

## 2. Host Script Launcher Route

When an operator or supervisor launches a worker directly on the host using `scripts/polecat` (typically wrapped in a tmux session per `tmux-interactive-driving.md`):

### Live Interactive UI (tmux)

- **Attach to session**: `tmux attach -t <session_name>` lets an operator watch the terminal interface (TUI, prompt boxes, streaming tokens, interactive tools) live.
- **Capture pane buffer**: `tmux capture-pane -t <session_name> -p -S -2000` extracts scrollback into scripts or test harnesses without manual intervention.

### Logging Architecture & Persistence Boundaries

Following the removal of `lib/polecat/cli.py` (PR #2742), host-side `$AOPS_SESSIONS` bind mounting and `polecat-session-hooks.jsonl` were removed from the execution path:

- `scripts/polecat` runs with `--rm` and mounts only `$WORKSPACE_DIR:/workspace` and credential stores (`niccreds`).
- Container-internal session files (`~/.claude/projects/`, `~/.gemini/antigravity-cli/brain/`) remain ephemeral inside the container and are destroyed on container exit unless custom volume flags are supplied.
- Output written to stdout/stderr is captured in the Docker daemon log (`docker logs -f`).

### Telemetry (Phoenix)

Forwards the OpenTelemetry contract to Phoenix via `GENAI_ENGINE_TRACE_ENDPOINT` on network `nicwin_polecat_workers`. Tool calls, agent spans, and LLM completions stream live to Phoenix.

## Observability Matrix & Failure Signals

| Observation Need                       | MCP Route                                                                                | Host Launcher Route                                         |
| :------------------------------------- | :--------------------------------------------------------------------------------------- | :---------------------------------------------------------- |
| **Is the container alive?**            | `polecat_list_containers`                                                                | `tmux has-session -t <name>` / `docker ps`                  |
| **What is the agent printing?**        | `polecat_fetch_container_logs` (stream-json) or `docker exec` tailing agy log/transcript | `tmux capture-pane` or attached terminal                    |
| **Which tool is executing right now?** | Phoenix span store query (`executeSql`)                                                  | Phoenix span store query (`executeSql`)                     |
| **Why did the worker fail?**           | `polecat.exit_code` span attribute / `polecat_fetch_container_logs`                      | Terminal/pane error text / Docker exit code / Phoenix trace |
