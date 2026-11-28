---
title: Caller-session tracing contract for MCP servers
status: ready
---

# Caller-session tracing contract for MCP servers

Every custom Model Context Protocol (MCP) server and gateway portal exports OpenTelemetry tool-call spans to the shared collector and attributes executions using standards-native MCP `2026-07-28` metadata and W3C Trace Context / Baggage rather than custom domain tool parameters. The contract applies to servers and gateways implemented in any language runtime, ensuring that direct and pass-through invocations link into the caller's session trace with complete attribution, secret-scrubbed payloads, and strict domain schemas, while Code Mode agent calls are attributed through the client hook tracer's `TOOL` spans.

## User stories

### US-1 Propagate trace and caller session context via MCP `2026-07-28` and W3C Baggage

As a platform operator, I want custom MCP servers and programmatic HTTP callers to propagate distributed trace context and caller session identifiers through MCP `2026-07-28` `params._meta` and W3C headers without adding correlation parameters to tool schemas, so that direct and pass-through executions attach to the originating agent session cleanly.

- **AC-1.1** Given a tool call carrying W3C Trace Context (`traceparent`, `tracestate`) and W3C Baggage (`baggage: session.id=<id>,agent.id=<id>,prompt.id=<id>`) in `params._meta` (SEP-414 primary carrier) or HTTP headers (secondary carrier), when the server receives the call, then the server extracts parent trace context and strictly allowlisted baggage keys (`session.id` / `session_id`, `agent.id` / `agent_id`, `prompt.id` / `prompt_id`, `parent.session_id` / `parent_session_id`, `task.id` / `task_id`) with `params._meta` taking precedence over HTTP headers, and falls back to client-native conversation metadata (`params._meta["antigravity.google/root_conversation_id"]` or `params._meta["antigravity.google/conversation_id"]`) when baggage carries no session identifier.
- **AC-1.2** Given a programmatic HTTP caller invoking an upstream MCP server directly or through a gateway portal (using `?codemode=off` and an explicit non-default `User-Agent` when calling through a Code Mode portal), when the caller sends the request, then it uses stateless MCP `2026-07-28` (`MCP-Protocol-Version: 2026-07-28`, `Mcp-Method`, `Mcp-Name`, and `params._meta` client descriptors) with W3C `traceparent` and `baggage` in both `params._meta` and HTTP headers, with zero stateful `initialize` handshakes and zero `x-session-id` or `arguments.session_id` correlation parameters.
- **AC-1.3** Given a hook-traced agent session invoking tools through a gateway Code Mode wrapper (`portal_codemode_execute`) that strips outer `_meta` and correlation headers, when the call executes, then session grouping, subagent lineage, full Code Mode input/output payloads, and structured `task.id` on task-bound sessions (`AOPS_TASK_ID`) are recorded on the client hook tracer's `TOOL` span in the shared trace project without requiring agents or hooks to inject `session_id` into tool arguments.
- **AC-1.4** Given a request that arrives without baggage or client-native session metadata, when the server processes the call, then the server executes the tool normally (never refusing the call for missing correlation metadata) with `session.id` unset and `aops.session.source = "none"`.

### US-2 Keep domain tool schemas free of transport and correlation parameters

As a platform operator, I want MCP servers to keep tool input schemas strictly domain-scoped with zero injected `session_id` or `_session` parameters, so that domain contracts stay clean, LLM context is unpolluted, and strict gateway validators pass without hook rewriting.

- **AC-2.1** Given any custom MCP server in the fleet, when the server advertises `tools/list`, then zero tool schemas declare correlation parameters named `session_id` or `_session` in `inputSchema.properties` or `inputSchema.required` (domain workspace handles use explicit domain names such as `resume_session_id`).
- **AC-2.2** Given any client surface invoking MCP tools directly or through a gateway portal, when an agent invokes a tool, then neither the agent nor client `PreToolUse` hooks pass or rewrite caller correlation `session_id` parameters in tool arguments.
- **AC-2.3** Given a server receiving actor/client descriptors, when the request carries `params._meta["io.modelcontextprotocol/clientInfo"]` or gateway identity headers (`X-Forwarded-User-Agent`, access identity headers), then the server records `mcp.client.name` / `mcp.client.version` without binding the HTTP connection to any caller session.

### US-3 Emit standardized OpenTelemetry tool spans with attribution attributes

