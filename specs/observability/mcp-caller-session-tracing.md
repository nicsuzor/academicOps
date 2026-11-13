---
title: Caller-session tracing contract for MCP servers
status: ready
---

# Caller-session tracing contract for MCP servers

Every custom Model Context Protocol (MCP) server and gateway portal exports OpenTelemetry tool-call spans to the shared collector and attributes each execution to the calling agent session. The contract applies to servers and gateways implemented in any language runtime, ensuring that direct invocations and gateway-routed calls appear in the caller's session trace with complete attribution, secret-scrubbed payloads, and unambiguous provenance across all client execution surfaces.

## User stories

### US-1 Receive and resolve caller session direct and through gateway portals

As a platform operator, I want custom MCP servers and gateway proxies to receive and propagate caller session identity across direct and multiplexed connections, so that downstream tool executions attach to the originating agent session without synthetic transport sessions.

- **AC-1.1** Given a direct tool call carrying a caller session identifier via top-level `session_id` tool argument, `_meta.session_id` request metadata, or `x-session-id` transport header, when the server receives the call, then the server resolves the caller session identifier from the highest-priority source present in precedence order: explicit tool argument (`session_id`), request metadata (`_meta.session_id`), transport header (`x-session-id`).
- **AC-1.2** Given a client invoking a tool through a gateway proxy (such as `call_mcp_tool` with `ServerName == "pkb"` or `portal_codemode_execute`), when the gateway forwards the call to an upstream server, then the gateway preserves or injects the caller's `session_id` and forwards it upstream in `Arguments.session_id` / `x-session-id` along with W3C `traceparent` context and stateless MCP `2026-07-28` headers.
- **AC-1.3** Given an upstream server receiving a request, when the server processes the call, then it resolves the caller session from top-level `session_id`, request metadata, or the forwarded `x-session-id` header for that call without binding the connection to any single session.
- **AC-1.4** Given a request that arrives without an explicit session identifier, when the server processes the call, then the call remains unattributed with `aops.session.source = "none"` and `session.id` unset.
- **AC-1.5** Given a client surface or tool wrapper that does not support client-side argument rewriting (such as `portal_codemode_execute` whose schema rejects unknown top-level parameters), when invoking PKB tools directly or through a gateway, then tool calls carry caller `session_id` explicitly inside the invoked tool arguments by instruction or resolve from transport headers and metadata.

### US-2 Declare caller session acceptance and preserve tool schemas

As a client or gateway dispatcher, I want MCP servers to accept explicit `session_id` on their tool schemas while leaving non-session and portal wrapper tools without injected unknown top-level arguments, so that domain schemas remain strict and attribution succeeds without schema validation errors.

- **AC-2.1** Given a PKB MCP server tool supporting caller attribution, when the server advertises its tool schemas, then it accepts top-level `session_id` as a parameter and clients inject `session_id` only onto PKB tools (or `call_mcp_tool` `Arguments` targeting `pkb`).
- **AC-2.2** Given an MCP server that handles caller `session_id` inside tool arguments, when a tool call containing `session_id` arrives, then the server extracts `session_id` cleanly alongside domain validation without rejecting it.
- **AC-2.3** Given an upstream MCP server that enforces strict argument validation without declaring `session_id` in its schema, when a gateway proxy receives a tool call carrying caller session metadata destined for that server, then the gateway translates the caller session identity into the `x-session-id` transport header or request metadata without injecting unknown top-level parameters onto strict portal wrappers (`portal_*`).

### US-3 Emit standardized OpenTelemetry tool spans with attribution attributes

As an auditor inspecting traces, I want every custom MCP server to emit OpenTelemetry spans for tool executions with complete attribution and correlation attributes, so that tool calls appear in the caller's session trace with accurate lineage and timing.

