---
name: phoenix
description: Query Arize Phoenix telemetry efficiently -- read built-in token and cost totals via GraphQL/SQL without whole-span fetches, generate condensed <slug>.outline.md session outlines from lean column projections, profile tool and upstream MCP calls, search across sessions, and inspect targeted spans, datasets, annotations, or prompts. Use when investigating session activity, decisions, bottlenecks, or token spend. Exclude for live container driving or tmux attachment (use debug); never falls back to local .jsonl logs.
---

# Phoenix Telemetry & Session Outlines

Query Arize Phoenix telemetry, audit built-in token spend and tool usage on the server, and generate readable, scannable session outlines from lean column projections without loading whole-span payload archives into context.

## 1. Core Query Discipline

- **Authenticated MCP perimeter**: Execute all reads via `phoenix_execute` (or structured Phoenix MCP tools). Surface errors verbatim; never fall back to local `.jsonl` files, invent default URLs, or guess project names.
- **`phoenix_execute` sandbox syntax**: `phoenix_execute` runs **Python** where upstream Phoenix tools are invoked via `await call_tool('<toolName>', {...})`:
  ```python
  # pick one:
  res = await call_tool('describeSqlSchema', {})
  res = await call_tool('executeSql', {'sql': sql})
  res = await call_tool('executeGraphqlQuery', {'query': gql, 'variables': {...}})
  return res
  ```
  `executeSql` returns an error dictionary rather than raising -- always check `if 'error' in res:` before reading `res['rows']`. Keep sequential chunk loops inside one `phoenix_execute` call under ~60s total wall time; when invoked through a JS MCP code-mode portal, keep returned payloads compact (< 20 KB, since portals truncate around ~24 KB).
- **Dialect and schema awareness**: Run `describeSqlSchema()` before writing custom SQL so queries match the active SQL dialect (SQLite vs PostgreSQL) and allowlisted schema (`spans.trace_id` and `spans.project_name` do not exist -- join `project_sessions -> projects -> traces -> spans`).
- **SQL bounds, materialization & pagination**:
  - Keep every SQL statement strictly <= 2,048 UTF-8 bytes and never select raw `s.attributes` or `s.events` blobs in list, cost, or outline queries.
  - Bound cross-session scans on indexed `s.start_time`. Before applying `LIKE` or `LOWER` to `s.attributes`, narrow indexed `s.start_time` + `s.span_kind` (and `parent_id`/`name` filters) inside a `WITH ... AS MATERIALIZED (...)` CTE so SQLite does not parse JSON blobs across every span in the window.
  - Run heavy cross-session SQL scans sequentially rather than concurrently to avoid SQLite contention timeouts.
  - When keyset-paging with SQL `LIMIT N` on `s.id > <cursor_id>`, stop when `len(rows) < N` (not on `!row_count_is_partial`, which reflects only the server's 500-row cap).

## 2. Routing to Declarative Resources

Load only the resource needed for the task from `resources/`:

- **Schema, dialect, identifiers & subagent correlation**: read `resources/span-store.md` before writing custom SQL (`session.id`, slug, `trace_id`, `task.id`, allowed SQLite functions, dual-emitter deduplication).
- **Project or single-session built-in cost**: read `resources/session-costs.graphql` (`GetProjectCosts`, `GetSessionCosts` -- one operation per call, zero span fetches).
- **Session model spend & tool/MCP latency profile**: read `resources/session-audit.sql` (deduplicates dual-emitted model spans and aggregates tool/MCP calls, latencies, errors, and payload bytes).
- **Session outline steps**: read `resources/session-outline.sql` (keyset-pageable, column-projected chronological steps omitting raw tool output JSON, plus slug/`trace_id` resolution).
- **Task spend rollups & top sessions by USD**: read `resources/cost-by-task.sql` (uses built-in `span_costs`).
- **Multi-day spend by surface & model**: read `resources/spend-by-harness-model.sql` (server-side chunked sums with `llm.message.id` deduplication, plus zero-JSON daily `span_costs` rollups).
- **Cross-session prompt, error, tool-argument, subagent & single-span lookups**: read `resources/cross-session-search.sql` (`MATERIALIZED` user-prompt and tool-argument searches, error search, windowed sweeps, subagent discovery, and Query 3 single-span payload drill-down).

## 3. Generating & Persisting `<slug>.outline.md`

Generate a single condensed outline `<slug>.outline.md` using the layout below (no full-payload transcript variant) and write local files with native file tools:

1. **Top-level heading & session header**: `# Session Outline: <slug>`, followed by session ID, project, UTC start/end timestamps, wall duration, turn/model/tool/error counts, token breakdown (`input`, `cache_read`, `cache_write`, `output`), USD cost (`session-costs.graphql` or `session-audit.sql`), subagent labels, and Phoenix redirect (`/redirects/sessions/<session_id>`) when known.
2. **`## Overview` executive summary tables**:
   - `### Turns`: turn number linked to `#t<n>`, concise ~5-8 word title, start UTC, duration, model/tool counts, output tokens, and turn cost.
   - `### Cost & Tool Profile`: per-model calls, tokens, and cost, plus per-tool / upstream MCP call count, total/max latency, and error count from `session-audit.sql`.
   - `### Errors`: included when errors > 0, listing step link `#t<n>-<m>`, failing span/tool name, and status message.
3. **Chronological turn sections (`<a id="t<n>"></a>`, `## Turn <n> · <title>`)**:
   - Turn metadata line (UTC timestamp, duration, model/tool counts, turn cost, `[session]` and `[span]` `/redirects/spans/<root_span_id>` links when UI URL is known) and substantive prompt blockquote (stripping `<system-reminder>`, `<skill>`, and `<ADDITIONAL_METADATA>` wrappers).
   - Ordered model prose steps (`<a id="t<n>-<m>"></a>`, `### <n>.<m>`) showing model, measured duration (omit if `NULL`), cost, tokens, and assistant reasoning from `reasoning_excerpt` / `output_excerpt`.
   - Omit raw tool-call JSON and prose-free tool-only headings, collapse duplicate hook/native pairs, and trim truncated `...` excerpts back to the last complete word.
   - Interleaved single-line tool/subagent bullets (`* <a id="t<n>-<m>"></a><n>.<m>`) with action summary, tool/service, duration, error status, and single-line target/args, plus `### Turn <n> reply` blockquote when final reply differs from the last model step.

### Durable Persistence & Targeted Drill-Down

- **Durable persistence**: Save `<slug>.outline.md` to durable storage (knowledge note `out-<slug>` with `~/...` host paths sanitized, or committed to a designated repository path) -- never leave only in ephemeral scratch.
- **Targeted drill-down**: When answering a decision question requires untruncated payload text at step `#t<n>-<m>`, execute Query 3 in `resources/cross-session-search.sql` for that `span_id` only and cite `#t<n>-<m>`.
