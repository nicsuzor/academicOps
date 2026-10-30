---
title: Caller-session tracing contract for MCP servers
status: ready
---

# Caller-session tracing contract for MCP servers

Every custom Model Context Protocol (MCP) server and gateway portal exports OpenTelemetry tool-call spans to the shared collector and attributes each execution to the calling agent session. The contract applies to servers and gateways implemented in any language runtime, ensuring that direct invocations and gateway-routed calls appear in the caller's session trace with complete attribution, secret-scrubbed payloads, and unambiguous provenance.

## User stories

### US-1 Receive and resolve caller session direct and through gateway portals

As a platform operator, I want custom MCP servers and gateway proxies to receive and propagate caller session identity across direct and multiplexed connections, so that downstream tool executions attach to the originating agent session without synthetic transport sessions.

- **AC-1.1** Given a direct tool call carrying a caller session identifier via `x-session-id` transport header, `_meta.session_id` request metadata, or the reserved `_session` argument object (`{ session_id, agent_id?, prompt_id? }`), when the server receives the call, then the server resolves the caller session identifier from the highest-priority source present in precedence order: `x-session-id`, `_meta.session_id`, `_session`.
- **AC-1.2** Given a client invoking a tool through a gateway proxy, when the gateway forwards the call to an upstream server, then the gateway extracts the caller session identifier from the incoming call and forwards it upstream in the `x-session-id` transport header along with W3C `traceparent` context.
- **AC-1.3** Given an upstream server receiving a request from a gateway client connection, when the server processes the call, then it resolves the caller session from the forwarded `x-session-id` header or request metadata for that call without binding the gateway connection to any single session.
- **AC-1.4** Given a direct stateful transport connection where an earlier request established an explicit session identifier, when a subsequent request arrives on the same connection without an explicit session identifier, then the server attributes the call to the bound session identifier.
- **AC-1.5** Given a stateless or gateway connection where a request arrives without an explicit session identifier, when the server processes the call, then the call remains unattributed with `aops.session.source = "none"` and no connection binding is created.

### US-2 Declare caller session acceptance and preserve tool schemas

As a client or gateway dispatcher, I want MCP servers to declare whether their tools accept caller session arguments and strip internal session objects before tool execution, so that domain schemas remain strict while session attribution succeeds without schema validation errors.

- **AC-2.1** Given an MCP server that supports caller session arguments, when the server responds to client initialization or advertises its tool listings, then the server indicates caller session support via capability declarations, by defining the optional `_session` parameter in tool input schemas, or by permitting additional properties.
- **AC-2.2** Given an MCP server that supports caller session arguments, when a tool call containing `_session` arrives, then the server extracts and removes `_session` prior to executing domain parameter validation, allowing strict domain schema validation to pass.
- **AC-2.3** Given an MCP server that enforces strict argument validation without declaring caller session support, when a client or gateway dispatches a tool call to that server, then the caller passes session identity exclusively via the `x-session-id` transport header or request metadata and omits `_session` from the tool arguments payload.

### US-3 Emit standardized OpenTelemetry tool spans with attribution attributes

As an auditor inspecting traces, I want every custom MCP server to emit OpenTelemetry spans for tool executions with complete attribution and correlation attributes, so that tool calls appear in the caller's session trace with accurate lineage and timing.

- **AC-3.1** Given any tool execution on an instrumented MCP server, when the server completes the call, then it exports an OpenTelemetry span with `openinference.span.kind = "TOOL"`, `openinference.project.name = "academicOps"`, `tool.name` set to the invoked tool name, `service.name` set to the server's logical service name, and secret-scrubbed tool inputs and outputs in `input.value` and `output.value`.
- **AC-3.2** Given a tool execution with a resolved caller session, when the server exports the tool span, then `session.id` is set to the resolved session identifier, and `aops.session.source` is set to `"header"`, `"meta"`, `"argument"`, or `"binding"`.
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

MCP servers resolve the caller session through four delivery channels evaluated in strict priority order:

1. **Transport Header (`x-session-id`)**: Transport-level header passed on HTTP, Server-Sent Events (SSE), or WebSocket requests. This is the primary channel used by gateways and HTTP clients.
2. **Request Metadata (`_meta.session_id`)**: JSON-RPC request metadata passed alongside standard MCP request structures.
3. **Reserved Tool Argument (`_session`)**: Injected dictionary parameter carrying `{ "session_id": "<uuid>", "agent_id": "<optional>", "prompt_id": "<optional>" }`.
4. **Connection Binding**: For direct stateful transport connections identified by a transport connection identifier (`Mcp-Session-Id`), the server binds the connection to the most recently resolved explicit session.

Only sources 1–3 establish or update a connection binding. The server sets `session.id` exclusively to an explicit caller session identifier resolved from sources 1–3; when no source is present, `session.id` remains unset and `aops.session.source` is set to `"none"`. Transport identifiers remain confined to `mcp.session_id`.

```
Client Invocation (Direct)
  ├── Header: x-session-id
  ├── Metadata: _meta.session_id
  └── Arguments: { "_session": { "session_id": "..." } }
          │
          ▼
     MCP Server ──► Resolves session.id (Priority: Header > Meta > Arg > Binding)
          │
          ├── Strip _session from arguments
          ├── Execute tool handler
          └── Export TOOL span to shared collector (session.id = caller session)
```

