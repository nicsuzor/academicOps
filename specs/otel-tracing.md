---
id: spec-otel-tracing
title: Unified OpenTelemetry Tracing and Emitter Architecture
type: spec
status: draft
tags:
  - spec
  - observability
  - otel
  - phoenix
  - tracing
---

# Unified OpenTelemetry Tracing and Emitter Architecture

## Overview

Every academicOps telemetry emitter exports OpenTelemetry spans to a single Arize Phoenix project: `academicOps`. Execution surface, emitter, repository, agent persona, host, session, team, and task identity are carried on span attributes rather than encoded in the Phoenix project name.

Partitioning traces across per-directory, per-repository, per-worktree, or per-service Phoenix projects fragments a single session across isolated trace stores that cannot be joined in one waterfall or queried under one project scope. Consolidating all client harnesses, subagents, peer sessions, CI workflows, and MCP servers into `academicOps` with a normalized span-attribute contract makes an entire multi-surface conversation reconstructable in one place.

## Core Rules

1. Every production academicOps telemetry emitter sets `openinference.project.name = "academicOps"` and `project.name = "academicOps"` on its OpenTelemetry `Resource` (and `openinference-project-name: academicOps` on OTLP/HTTP export headers where supported).
2. The Phoenix project name is fixed at `academicOps`. No emitter derives `openinference.project.name` from the current working directory, git repository name, git worktree name, `polecat.yaml` project key, `PHOENIX_PROJECT_NAME`, `OTEL_SERVICE_NAME`, or `OTEL_RESOURCE_ATTRIBUTES` `service.name`.
3. Repository and workspace identity are recorded on span attributes (`aops.repo`, `project.dir`, `cwd`), never in `openinference.project.name`. `aops.repo` is derived solely from `resolve_project_from_dir(cwd)` and normalized to the canonical repository slug (`"academicOps"`, never `"aops"`), falling back to `"unknown"` when `cwd` is outside any git repository.
4. Every span in `academicOps` carries `service.name` and `aops.surface` in `spans.attributes` so traffic from different emitters and execution surfaces remains distinguishable in SQL and UI filters.
5. Because Phoenix strips `service.name` from OTLP `Resource` attributes when serializing `spans.attributes` in SQLite, the OpenTelemetry Collector `traces/phx` pipeline copies `resource.attributes["service.name"]`, `resource.attributes["host.name"]`, and `resource.attributes["aops.surface"]` into `span.attributes` whenever those keys are absent on the span, using a dedicated processor separate from any backend-specific attribute rewrites.
6. Spans emitted by hook processes and hook-launched scripts (such as `plugins/ida/hooks/premise_check_verdict.py` and `plugins/rbg/hooks/evaluator_otel_trace.py`) parent under the active turn span without depending on a built-in CLI exporter's process-wide `TRACEPARENT`. Reading the active turn's `trace_id` and `root_span_id` from the hook tracer's per-session state file works across all hook processes (`CLAUDE_ENV_FILE` is sourced before Bash commands only and never reaches hook processes). Even when `evaluator_otel_trace.py` writes OTLP JSON spans to a file sink (`COPE_EVALUATOR_OTEL_TRACE_PATH`), parenting under the turn span ensures replayed or offline-joined rule evaluations attach to the turn tree rather than becoming orphaned roots.
7. MCP server emitters (`pkb`, `polecat-mcp`) set `session.id` only when the caller propagates an explicit client session identifier (`x-session-id` header or `_meta.session_id`). They never fall back to copying the per-connection MCP transport session identifier (`mcp.session_id`) into `session.id`, preventing stateless MCP calls from appearing as synthetic sessions in Phoenix's Sessions view.
8. Automated test suites scrub OTLP export endpoints (`GENAI_ENGINE_TRACE_ENDPOINT`, `GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TRACE_PROTOCOL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`) by default so unit and integration tests never write spans to a live collector or create ephemeral Phoenix projects.
9. Each execution surface is traced by one canonical emitter: `plugins/ida/hooks/claude_code_tracer.py` for Claude Code and `plugins/ida/hooks/agy_tracer.py` for Antigravity. Built-in CLI exporters (`claude-native`) and third-party harness tracers (`coding-harness-tracing`) are not run alongside the academicOps hook tracers once the hook tracers satisfy turn-output completeness, subagent stitching, and hook-process parenting (AC4 and AC5).

## Boundaries and Constraints

- **In scope**: academicOps hook tracers (`plugins/ida/hooks/claude_code_tracer.py`, `plugins/ida/hooks/agy_tracer.py`, `plugins/ida/hooks/premise_check_verdict.py`, `plugins/ida/hooks/handlers.py`), rule-evaluation tracer (`plugins/rbg/hooks/evaluator_otel_trace.py`), CI hook generator (`scripts/ci_otel_hooks.py`), test environment isolation (`tests/conftest.py`), academicOps MCP servers (`pkb`, `polecat-mcp`), the OpenTelemetry Collector `traces/phx` pipeline, and client/container telemetry configuration.
- **Out of scope**: External, non-academicOps applications sharing a collector or Phoenix instance, and modifications to closed-source client binaries (`claude`, `agy`).
- **Single-emitter precondition**: Duplicate harness exporters (`claude-native` and Arize `coding-harness-tracing`) must only be disabled after live session traces verify that the canonical academicOps hook tracers (`claude_code_tracer.py` and `agy_tracer.py`) anchor turn extraction at the prompt-submit transcript offset, consume `last_assistant_message` from the `Stop` / `SubagentStop` hook payload when the final assistant reply has not yet flushed to disk, emit non-null `input.value` and `output.value` on turn root spans (including injected `<channel>`, `<cross-session-message>`, and `<task-notification>` turns), preserve `openinference.span.kind = "LLM"` across multi-step turns without attribute-limit eviction, stitch subagent transcripts, and parent hook-process spans under the turn.