- **AC-3.1** Given any tool execution on an instrumented MCP server, when the server completes the call, then it exports an OpenTelemetry span with `openinference.span.kind = "TOOL"`, `openinference.project.name = "academicOps"`, `tool.name` set to the invoked tool name, `service.name` set to the server's logical service name, and secret-scrubbed tool inputs and outputs in `input.value` and `output.value`.
- **AC-3.2** Given a tool execution with a resolved caller session, when the server exports the tool span, then `session.id` is set to the resolved session identifier, and `aops.session.source` is set to `"argument"`, `"meta"`, or `"header"`.
- **AC-3.3** Given a tool execution where no caller session could be resolved, when the server exports the tool span, then `session.id` remains unset, `mcp.session_id` records the transport connection ID, and `aops.session.source` is set to `"none"`.
- **AC-3.4** Given a tool execution with `agent_id` or `prompt_id` supplied in caller session metadata, when the server exports the tool span, then the span sets `agent.id` and `prompt.id`.
- **AC-3.5** Given a tool call that references a specific task, when the server exports the tool span, then `task.id` is set to the target task identifier.
- **AC-3.6** Given a request carrying W3C trace context (`traceparent`), when the server exports the tool span, then the tool span adopts the caller's `trace_id` and parents under the caller's tool invocation span.

### US-4 Fail-fast OpenTelemetry export configuration across language runtimes

As a platform operator deploying MCP servers in various runtime environments, I want servers in any language to use a uniform, fail-fast configuration contract for OpenTelemetry export, so that telemetry pipelines deploy reliably and configuration errors halt immediately at startup.

- **AC-4.1** Given an instrumented MCP server initializing telemetry, when resolving the collector OTLP traces endpoint, then the server resolves the endpoint in precedence order from `GENAI_ENGINE_ENDPOINT` followed by `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, and if neither variable is set, halts startup immediately with an explicit configuration error.
- **AC-4.2** Given an instrumented MCP server initializing telemetry with an endpoint configured, when configuring export credentials, then the server resolves authentication headers in precedence order from `GENAI_ENGINE_API_KEY` (formatted as comma-delimited `Key=Value` pairs) followed by `OTEL_EXPORTER_OTLP_HEADERS`.
- **AC-4.3** Given an instrumented MCP server exporting tool spans, when the collector endpoint is unreachable or span delivery encounters an error, then the server surfaces the export failure with diagnostic error details to standard error output.

## Design

### Calling Session Delivery and Resolution

MCP servers resolve the caller session through three delivery channels evaluated in strict priority order:

1. **Top-Level Tool Argument (`session_id`)**: String parameter carrying the caller's active `session_id` (resolved from `CLAUDE_CODE_SESSION_ID` / `CLAUDE_SESSION_ID` or `ANTIGRAVITY_CONVERSATION_ID`, falling back to hook stdin). Explicit per-call arguments take highest precedence to ensure caller subagent or prompt turn context is never masked by ambient connection transport headers.
2. **Request Metadata (`_meta.session_id`)**: JSON-RPC request metadata passed alongside stateless MCP `2026-07-28` request structures.
3. **Transport Header (`x-session-id`)**: Transport-level header passed on HTTP, Server-Sent Events (SSE), or WebSocket requests.

Every tool invocation is evaluated strictly per-request. The server sets `session.id` exclusively to an explicit caller session identifier resolved from sources 1–3 in priority order (`session_id` > `_meta.session_id` > `x-session-id`). When no explicit session identifier is present, `session.id` remains unset and `aops.session.source` is set to `"none"`. Transport connection identifiers remain confined to `mcp.session_id` and are never bound to caller sessions, eliminating session bleed across persistent connections, dev servers, or multiplexed clients.

```
Client Invocation (Direct)
  ├── Arguments: { "session_id": "..." }
  ├── Metadata: _meta.session_id
  └── Header: x-session-id
          │
          ▼
     MCP Server ──► Resolves session.id (Priority: Arg > Meta > Header)
          │
          ├── Extract session_id
          ├── Execute tool handler
          └── Export TOOL span to shared collector (session.id = caller session)
```

```
Client Invocation (Gateway / Portal)
  └── Tool Arguments: { "ServerName": "pkb", "Arguments": { "session_id": "..." } }
          │
          ▼
    Gateway Portal
          │
          ├── Extract session_id and traceparent
          └── Forward upstream with HTTP Header: x-session-id & traceparent
                  │
                  ▼
            Upstream Server
                  ├── Evaluates request per-call without connection binding
                  ├── Resolves session.id from Arguments.session_id or x-session-id header
                  └── Emits child TOOL span linked to caller trace
