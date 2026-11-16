---
name: phoenix
description: Query Arize Phoenix telemetry efficiently -- read built-in token and cost totals via GraphQL/SQL without whole-span fetches, generate condensed <slug>.outline.md session outlines from lean column projections, profile tool and upstream MCP calls, search across sessions, and inspect targeted spans, datasets, annotations, or prompts. Use when investigating session activity, decisions, bottlenecks, or token spend. Exclude for live container driving or tmux attachment (use debug); never falls back to local .jsonl logs.
---

# Phoenix Telemetry & Session Outlines

Query Arize Phoenix telemetry, audit built-in token spend and tool usage on the server, and generate readable, scannable session outlines from lean column projections without loading whole-span payload archives into context.

## 1. Core Query Discipline

- **Execute reads via authenticated Phoenix MCP**: Use `phoenix_execute` (Python code-mode calling `await call_tool("executeGraphqlQuery", {"query": ..., "variables": ...})`, `await call_tool("executeSql", {"sql": ...})`, and `await call_tool("describeSqlSchema", {})`) and structured Phoenix MCP tools. Surface errors verbatim; never fall back to local `.jsonl` files, invent default URLs, or guess project names.
- **Dialect and schema awareness**: Run `describeSqlSchema()` before writing custom SQL so queries match the active SQL dialect (SQLite vs PostgreSQL) and allowlisted schema (`spans.trace_id` and `spans.project_name` do not exist -- join `project_sessions -> projects -> traces -> spans`).
- **Query size & payload bounds**: Keep every SQL query statement <= 2,048 UTF-8 bytes. Bound cross-session scans on indexed `s.start_time`. Never select raw `s.attributes` or `s.events` blobs in list, cost, or outline queries. Keep code-mode returns compact (< 20 KB) by paging outline batches (`LIMIT 25` on `s.id > <cursor_id>`). `phoenix_execute` runs remotely inside the MCP server -- return compact structured rows to the agent and write files locally with native file tools.

## 2. Routing to Declarative Resources

Follow imperative procedural gating: load only the template needed for the task from `resources/`:

- For identifier resolution (`session.id` UUID, 6--8 char slug, 32-hex `trace_id`, or `task.id`), dual-emitter deduplication, and subagent correlation: read `resources/span-store.md`.
- For project-level spend (token totals, cost summaries, top models) or single-session cost: read `resources/session-costs.graphql` (`GetProjectCosts`, `GetSessionCosts` -- one operation per call, zero span fetches).
- For per-model spend (deduplicating dual-emitted model spans when multiple emitters cover a session) or per-tool / upstream MCP service call counts, latencies, errors, and payload bytes: read `resources/session-audit.sql`.
- For keyset-pageable, column-projected chronological steps: read `resources/session-outline.sql`.
- For task-level spend rollups or ranking top sessions by USD spend over a time window: read `resources/cost-by-task.sql`.
- For cross-session text/tool/error searches, subagent session discovery, or single-span payload drill-down: read `resources/cross-session-search.sql`.

## 3. Generating & Persisting `<slug>.outline.md`

Generate a single condensed outline `<slug>.outline.md` matching `specs/observability/decision-trace.md` (no full-payload transcript variant):

1. **Top-level heading & session header**:
   - `# Session Outline: <slug>` H1 heading.
   - Session header block: session ID, project name, UTC start/end timestamps and wall duration, turn/model/tool/error counts, built-in token breakdown (`input`, `cache_read`, `cache_write`, `output`) and comparable USD cost from `session-costs.graphql` or `session-audit.sql`, subagent labels, and Phoenix redirect link (`/redirects/sessions/<session_id>`) when UI URL is known.
2. **`## Overview` executive summary tables**:
   - `### Turns`: turn number linked to `#t<n>`, concise turn title (~5--8 words describing prompt intent to prevent wrapping), start UTC, duration, model calls, tool calls, output tokens, and turn cost.
   - `### Cost & Tool Profile`: per-model calls, tokens, and cost; plus per-tool / upstream MCP service call count, total and max latency, and error count from `session-audit.sql`.
   - `### Errors`: included when errors > 0, listing step anchor link `#t<n>-<m>`, failing span/tool name, and status message.
3. **Chronological turn sections (`<a id="t<n>"></a>`, `## Turn <n> · <title>`)**:
   - Turn metadata line with UTC timestamp, duration, model/tool counts, turn cost, and Phoenix `[session]` and root `[span]` (`/redirects/spans/<root_span_id>`) links when UI URL is known.
   - Substantive prompt blockquote (stripping `<system-reminder>`, `<skill>`, and `<ADDITIONAL_METADATA>` wrappers).
   - Ordered model prose steps (`<a id="t<n>-<m>"></a>`, `### <n>.<m>`) showing model, measured duration (omit duration when `latency_ms` is `NULL` from synthetic `<= 1.5ms` post-turn spans), cost, tokens, and assistant reasoning prose from `reasoning_excerpt` / `output_excerpt` (omitting raw tool-call JSON arrays, collapsing duplicate hook/native LLM pairs, omitting empty `### <n>.<m>` headings when a model step dispatches only tool calls with no prose, and trimming any truncated `...` excerpt back to the last complete word so sentences never cut mid-word).
   - Interleaved single-line tool and subagent bullets (`* <a id="t<n>-<m>"></a><n>.<m>`) showing action summary, tool/service name, duration, error status, and target path/command/arguments (collapsing embedded `\r`/`\n` to single spaces).
   - `### Turn <n> reply` blockquote when the turn's final response differs from the last model step's prose.

### Durable Persistence & Targeted Drill-Down

- **Durable persistence**: Save `<slug>.outline.md` to durable storage (knowledge note `out-<slug>` with literal `~/...` host paths sanitized, or committed to a designated repository path) -- never leave only in ephemeral container scratch.
- **Targeted drill-down**: When answering a decision question requires untruncated payload text at step `#t<n>-<m>`, execute Query 3 in `resources/cross-session-search.sql` for only that `span_id` and cite `#t<n>-<m>`.