## Output Contract: Span Attribute Schema

All spans ingested into the `academicOps` Phoenix project conform to the following attribute schema. Standard OpenInference (`openinference.*`, `session.id`, `input.value`, `output.value`, `llm.*`, `tool.*`, `agent.*`, `user.*`) and OpenTelemetry (`service.name`, `host.name`, `gen_ai.*`) keys are used wherever a standard exists; custom attributes are restricted to academicOps domain concepts (`aops.surface`, `aops.repo`, `aops.team`, `aops.message.hash`, `task.id`, `parent.session_id`, `mcp.session_id`, `cwd`, `project.dir`) that have no standard OpenInference or OpenTelemetry equivalent.

| Attribute                                                                                                                                                      | Convention     | Allowed / Expected Values                                                                                                                 | Emitters Setting It                                                                          | Purpose                                                                                                                                                                     |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `openinference.project.name`                                                                                                                                   | OpenInference  | `"academicOps"`                                                                                                                           | All emitters (`Resource` and/or `Span`)                                                      | Routes all academicOps telemetry into the single `academicOps` project in Phoenix.                                                                                          |
| `service.name`                                                                                                                                                 | OpenTelemetry  | `"aops-claude-hooks"`, `"aops-agy-hooks"`, `"aops-verdict-hooks"`, `"rbg-evaluator"`, `"pkb"`, `"polecat-mcp"`                            | All emitters (`Resource` and `Span`; enforced on `Span` by OTel Collector `traces/phx`)      | Identifies the telemetry emitter that produced the span.                                                                                                                    |
| `aops.surface`                                                                                                                                                 | academicOps    | `"claude-code"`, `"agy"`, `"github-actions"`, `"mcp-server"`                                                                              | All emitters (`Span` or `Resource` promoted by collector)                                    | Distinguishes client harness, CI runner, and MCP server traffic within the unified `academicOps` project.                                                                   |
| `aops.repo`                                                                                                                                                    | academicOps    | Canonical repository slug from `resolve_project_from_dir(cwd)` (e.g., `"academicOps"`, `"<repo>"`, or `"unknown"` outside a git checkout) | `claude_code_tracer.py`, `agy_tracer.py`, `premise_check_verdict.py`                         | Preserves per-repository filtering on span attributes; normalizes `"aops"` to `"academicOps"`.                                                                              |
| `session.id`                                                                                                                                                   | OpenInference  | 36-char dashed UUID of the client session (never populated from `mcp.session_id`)                                                         | `claude_code_tracer.py`, `agy_tracer.py`, `premise_check_verdict.py`, MCP servers (explicit) | Primary correlation key grouping all turns, LLM calls, and tool executions for a single client session ([`phoenix-span-store.md`](../lib/telemetry/phoenix-span-store.md)). |
| `mcp.session_id`                                                                                                                                               | academicOps    | Per-connection MCP transport session identifier                                                                                           | `pkb`, `polecat-mcp`                                                                         | Records the MCP transport connection ID separately from `session.id` so stateless MCP calls do not create synthetic sessions in Phoenix.                                    |
| `parent.session_id`                                                                                                                                            | academicOps    | 36-char dashed UUID of the dispatching parent session (when present)                                                                      | `claude_code_tracer.py`, `agy_tracer.py`, `polecat-mcp` (via `AOPS_PARENT_SESSION_ID`)       | Links spawned subagent or polecat worker container sessions back to the parent session.                                                                                     |
| `aops.team`                                                                                                                                                    | academicOps    | Shared team deployment identifier across peer agent sessions (when running in a multi-agent team)                                         | `claude_code_tracer.py`, `agy_tracer.py`                                                     | Groups concurrent peer sessions belonging to the same team deployment under a single filter key.                                                                            |
| `aops.message.hash`                                                                                                                                            | academicOps    | Content hash of a cross-session message payload                                                                                           | `claude_code_tracer.py`, `agy_tracer.py` (sender tool span and receiver turn root)           | Links a peer session's outbound message tool span to the receiving session's `claude-code-turn` root span.                                                                  |
| `agent.name`                                                                                                                                                   | OpenInference  | Persona or role slug (`"ida"`, `"james"`, `"sara"`, `"pauli"`, `"rbg"`, `"marsha"`, `"main"`, `"general-purpose"`, etc.)                  | `claude_code_tracer.py`, `agy_tracer.py`                                                     | Identifies which agent persona executed the turn, LLM call, or tool call.                                                                                                   |
| `agent.id`                                                                                                                                                     | OpenInference  | Session UUID (for main agent) or subagent invocation UUID / hex ID                                                                        | `claude_code_tracer.py`, `agy_tracer.py`                                                     | Distinguishes concurrent subagents sharing the parent's `session.id`.                                                                                                       |
| `host.name`                                                                                                                                                    | OpenTelemetry  | Hostname or container identifier (e.g., `"<host>"`, `"<container-id>"`, `"<ci-runner>"`)                                                  | All emitters (`Resource` and/or `Span`, promoted by collector)                               | Distinguishes persistent agent hosts, workstations, ephemeral polecat worker containers, and CI runners.                                                                    |
| `cwd`                                                                                                                                                          | academicOps    | Absolute working directory path (e.g., `"/workspace"`, `"/path/to/<repo>"`)                                                               | `claude_code_tracer.py`, `agy_tracer.py`, `premise_check_verdict.py`                         | Records the working directory where the hook fired.                                                                                                                         |
| `project.dir`                                                                                                                                                  | academicOps    | Resolved git repository root path (when inside a git checkout)                                                                            | `claude_code_tracer.py`, `agy_tracer.py`, `premise_check_verdict.py`                         | Records the checkout root path corresponding to `aops.repo` (distinct from `cwd` when running in a subdirectory).                                                           |
| `task.id`                                                                                                                                                      | academicOps    | Claimed task identifier when `AOPS_TASK_ID` or `POLECAT_TARGET_TASK` is set                                                               | `claude_code_tracer.py`, `agy_tracer.py`, `polecat-mcp`                                      | Correlates spans directly with the active task node.                                                                                                                        |
| `github.repository`, `github.workflow`, `github.job`, `github.run_id`, `github.run_attempt`, `github.run_url`, `github.sha`, `github.ref`, `github.event_name` | academicOps CI | GitHub Actions run metadata strings                                                                                                       | `claude_code_tracer.py` (when `GITHUB_ACTIONS=true`)                                         | Preserves CI workflow, job, and run filtering inside `academicOps` without a separate `github-actions` Phoenix project.                                                     |