```
Client Invocation (Gateway / Portal)
  └── Tool Arguments: { "_session": { "session_id": "..." } }
          │
          ▼
    Gateway Portal
          │
          ├── Extract session_id and traceparent
          ├── Omit _session if upstream does not accept it
          └── Forward upstream with HTTP Header: x-session-id & traceparent
                  │
                  ▼
            Upstream Server
                  ├── Never binds gateway connection
                  ├── Resolves session.id from x-session-id header
                  └── Emits child TOOL span linked to caller trace
```

### Connection Classification and Gateway Multiplexing

Servers classify incoming transport connections into three distinct categories to avoid session bleed across multiplexed clients:

| Connection Class | Identification | Binding Behavior |
| :- | :- | :- |
| **Direct Stateful** | Standard MCP client connection (`Mcp-Session-Id`) not matching any gateway client identifier. | Bound to the most recent explicit session identifier. Subsequent requests lacking explicit session inherit the bound session with `aops.session.source = "binding"`. If a new explicit session arrives, the binding updates and records `aops.session.rebound_from`. |
| **Gateway Multiplexed** | Connection whose client identifier during `initialize` or transport headers matches an entry in `MCP_GATEWAY_CLIENTS`. | Evaluated independently per request without connection binding. Every request must supply its own explicit session identifier. Calls lacking an explicit session resolve to `aops.session.source = "none"`. |
| **Stateless One-Shot** | Request arriving on stateless endpoints without persistent transport session tracking. | Evaluated independently per request without connection binding. Every request is evaluated from its headers, metadata, or arguments. Calls lacking an explicit session resolve to `aops.session.source = "none"`. |

### Server Declaration and Schema Handling

To prevent client argument injection from breaking third-party servers that enforce strict JSON Schema validation (`additionalProperties: false`):

1. **Acceptance Declaration**: Servers declare support for caller session injection by:
   - Defining `_session` in tool parameter schemas under `properties._session` with schema `{ "type": "object", "description": "Caller session context" }`; or
   - Setting `additionalProperties: true` in tool parameter schemas; or
   - Advertising caller session support in server capabilities during protocol initialization (`capabilities.experimental.callerSession = true`).
2. **Pre-Validation Stripping**: Servers that accept `_session` must extract and remove the `_session` key from input arguments before handing arguments to domain parameter validators or business logic handlers.
3. **Client / Gateway Filtering**: Clients and gateway proxies only inject `_session` into argument dictionaries when targeting servers that declare acceptance. For all other servers, callers convey session identity exclusively through transport headers (`x-session-id`) or request metadata (`_meta.session_id`).

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
| `aops.session.source` | string | Required | Resolution source: `"header"`, `"meta"`, `"argument"`, `"binding"`, or `"none"`. |
| `mcp.session_id` | string | Required | The underlying MCP transport connection identifier. Transport identifiers are recorded in `mcp.session_id` and kept distinct from `session.id`. |
| `agent.id` | string | Optional | Caller agent identifier when supplied in session metadata. |
| `prompt.id` | string | Optional | Caller prompt turn identifier when supplied in session metadata. |
| `task.id` | string | Optional | Target task identifier when the tool operation targets a task. |
| `input.value` | string | Required | JSON-serialized string of tool input arguments, scrubbed of credentials and secrets. |
| `output.value` | string | Required | JSON-serialized string of tool execution results, scrubbed of credentials and secrets. |
| `aops.session.rebound_from` | string | Optional | Previous session identifier if a direct connection was rebound to a new session. |

### Configuration and Export Guarantees

Custom MCP servers configure OpenTelemetry export using environment variables common across all language runtimes:

| Variable | Precedence | Purpose |
| :- | :- | :- |
| `GENAI_ENGINE_ENDPOINT` | 1 | Primary OTLP traces export URL (e.g. `https://otel.example.org/v1/traces` or `http://localhost:4318/v1/traces`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | 2 | Secondary OTLP traces export URL evaluated if `GENAI_ENGINE_ENDPOINT` is unset. |
| `GENAI_ENGINE_API_KEY` | 1 | Primary authentication credentials formatted as comma-delimited headers (`Key1=Value1,Key2=Value2`). |
| `OTEL_EXPORTER_OTLP_HEADERS` | 2 | Secondary OTLP headers evaluated if `GENAI_ENGINE_API_KEY` is unset. |
| `OTEL_SERVICE_NAME` | 1 | Logical service name for the server instance. |
| `MCP_GATEWAY_CLIENTS` | 1 | Comma-separated client identifiers treated as multiplexing gateways (disabling connection binding). |

#### Fail-Fast Startup and Export Reliability

Servers require an explicit OTLP endpoint to initialize telemetry. If neither `GENAI_ENGINE_ENDPOINT` nor `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is set, the server aborts startup immediately with an exit code and an error message identifying the missing configuration. When an export batch fails at runtime, the server surfaces the error to standard error output rather than discarding telemetry silently.