As an auditor inspecting traces, I want every custom MCP server to emit OpenTelemetry spans for tool executions with complete attribution and correlation attributes, so that tool calls appear in the caller's session trace with accurate lineage and timing.

- **AC-3.1** Given any tool execution on an instrumented MCP server, when the server completes the call, then it exports an OpenTelemetry span with `openinference.span.kind = "TOOL"`, `openinference.project.name = "academicOps"`, `tool.name` set to the invoked tool name, `service.name` set to the server's logical service name, and secret-scrubbed tool inputs and outputs in `input.value` and `output.value`.
- **AC-3.2** Given a tool execution with a resolved caller session from W3C `baggage` or client-native `_meta`, when the server exports the tool span, then `session.id` is set to the resolved session identifier and `aops.session.source` records `"meta"` or `"header"`.
- **AC-3.3** Given a tool execution where no caller session was propagated (such as through a Code Mode gateway that strips `_meta`), when the server exports the tool span, then `session.id` remains unset, `aops.session.source` is `"none"`, and `mcp.client.name` records client identity when supplied.
- **AC-3.4** Given a tool execution carrying allowlisted `agent.id` or `prompt.id` in W3C `baggage`, when the server exports the tool span, then the span sets `agent.id` and `prompt.id`.
- **AC-3.5** Given a tool call that references a specific task, when the server exports the tool span, then `task.id` is set to the target task identifier.
- **AC-3.6** Given a request carrying W3C trace context (`traceparent`) in `params._meta` or HTTP headers, when the server exports the tool span, then the tool span adopts the caller's `trace_id` and parents under the caller's tool invocation span.

### US-4 Fail-fast OpenTelemetry export configuration across language runtimes

As a platform operator deploying MCP servers in various runtime environments, I want servers in any language to use a uniform, fail-fast configuration contract for OpenTelemetry export, so that telemetry pipelines deploy reliably and configuration errors halt immediately at startup.

- **AC-4.1** Given an instrumented MCP server initializing telemetry, when resolving the collector OTLP traces endpoint, then the server resolves the endpoint in precedence order from `GENAI_ENGINE_ENDPOINT` followed by `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, and if neither variable is set, halts startup immediately with an explicit configuration error.
- **AC-4.2** Given an instrumented MCP server initializing telemetry with an endpoint configured, when configuring export credentials, then the server builds the `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers from `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` and passes them to the exporter constructor; it never reads or sets `OTEL_EXPORTER_OTLP_HEADERS` as a carrier for the token, since every OTel SDK in the process tree would pick it up.
- **AC-4.3** Given an instrumented MCP server exporting tool spans, when the collector endpoint is unreachable or span delivery encounters an error, then the server surfaces the export failure with diagnostic error details to standard error output.

## Design

### Calling Session Delivery and Resolution

MCP servers resolve distributed trace context and caller correlation strictly per-request over stateless MCP `2026-07-28`, using standard OpenTelemetry carriers in strict priority order:

1. **Request Metadata (`params._meta`, SEP-414 primary carrier)**: Standard unprefixed W3C keys `traceparent`, `tracestate`, and `baggage` (`session.id=<uuid>,agent.id=<id>,prompt.id=<id>`) inside `params._meta`, alongside `io.modelcontextprotocol/clientInfo`.
2. **HTTP Headers (secondary carrier)**: Standard W3C `traceparent`, `tracestate`, and `baggage` headers on Streamable HTTP (`/mcp`) POST requests.
3. **Client-Native Metadata Fallback**: When W3C `baggage` carries no session identifier, servers check `params._meta["antigravity.google/root_conversation_id"]` then `params._meta["antigravity.google/conversation_id"]` so direct or pass-through clients carrying native conversation IDs attribute automatically without extra wrappers.

Only strictly allowlisted baggage keys are copied onto span attributes (via a server-side allowlist `SpanProcessor` or explicit extractor), preventing arbitrary caller baggage from leaking into telemetry. When no session metadata is present, `session.id` remains unset and `aops.session.source` is `"none"`; servers never refuse calls for missing correlation metadata and never bind HTTP connections to caller sessions.