### Cross-Surface Trace Context and Correlation

Spans inside `academicOps` correlate across three mechanisms:

1. **Intra-session turn hierarchy, turn-boundary extraction, and hook-process parenting**:
   - `plugins/ida/hooks/claude_code_tracer.py` and `plugins/ida/hooks/agy_tracer.py` create a per-turn `CHAIN` root span (`claude-code-turn` on Claude Code, `agy session` on Antigravity) at turn start, persist `trace_id` and `root_span_id` in the per-session state file, and parent all `LLM`, `TOOL`, and `AGENT` spans in the turn under that root span.
   - **Turn-start offset anchor**: At `UserPromptSubmit` (`PreInvocation` on `agy`), the tracer records the transcript byte/line offset so turn extraction reads from that offset rather than counting user messages or skipping `isMeta: true` entries. Turns triggered by injected `<channel>`, `<cross-session-message>`, or `<task-notification>` envelopes -- as well as subsequent typed turns in the same session -- extract all mid-turn `LLM` spans reliably.
   - **Turn-end `last_assistant_message` fallback at `Stop` / `SubagentStop`**: Client harnesses invoke `Stop` and `SubagentStop` before the final (`end_turn`) assistant reply is guaranteed to be flushed to the JSONL transcript file on disk. When the transcript on disk does not yet contain the turn's final assistant reply, the tracer reads `last_assistant_message` from the `Stop` / `SubagentStop` hook payload, logs the final `LLM` span from that text if not yet emitted, and sets `output.value` on the turn root span to that final answer rather than `null` or an earlier mid-turn `tool_use` assistant preamble.
   - `plugins/ida/hooks/premise_check_verdict.py` reads `trace_id` and `root_span_id` from the session state file so `premise_check_verdict` (`aops-verdict-hooks`) spans share the active turn's `trace_id` and parent under the turn root span.
   - `plugins/rbg/hooks/evaluator_otel_trace.py` likewise resolves its parent context from the active turn's session state file rather than relying on `claude-native` exporting a process-wide `TRACEPARENT`. Because `evaluator_otel_trace.py` writes OTLP JSON spans to `COPE_EVALUATOR_OTEL_TRACE_PATH` for collector ingestion or batch replay, reading the turn context from the state file ensures rule-evaluation spans attach to the turn tree even after `claude-native` is retired.
2. **Peer-session and worker correlation**:
   - Persistent peer sessions in a multi-agent team set a shared `aops.team` attribute on every span and record `aops.message.hash` on the sender's message-dispatch tool span and the receiver's `claude-code-turn` root span (with an OTel span link where supported).
   - Dispatched polecat worker containers receive `AOPS_PARENT_SESSION_ID` (`parent.session_id`) and the target task ID (`task.id`) from the dispatcher so worker spans link back to the dispatching session.
3. **MCP server correlation (`pkb` and `polecat-mcp`)**:
   - MCP server spans share the `academicOps` project with client spans. The `services` MCP portal forwards W3C `traceparent` and the caller's `AOPS_SESSION_ID` (`x-session-id` header or `_meta.session_id` / `_meta.traceparent`) to upstream MCP servers (`pkb`, `polecat-mcp`).
   - When the caller supplies a client session ID and `traceparent`, the MCP server parents its tool span under the caller's span and sets `session.id` to the client session ID. When no client session ID is supplied, the MCP server records the transport connection ID solely on `mcp.session_id` and leaves `session.id` unset.

### Collector Normalization Rule (`traces/phx`)

Phoenix extracts `openinference.project.name` from the OTLP `Resource` to assign the trace's `project_rowid`, and merges non-service resource attributes into `spans.attributes`, but drops `resource.attributes["service.name"]`. Emitters that set `service.name` only on the OTLP `Resource` therefore produce `NULL` for `s.attributes ->> '$.service.name'` unless the collector promotes `service.name` to a span attribute.

In the OTel Collector configuration, a dedicated `transform/promote_resource` processor holds only the resource-to-span promotion statements. It is kept separate from `transform/normalize_traces`, whose GCP-specific rewrites (`gen_ai.system="anthropic"`, `openinference.span.kind="AGENT"`, `lmnr.span.*` copies) must not run on Phoenix spans:

```yaml
transform/promote_resource:
  trace_statements:
    - context: span
      statements:
        - set(attributes["service.name"], resource.attributes["service.name"]) where resource.attributes["service.name"] != nil and attributes["service.name"] == nil
        - set(attributes["host.name"], resource.attributes["host.name"]) where resource.attributes["host.name"] != nil and attributes["host.name"] == nil
        - set(attributes["aops.surface"], resource.attributes["aops.surface"]) where resource.attributes["aops.surface"] != nil and attributes["aops.surface"] == nil
```

The `traces/phx` pipeline runs `transform/promote_resource` before `batch`:

```yaml
traces/phx:
  receivers: [otlp]
  processors: [memory_limiter, transform/promote_resource, batch]
  exporters: [otlp/phoenix, debug]
```

## Emitter Architecture and Component Responsibilities

Each component in the academicOps telemetry pipeline owns a distinct `service.name` and `aops.surface` contract within the `academicOps` project:

| Emitter Group                     | `service.name`         | `aops.surface`                        | Owning Component                             | Behavioral Contract                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| :-------------------------------- | :--------------------- | :------------------------------------ | :------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Claude Code Hook Tracer**       | `"aops-claude-hooks"`  | `"claude-code"` or `"github-actions"` | `plugins/ida/hooks/claude_code_tracer.py`    | Sets `openinference.project.name` and `project.name` to `"academicOps"` unconditionally, without `PHOENIX_PROJECT_NAME`, `OTEL_SERVICE_NAME`, or `OTEL_RESOURCE_ATTRIBUTES` project-name overrides. Sets `aops.repo` solely from `resolve_project_from_dir(cwd)` normalized via `resolve_canonical_project` (`"academicOps"` canonical, `"aops"` alias in `polecat.yaml`), and sets `project.dir` to the git root. Anchors turn extraction on the `UserPromptSubmit` transcript offset and consumes `last_assistant_message` at `Stop` / `SubagentStop` when the final reply is not yet on disk. |
| **Antigravity Hook Tracer**       | `"aops-agy-hooks"`     | `"agy"`                               | `plugins/ida/hooks/agy_tracer.py`            | Exports `agy session` (`CHAIN`), `LLM`, and `TOOL` spans with non-empty root `input.value` / `output.value` and per-step reported token counts to `"academicOps"`, bounding per-step `llm.input_messages` so OpenTelemetry's 128-attribute limit never evicts `openinference.span.kind` or session/service attributes, attributing each tool span's own result, propagating `parent.session_id` to `invoke_subagent` child conversations, and sharing `aops.repo` / `project.dir` (`state.get("cwd")`) with `claude_code_tracer.py`.                                                             |
| **Premise-Check Verdict Tracer**  | `"aops-verdict-hooks"` | `"claude-code"` or `"agy"`            | `plugins/ida/hooks/premise_check_verdict.py` | Exports `premise_check_verdict` (`TOOL`) spans to `"academicOps"` with `service.name = "aops-verdict-hooks"`, parenting under the active turn via the hook tracer's session state file.                                                                                                                                                                                                                                                                                                                                                                                                          |
| **Rule-Evaluation Tracer**        | `"rbg-evaluator"`      | `"claude-code"` or `"agy"`            | `plugins/rbg/hooks/evaluator_otel_trace.py`  | Emits `rbg.rule_evaluation.<slug>` spans to the `COPE_EVALUATOR_OTEL_TRACE_PATH` OTLP JSON file sink, reading parent trace context from the hook tracer's session state file so rule evaluations parent under the active turn without `claude-native`.                                                                                                                                                                                                                                                                                                                                           |
| **CI Hook Generator**             | `"aops-claude-hooks"`  | `"github-actions"`                    | `scripts/ci_otel_hooks.py`                   | Generates CI hook wrappers targeting `"academicOps"` with no `AOPS_OTEL_PROJECT` override; `claude_code_tracer.py` sets `aops.surface = "github-actions"` and attaches `github.*` attributes when `GITHUB_ACTIONS=true`.                                                                                                                                                                                                                                                                                                                                                                         |
| **PKB MCP Server**                | `"pkb"`                | `"mcp-server"`                        | PKB MCP server OTel module                   | Reads `service.name` (`OTEL_SERVICE_NAME`, `"pkb"`) separately from `openinference.project.name` (`PHOENIX_PROJECT_NAME`, required `"academicOps"` with no silent fallback). Sets `aops.surface = "mcp-server"`, records the MCP transport ID on `mcp.session_id`, and sets `session.id` only when an explicit client session ID (`x-session-id` or `_meta.session_id`) is provided.                                                                                                                                                                                                             |
| **Container-Dispatch MCP Server** | `"polecat-mcp"`        | `"mcp-server"`                        | Polecat MCP server telemetry module          | Exports `tools/call <name>` and container lifecycle spans to `"academicOps"` (`PHOENIX_PROJECT_NAME="academicOps"`) with `service.name = "polecat-mcp"` and `aops.surface = "mcp-server"`, and forwards `AOPS_PARENT_SESSION_ID` (`parent.session_id`) and `task.id` into worker containers.                                                                                                                                                                                                                                                                                                     |
| **Test Suite Isolation**          | None                   | None                                  | `tests/conftest.py`                          | Scrubs `GENAI_ENGINE_TRACE_ENDPOINT`, `GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TRACE_PROTOCOL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` in the default pytest fixture so tests never export to a live collector.                                                                                                                                                                                                                                                                                                                                                    |

## Canonical Emitter Selection (Single Emitter per Surface)