```

### Server Declaration and Schema Handling

To prevent client argument injection from breaking third-party servers or strict portal wrappers (`portal_*`) that enforce JSON Schema validation (`additionalProperties: false`):

1. **Acceptance Declaration**: PKB tools declare `session_id` in their tool input schemas (`properties.session_id` with schema `{ "type": "string" }`), and `PreToolUse` hooks inject `session_id` only on direct PKB tools and `call_mcp_tool` calls targeting `ServerName == "pkb"`.
2. **Portal Isolation**: Hooks do not inject top-level `session_id` onto `portal_codemode_execute` or other `portal_*` tools whose schemas reject unknown top-level parameters; inside codemode blocks, agents pass `session_id` directly to `pkb.*` calls.
3. **Gateway Header Translation**: Gateway proxies forward caller identity upstream via `x-session-id` and `traceparent` headers when proxying across connections.

### Span Attributes Specification

Tool execution spans emitted by custom MCP servers comply with OpenInference semantic conventions and framework attribution invariants:

| Attribute | Type | Requirement | Description |
| :- | :- | :- | :- |
| `openinference.span.kind` | string | Required | Must be `"TOOL"`. |
| `openinference.project.name` | string | Required | Must be `"academicOps"`. |
| `project.name` | string | Required | Must be `"academicOps"`. |
| `service.name` | string | Required | Logical service name of the MCP server (e.g. `polecat-mcp`, `custom-server`). |
| `aops.surface` | string | Required | Must be `"mcp-service"`. |
| `tool.name` | string | Required | The name of the executed MCP tool. |
| `tool.call_id` | string | Required | Transport call or message identifier for the invocation. |
| `session.id` | string | Conditional | Set to the 36-character caller session UUID when resolved. Omitted when unattributed. |
| `aops.session.source` | string | Required | Resolution source: `"argument"`, `"meta"`, `"header"`, or `"none"`. |
| `mcp.session_id` | string | Required | The underlying MCP transport connection identifier. Transport identifiers are recorded in `mcp.session_id` and kept distinct from `session.id`. |
| `agent.id` | string | Optional | Caller agent identifier when supplied in session metadata. |
| `prompt.id` | string | Optional | Caller prompt turn identifier when supplied in session metadata. |
| `task.id` | string | Optional | Target task identifier when the tool operation targets a task. |
| `input.value` | string | Required | JSON-serialized string of tool input arguments, scrubbed of credentials and secrets. |
| `output.value` | string | Required | JSON-serialized string of tool execution results, scrubbed of credentials and secrets. |

### Configuration and Export Guarantees

Custom MCP servers configure OpenTelemetry export using environment variables common across all language runtimes:

| Variable | Precedence | Purpose |
| :- | :- | :- |
| `GENAI_ENGINE_ENDPOINT` | 1 | Primary OTLP traces export URL (e.g. `https://otel.example.org/v1/traces` or `http://localhost:4318/v1/traces`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | 2 | Secondary OTLP traces export URL evaluated if `GENAI_ENGINE_ENDPOINT` is unset. |
| `GENAI_ENGINE_API_KEY` | 1 | Primary authentication credentials formatted as comma-delimited headers (`Key1=Value1,Key2=Value2`). |
| `OTEL_EXPORTER_OTLP_HEADERS` | 2 | Secondary OTLP headers evaluated if `GENAI_ENGINE_API_KEY` is unset. |
| `OTEL_SERVICE_NAME` | 1 | Logical service name for the server instance. |

#### Fail-Fast Startup and Export Reliability

Servers require an explicit OTLP endpoint to initialize telemetry. If neither `GENAI_ENGINE_ENDPOINT` nor `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is set, the server aborts startup immediately with an exit code and an error message identifying the missing configuration. When an export batch fails at runtime, the server surfaces the error to standard error output rather than discarding telemetry silently.