```
Programmatic HTTP Caller (Direct or Portal ?codemode=off)
  ├── params._meta: { traceparent, baggage: "session.id=...,agent.id=...,prompt.id=...", clientInfo }
  └── HTTP headers: traceparent, baggage, MCP-Protocol-Version: 2026-07-28, Mcp-Method, Mcp-Name
          │
          ▼
     MCP Server (/mcp, stateless 2026-07-28)
          │
          ├── Extracts TraceContext + allowlisted Baggage (_meta > HTTP headers > client-native _meta)
          ├── Executes domain tool handler (zero session_id tool arguments)
          └── Exports child TOOL span parented under caller trace with session.id
```

```
Hook-Traced Agent Session (Gateway Code Mode, e.g. portal_codemode_execute)
  ├── Client hook tracer emits TOOL span (session.id, agent.id, parent.session_id, input/output, plus task.id when task-bound)
  └── Gateway Code Mode invokes upstream server (/mcp, stateless 2026-07-28)
          └── Upstream server executes clean domain tool and emits service TOOL span (mcp.client.name, latency)
```

### Rejected Choices

- **Client `PreToolUse` hook input injection (`updatedInput` / `overwrite`)**: Rejected because remote/cloud MCP surfaces refuse hook-mutated tool inputs, strict third-party schemas reject injected keys, and client hooks cannot rewrite nested tool calls inside `portal_codemode_execute`.
- **Mandatory caller-supplied `session_id` tool arguments and `x-session-id` headers**: Rejected because they pollute domain tool schemas and LLM context, cause recurring tool-call failures when agents omit or mismatch subagent IDs, and never propagate W3C `traceparent` span parenting.

### Span Attributes Specification

Tool execution spans emitted by custom MCP servers comply with OpenInference semantic conventions and framework attribution invariants:

| Attribute | Type | Requirement | Description |
| :- | :- | :- | :- |
| `openinference.span.kind` | string | Required | Must be `"TOOL"`. |
| `openinference.project.name` | string | Required | Must be `"academicOps"`. |
| `project.name` | string | Required | Must be `"academicOps"`. |
| `service.name` | string | Required | Logical service name of the MCP server. |
| `aops.surface` | string | Required | Must be `"mcp-service"`. |
| `tool.name` | string | Required | The name of the executed MCP tool. |
| `tool.call_id` | string | Conditional | Transport call or message identifier when available. |
| `session.id` | string | Conditional | Resolved caller session identifier from allowlisted W3C `baggage` or client-native `_meta`. Omitted when unattributed. |
| `aops.session.source` | string | Required | Resolution source: `"meta"`, `"header"`, or `"none"`. |
| `mcp.client.name` | string | Optional | Client software name from `params._meta["io.modelcontextprotocol/clientInfo"]` or `X-Forwarded-User-Agent`. |
| `agent.id` | string | Optional | Caller agent identifier when supplied in allowlisted W3C `baggage`. |
| `prompt.id` | string | Optional | Caller prompt turn identifier when supplied in allowlisted W3C `baggage`. |
| `task.id` | string | Optional | Target task identifier when the tool operation targets a task. |
| `input.value` | string | Required | JSON-serialized string of tool input arguments, scrubbed of credentials and secrets. |
| `output.value` | string | Required | JSON-serialized string of tool execution results, scrubbed of credentials and secrets. |

### Configuration and Export Guarantees

Custom MCP servers configure OpenTelemetry export using environment variables common across all language runtimes:

| Variable | Precedence | Purpose |
| :- | :- | :- |
| `GENAI_ENGINE_ENDPOINT` | 1 | Primary OTLP traces export URL (e.g. `https://otel.example.org/v1/traces` or `http://localhost:4318/v1/traces`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | 2 | Secondary OTLP traces export URL evaluated if `GENAI_ENGINE_ENDPOINT` is unset. |
| `CF_ACCESS_CLIENT_ID` + `CF_ACCESS_CLIENT_SECRET` | 1 | The one Cloudflare Access service-token pair, sent as `CF-Access-Client-Id` / `CF-Access-Client-Secret`. The launching context chooses which stored token fills it. |
| `OTEL_SERVICE_NAME` | 1 | Logical service name for the server instance. |

#### Fail-Fast Startup and Export Reliability

Servers require an explicit OTLP endpoint to initialize telemetry. If neither `GENAI_ENGINE_ENDPOINT` nor `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is set, the server aborts startup immediately with an exit code and an error message identifying the missing configuration. When an export batch fails at runtime, the server surfaces the error to standard error output rather than discarding telemetry silently.