Running built-in CLI exporters (`claude-native`) or third-party harness tracers (Arize `coding-harness-tracing`) alongside the academicOps hook tracers produces duplicate spans for every turn, LLM call, and tool invocation. Each pair is evaluated below to establish why the academicOps hook tracers are the sole canonical emitters.

### Pair 1: Claude Code Built-In Exporter (`claude-native`) vs academicOps Claude Code Hook Tracer (`plugins/ida/hooks/claude_code_tracer.py`)

| Dimension                                     | `claude-native` (Built-In CLI Exporter)                                                                                                                                                                                                                                                        | `claude_code_tracer.py` (academicOps Hook Tracer)                                                                                                                                                                                                                                                                                                    |
| :-------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLM Prompts & Completions**                 | **Partial.** When `OTEL_LOG_USER_PROMPTS=1` and `ENABLE_BETA_TRACING_DETAILED=1` are active, `claude_code.llm_request` carries `new_context`, `system_prompt_preview`, `system_reminders`, the `tools` list, and `response.model_output` on a subset of requests, without full message arrays. | **Complete.** `claude/<model>` and `claude-code-turn` carry full unredacted (secret-scrubbed via `<REDACTED_SECRET>`) `input.value`, `output.value`, `llm.input_messages`, and `llm.output_messages`, consuming `last_assistant_message` at `Stop` / `SubagentStop` when the final `end_turn` reply has not yet flushed to disk.                     |
| **Tool Call Inputs & Outputs**                | **Inputs only.** With `OTEL_LOG_TOOL_DETAILS=1`, `claude_code.tool` carries `full_command`, `tool_input`, `skill_name`, and `subagent_type`; `claude_code.tool.execution` carries `tool_use_id` and `duration_ms`. Tool outputs are omitted.                                                   | **Complete.** Tool spans carry full JSON `input.value`, `output.value` (secret-scrubbed), `tool.name`, `tool.call_id`, and `tool.json_schema`.                                                                                                                                                                                                       |
| **Subagent LLM & Tool Spans**                 | **Present.** Fires inside the `claude` process for every API request, including subagents.                                                                                                                                                                                                     | **Present via `SubagentStop` stitching.** Stitches subagent JSONL transcripts (`subagents/agent-*.jsonl`) at `SubagentStop` (including `last_assistant_message` fallback) and anchors turn extraction at `UserPromptSubmit` so injected turns (`<channel>`, `<cross-session-message>`, `<task-notification>`) retain all LLM spans and turn outputs. |
| **API Latency & Streaming Metrics**           | **Present.** Carries `ttft_ms`, `first_content_ms`, `duration_ms`, `attempt`, `speed`, `effort`, `query_source`, per-request cache tokens, `request_id`, `client_request_id`, and `claude_code.hook` timing spans.                                                                             | **Absent** for `ttft_ms`, `first_content_ms`, and `request_id` (Claude Code transcripts record turn/step timestamps and token usage, not streaming time-to-first-token).                                                                                                                                                                             |
| **Permission-Wait Spans**                     | **Present** (`claude_code.tool.blocked_on_user` with `decision` and `duration_ms`).                                                                                                                                                                                                            | **Present via hook events** (`Notification: permission_prompt`, `Permission Request`, `Permission Denied`).                                                                                                                                                                                                                                          |
| **Trace Hierarchy & W3C Context Propagation** | **Turn-hierarchical.** Parents `claude_code.llm_request` and `claude_code.tool` under `claude_code.interaction` and exports a process-wide `TRACEPARENT` into hook subprocess environments.                                                                                                    | **Turn-hierarchical.** Parents `LLM`, `TOOL`, `AGENT`, and hook-process spans (`premise_check_verdict.py`, `evaluator_otel_trace.py`) under `claude-code-turn` (`CHAIN`) via the per-session state file (Core Rule 6).                                                                                                                               |
| **Domain Attribution**                        | **Partial.** Carries `agent_id`, `parent_agent_id`, `subagent_type`, `user.email`, `organization.id`, and `terminal.type`, but no `agent.name`, `aops.repo`, `aops.team`, `cwd`, `project.dir`, `task.id`, or `github.*`.                                                                      | **Complete.** Sets `agent.name`, `agent.id`, `subagent.id`, `aops.repo`, `aops.team`, `aops.message.hash`, `cwd`, `project.dir` (git root), `task.id`, and `github.*`.                                                                                                                                                                               |

- **Canonical emitter to keep**: `plugins/ida/hooks/claude_code_tracer.py`, for complete prompt, completion, and tool-output capture and academicOps domain attributes.
- **Lost when `claude-native` is disabled**: `ttft_ms`, `first_content_ms`, `request_id`, `query_source`, `effort`, per-request cache tokens, `claude_code.hook` timings, `claude_code.tool.blocked_on_user` durations, and in-process subagent nesting.
- **Duplicate to retire**: `claude-native` (retired once AC4 and AC5 pass on live traces).

### Pair 2: Arize `coding-harness-tracing` for Antigravity (`antigravity`) vs academicOps Agy Hook Tracer (`plugins/ida/hooks/agy_tracer.py`)

| Dimension                                | `antigravity` (Arize `coding-harness-tracing`)                                                                      | `agy_tracer.py` (academicOps Hook Tracer)                                                                                                                                                                      |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Prompts, Completions & Tool Payloads** | **Redacted or empty.** Outputs are replaced with `"<redacted (N chars)>"`; `LLM` span inputs are mostly empty.      | **Complete.** Carries unredacted (secret-scrubbed) `input.value` and `output.value` on `agy session` (`CHAIN`), `LLM`, and `TOOL` spans, with bounded per-step `llm.input_messages` and `llm.output_messages`. |
| **Token Counts**                         | **Absent.** `LLM` spans carry `llm.model_name` only, with no token usage.                                           | **Present.** Extracts per-step reported prompt, completion, total, and cache-read token counts from the Antigravity transcript (`PLANNER_RESPONSE`) and conversation database.                                 |
| **Step & Subagent Coverage**             | **Incomplete.** Captures a subset of `LLM` steps and collapses multi-turn sessions into a single `Turn` span.       | **Complete.** Captures all `LLM` and `TOOL` steps across each turn (including continuations after `wait` / `SYSTEM_MESSAGE` wakeups) and links `invoke_subagent` child conversations via `parent.session_id`.  |
| **Model Display Name**                   | Includes the UI display string in the span name (`"LLM: <Model Display Name>"`).                                    | Sets `llm.model_name` from the step payload and parses `<USER_SETTINGS_CHANGE>` in `llm.input_messages`.                                                                                                       |
| **Domain Attribution**                   | **Minimal.** Sets `session.id` only; no `agent.name`, `aops.repo`, `host.name`, `user.id`, `cwd`, or `project.dir`. | **Complete.** Sets `agent.name`, `agent.id`, `subagent.id`, `parent.session_id`, `aops.repo`, `host.name`, `user.id`, `cwd`, and `project.dir` (git root).                                                     |

- **Canonical emitter to keep**: `plugins/ida/hooks/agy_tracer.py`.
- **Duplicate to retire**: Arize `coding-harness-tracing` for Antigravity.

### Pair 3: Arize `coding-harness-tracing` for Claude Code (`claude-code`) vs academicOps Claude Code Hook Tracer (`plugins/ida/hooks/claude_code_tracer.py`)

| Dimension                                | `claude-code` (Arize `coding-harness-tracing`)                                                                               | `claude_code_tracer.py` (academicOps Hook Tracer)                                                    |
| :--------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| **Prompts, Completions & Tool Payloads** | **Redacted.** All `input.value`, `output.value`, `tool.command`, and `tool.description` fields are `"<redacted (N chars)>"`. | **Complete** (secret-scrubbed via `<REDACTED_SECRET>`).                                              |
| **Slash Command Metadata**               | `Turn N` spans parse `command.name`, `command.expansion_type`, and `command.source` as discrete attributes.                  | Captures the expanded `<command-name>` and prompt text directly in `claude-code-turn` `input.value`. |
| **Domain Attribution & W3C Context**     | **Absent.** No `host.name`, `agent.name`, `aops.repo`, `cwd`, or turn-tree context sharing.                                  | **Complete.** Full domain attributes and turn-level hierarchy.                                       |

- **Canonical emitter to keep**: `plugins/ida/hooks/claude_code_tracer.py`.
- **Lost when retired**: `command.name`, `command.expansion_type`, and `command.source` as discrete attributes (the expanded command text remains in `input.value`).
- **Duplicate to retire**: Arize `coding-harness-tracing` for Claude Code.

## Acceptance Criteria

Each acceptance criterion below is verified against the Phoenix SQLite database via `executeSql` over a verification window `s.start_time >= '<SINCE_ISO>'` (an RFC 3339 UTC timestamp, e.g. `'2026-10-15T00:00:00+00:00'`).

### AC1: Single Target Project (`academicOps`)

All academicOps spans ingested during the verification window land exclusively in the `academicOps` project.

**Verification query**:

```sql
SELECT p.name AS project_name, COUNT(s.id) AS span_count
FROM spans s
JOIN traces t ON s.trace_rowid = t.id
JOIN projects p ON t.project_rowid = p.id
WHERE s.start_time >= '<SINCE_ISO>'
GROUP BY p.name
ORDER BY span_count DESC
```

**Pass condition**: `academicOps` is returned, and no academicOps emitter writes to any per-directory, per-repository, per-worktree (`wt-%`), per-service (`pkb`, `polecat-mcp`, `default`, `github-actions`), or duplicate-harness (`claude-native`, `antigravity`, `claude-code`) project.

### AC2: Emitter and Surface Distinguishability on Every Span

Every span ingested into `academicOps` carries non-null `service.name` and `aops.surface` attributes in `spans.attributes`, covering hook tracers (`aops-claude-hooks`, `aops-agy-hooks`, `aops-verdict-hooks`) and MCP servers (`pkb`, `polecat-mcp`).

**Verification query**:

```sql
SELECT
  s.attributes ->> '$.service.name' AS service_name,
  s.attributes ->> '$.aops.surface' AS surface,
  COUNT(s.id) AS span_count
FROM spans s
JOIN traces t ON s.trace_rowid = t.id
JOIN projects p ON t.project_rowid = p.id
WHERE p.name = 'academicOps'
  AND s.start_time >= '<SINCE_ISO>'
GROUP BY service_name, surface
ORDER BY span_count DESC
```

**Pass condition**: Zero rows have `service_name IS NULL` or `surface IS NULL`, and active emitters (`aops-claude-hooks`, `aops-agy-hooks`, `aops-verdict-hooks`, `pkb`, `polecat-mcp`) appear as distinct `(service_name, surface)` rows.

### AC3: Repository, Host, Agent, and Session Distinguishability on Hook-Tracer Spans

Every client hook-tracer span (`service.name IN ('aops-claude-hooks', 'aops-agy-hooks', 'aops-verdict-hooks')`) in `academicOps` carries non-null `session.id`, `aops.repo` (derived from `resolve_project_from_dir(cwd)` with `"aops"` normalized to `"academicOps"`), `host.name`, and `agent.name`.

**Verification query**:

```sql
SELECT
  COUNT(s.id) AS total_hook_spans,
  SUM(CASE WHEN s.attributes ->> '$.session.id' IS NULL THEN 1 ELSE 0 END) AS missing_session_id,
  SUM(CASE WHEN s.attributes ->> '$.aops.repo' IS NULL THEN 1 ELSE 0 END) AS missing_repo,
  SUM(CASE WHEN s.attributes ->> '$.aops.repo' = 'aops' THEN 1 ELSE 0 END) AS unnormalized_aops_slug,
  SUM(CASE WHEN s.attributes ->> '$.host.name' IS NULL THEN 1 ELSE 0 END) AS missing_host_name,
  SUM(CASE WHEN s.attributes ->> '$.agent.name' IS NULL THEN 1 ELSE 0 END) AS missing_agent_name
FROM spans s
JOIN traces t ON s.trace_rowid = t.id
JOIN projects p ON t.project_rowid = p.id
WHERE p.name = 'academicOps'
  AND s.start_time >= '<SINCE_ISO>'
  AND s.attributes ->> '$.service.name' IN ('aops-claude-hooks', 'aops-agy-hooks', 'aops-verdict-hooks')
```

**Pass condition**: `total_hook_spans > 0` and `missing_session_id = 0`, `missing_repo = 0`, `unnormalized_aops_slug = 0`, `missing_host_name = 0`, `missing_agent_name = 0`.

### AC4: Cross-Surface Coexistence, Turn-Tree Hierarchy, and MCP Session Hygiene

Client surface spans (`aops.surface IN ('claude-code', 'agy', 'github-actions')`) and MCP server spans (`aops.surface = 'mcp-server'`, `service.name IN ('pkb', 'polecat-mcp')`) coexist in `academicOps`, every non-root hook-tracer span has a parent span present in the same trace, and no MCP server span sets `session.id` from its `mcp.session_id` transport fallback.

**Verification query**:

```sql
SELECT
  s.attributes ->> '$.aops.surface' AS surface,
  s.attributes ->> '$.service.name' AS service_name,
  COUNT(DISTINCT t.id) AS trace_count,
  COUNT(s.id) AS span_count,
  SUM(CASE WHEN s.span_kind IN ('LLM', 'TOOL', 'AGENT') AND s.parent_id IS NOT NULL THEN 1 ELSE 0 END) AS parented_child_spans,
  SUM(CASE WHEN s.parent_id IS NOT NULL AND ps.id IS NULL THEN 1 ELSE 0 END) AS orphaned_spans,
  SUM(CASE WHEN s.attributes ->> '$.mcp.session_id' IS NOT NULL AND s.attributes ->> '$.session.id' = s.attributes ->> '$.mcp.session_id' THEN 1 ELSE 0 END) AS transport_session_leaks
FROM spans s
JOIN traces t ON s.trace_rowid = t.id
JOIN projects p ON t.project_rowid = p.id
LEFT JOIN spans ps ON ps.span_id = s.parent_id AND ps.trace_rowid = s.trace_rowid
WHERE p.name = 'academicOps'
  AND s.start_time >= '<SINCE_ISO>'
GROUP BY surface, service_name
ORDER BY span_count DESC
```

**Pass condition**: Rows are present in `academicOps` for both client surfaces (`claude-code` / `agy`) and `mcp-server` (`pkb` / `polecat-mcp`); for hook-tracer rows (`aops-claude-hooks`, `aops-agy-hooks`, `aops-verdict-hooks`) `parented_child_spans > 0` and `orphaned_spans = 0`; and across all rows `transport_session_leaks = 0`.

### AC5: Turn-Output, LLM Span, and Subagent Span Completeness (Single-Emitter Prerequisite Gate)

Completed turn root spans (`s.name IN ('claude-code-turn', 'agy session')`) -- including turns triggered by injected `<channel>`, `<cross-session-message>`, or `<task-notification>` envelopes -- carry non-empty `input.value` and `output.value` (via transcript offset anchoring and `Stop` / `SubagentStop` `last_assistant_message` fallback) and at least one child `LLM` span in the same trace with zero `LLM` spans degraded to `span_kind = 'UNKNOWN'` by attribute-limit eviction, and turns that invoke the `Agent` tool emit stitched subagent spans (`subagent.id IS NOT NULL`).

**Verification query**:

```sql
WITH turn_stats AS (
  SELECT
    s.attributes ->> '$.input.value' AS input_val,
    s.attributes ->> '$.output.value' AS output_val,
    CASE
      WHEN s.attributes ->> '$.input.value' LIKE '%<channel%'
        OR s.attributes ->> '$.input.value' LIKE '%<cross-session-message%'
        OR s.attributes ->> '$.input.value' LIKE '%<task-notification%'
      THEN 1 ELSE 0
    END AS is_injected,
    (SELECT COUNT(1) FROM spans l WHERE l.trace_rowid = s.trace_rowid AND l.span_kind = 'LLM') AS llm_cnt,
    (SELECT COUNT(1) FROM spans u WHERE u.trace_rowid = s.trace_rowid AND u.name = 'LLM' AND u.span_kind = 'UNKNOWN') AS bad_llm_cnt,
    (SELECT COUNT(1) FROM spans a WHERE a.trace_rowid = s.trace_rowid AND a.name = 'Agent' AND a.span_kind = 'TOOL') AS agent_cnt,
    (SELECT COUNT(1) FROM spans b WHERE b.trace_rowid = s.trace_rowid AND b.attributes ->> '$.subagent.id' IS NOT NULL) AS sub_cnt
  FROM spans s
  JOIN traces t ON s.trace_rowid = t.id
  JOIN projects p ON t.project_rowid = p.id
  WHERE p.name = 'academicOps'
    AND s.start_time >= '<SINCE_ISO>'
    AND s.name IN ('claude-code-turn', 'agy session')
    AND s.end_time IS NOT NULL
)
SELECT
  COUNT(1) AS completed_turns,
  SUM(is_injected) AS injected_turns,
  SUM(CASE WHEN input_val IS NULL OR input_val = '' THEN 1 ELSE 0 END) AS missing_turn_input,
  SUM(CASE WHEN output_val IS NULL OR output_val = '' THEN 1 ELSE 0 END) AS missing_turn_output,
  SUM(CASE WHEN is_injected = 1 AND (output_val IS NULL OR output_val = '') THEN 1 ELSE 0 END) AS missing_injected_turn_output,
  SUM(CASE WHEN llm_cnt = 0 THEN 1 ELSE 0 END) AS turns_without_llm_spans,
  SUM(bad_llm_cnt) AS degraded_llm_spans,
  SUM(CASE WHEN agent_cnt > 0 AND sub_cnt = 0 THEN 1 ELSE 0 END) AS agent_turns_without_subagent_spans
FROM turn_stats
```

**Pass condition**: `completed_turns > 0`, `injected_turns > 0`, `missing_turn_input = 0`, `missing_turn_output = 0`, `missing_injected_turn_output = 0`, `turns_without_llm_spans = 0`, `degraded_llm_spans = 0`, and `agent_turns_without_subagent_spans = 0`.

### AC6: Zero Duplicate-Emitter Traffic and Zero Test/Worktree Project Pollution

Zero spans are emitted by duplicate harness exporters (`claude-native` or Arize `coding-harness-tracing`), and running `uv run pytest` or executing work inside git worktrees produces zero spans in test or worktree-named projects (`academicOps-test`, `hooks`, `test-%`, `outside%`, `wt-%`).

**Verification query**:

```sql
SELECT
  p.name AS project_name,
  s.attributes ->> '$.service.name' AS service_name,
  s.name AS span_name,
  COUNT(s.id) AS span_count
FROM spans s
JOIN traces t ON s.trace_rowid = t.id
JOIN projects p ON t.project_rowid = p.id
WHERE s.start_time >= '<SINCE_ISO>'
  AND (
    p.name IN ('claude-native', 'antigravity', 'claude-code', 'academicOps-test', 'hooks')
    OR p.name LIKE 'test-%'
    OR p.name LIKE 'outside%'
    OR p.name LIKE 'wt-%'
    OR s.attributes ->> '$.service.name' = 'claude-native'
    OR s.name LIKE 'claude_code.%'
    OR s.attributes ->> '$.input.value' LIKE '<redacted (%chars)>'
  )
GROUP BY p.name, service_name, span_name
```

**Pass condition**: Zero rows returned.

## Rationale

- **One project (`academicOps`) over per-emitter or per-repository projects**: In Phoenix, `projects` partition the trace store -- cross-project traces cannot render in a single waterfall, and UI searches or evaluations are scoped to one project at a time. Because one academicOps session routinely crosses repositories, spawns subagents or polecat containers, messages peer sessions, and calls MCP servers (`pkb`, `polecat-mcp`), only a single project allows end-to-end session inspection.
- **OpenInference + OpenTelemetry semantic conventions with minimal `aops.*` extensions**: Phoenix's UI natively indexes `session.id`, `input.value`, `output.value`, `openinference.span.kind`, `llm.model_name`, `llm.token_count.*`, `tool.name`, `agent.name`, and `user.id`. Using standard keys for those fields preserves native Phoenix UI rendering (Sessions tab, token/cost rollups, span kind badges), while `aops.surface`, `aops.repo`, `aops.team`, `aops.message.hash`, `task.id`, `parent.session_id`, and `mcp.session_id` capture academicOps-specific routing and correlation dimensions without colliding with OpenInference fields or polluting `session.id` with stateless MCP transport connections.
- **Collector-level promotion of `service.name`, `host.name`, and `aops.surface` in a dedicated processor**: Relying on every emitter to duplicate `Resource` attributes onto every `Span` fails for third-party middleware (`FastMCP` `OpenTelemetryMiddleware` in `polecat-mcp` or SDK-level resource configuration in `pkb`). Promoting `resource.attributes["service.name"]`, `resource.attributes["host.name"]`, and `resource.attributes["aops.surface"]` in a dedicated `transform/promote_resource` processor in the OTel Collector's `traces/phx` pipeline solves the Phoenix resource-attribute stripping gap once at the ingestion boundary without running GCP-specific `transform/normalize_traces` rewrites on Phoenix spans.
- **Canonical academicOps hook tracers over `claude-native` and Arize `coding-harness-tracing`**: Arize `coding-harness-tracing` (`antigravity`, `claude-code`) redacts content, and `claude-native` captures prompts and tool inputs only partially while omitting tool outputs and academicOps domain attributes. With turn extraction anchored at `UserPromptSubmit` (`PreInvocation` on `agy`), final turn outputs captured via `Stop` / `SubagentStop` `last_assistant_message` fallback when the transcript has not yet flushed, subagent transcripts stitched at `SubagentStop`, and hook-process spans parented under the turn via the session state file, the duplicate harness exporters add storage and span noise without contributing unique turn or tool content.
