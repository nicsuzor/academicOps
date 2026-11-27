# Phoenix Span Store Architecture & Query Reference

Arize Phoenix persists OpenTelemetry traces, spans, evaluations, and datasets.

## Identifier Shapes

- `session.id`: Full UUID (e.g. `00000000-0000-0000-0000-000000000000`) identifying a continuous conversation.
- `slug`: 6-8 character prefix of `session.id` used in filenames (e.g. `<slug>.outline.md`).
- `trace_id`: 32-character lowercase hex string identifying an OTel distributed trace.
- `span_id`: 16-character lowercase hex string identifying an individual span.
- `task_id`: Framework task identifier recorded in span attributes (`task.id` or `tag.task_id`).

## Executing via `phoenix_execute`

`phoenix_execute` runs a **Python** async sandbox calling upstream tools via `await call_tool('<toolName>', {...})` (`describeSqlSchema`, `executeSql`, `executeGraphqlQuery`, `getSpans`). Always check `if "error" in res:` before reading `res["rows"]`. For multi-chunk sweeps, loop sequentially inside `phoenix_execute` (keeping total wall time under ~60s) rather than firing concurrent heavy SQL scans that contend on SQLite, and keep portal returns < 20 KB.

## Session Grouping vs Trace ID

Multi-turn client conversations group by `session.id` via `project_sessions`, not `trace_id`:

- **One trace per turn**: In multi-turn sessions, client harnesses emit a fresh `trace_id` per turn. Filtering by `trace_id` yields only a single turn rather than the full session.
- **Cross-service propagation**: A single trace can span across external service boundaries. `project_sessions.session_id` provides the true boundary of user-agent interaction.

## Schema, Indexing & Query Limits

- Run `describeSqlSchema()` before writing custom SQL. Analytics SQL executes against SQLite (or PostgreSQL on remote backends) with automatic JSON extraction rewrites (`attributes ->> '$.field'`).
- Columns `spans.trace_id` and `spans.project_name` do not exist directly on `spans`: join `project_sessions -> projects -> traces -> spans`.
- Statement length ceiling: Every SQL query must be strictly <= 2,048 UTF-8 bytes.
- Paging & payload limits: Default `row_limit` is 500 (max 5,000). `row_count_is_partial` is `true` only when the server's `row_limit` or response-byte cap is reached. When keyset-paging on `s.id > <cursor_id>` with a smaller SQL `LIMIT N` (such as `LIMIT 25`), stop when `len(rows) < N`, not on `!row_count_is_partial`. Never select unbounded `s.attributes` or `s.events` JSON blobs in list queries.
- Indexed scans & `MATERIALIZED` CTEs: `spans.start_time` is indexed, whereas `spans.attributes` and `spans.name` are not. Putting `s.attributes->>'$.input.value' LIKE ...` directly in `WHERE` causes SQLite to parse JSON blobs on every span in the window and time out (~30-60s). Instead, filter `s.start_time`, `s.span_kind`, `s.parent_id`, and `s.name` exclusions inside a `WITH ... AS MATERIALIZED (...)` CTE first, then apply `LIKE`/`LOWER` in the outer `SELECT`.
  - Root `CHAIN` spans are sparse (~200-600/day): a `MATERIALIZED` prompt search spans 1-2 weeks in a single call (~4-6s).
  - `TOOL` and `LLM` spans are ~10-50x denser: chunk by 2h-6h on busy days (up to 24h on quiet days) and run chunks sequentially.
  - `span_costs` queries with no `spans.attributes` reads run fast in 1-day chunks (~2s/day).

## Allowed SQL Dialect and Functions

Verified against Phoenix `executeSql` and `describeSqlSchema`:

- **String & matching**: `SUBSTR`, `SUBSTRING`, `LENGTH`, `CHAR_LENGTH`, `CHARACTER_LENGTH`, `LOWER`, `UPPER`, `LIKE`, `GLOB`, and the `||` concatenation operator.
- **Aggregates & statistics**: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `GROUP_CONCAT`, `STRING_AGG`, `MEDIAN`, `PERCENTILE(x, p)` (`p` in `0-100`; `percentile_cont` is PostgreSQL-only).
- **JSON**: `JSON`, `JSON_EXTRACT` (and `->` / `->>`), `JSON_TYPE`, `JSON_VALID`, `JSON_ARRAY_LENGTH`, `JSON_OBJECT`, `JSON_ARRAY`, `JSON_GROUP_ARRAY`, `JSON_GROUP_OBJECT`, `JSON_EACH`.
- **Math**: `ROUND`, `ABS`, `CEIL`, `CEILING`, `FLOOR`, `SIGN`, `MOD`.
- **Conditional & type**: `COALESCE`, `IFNULL`, `NULLIF`, `TYPEOF`, `CAST` (use `CASE WHEN` for conditional branching).
- **Date & time**: `DATE`, `DATETIME`, `UNIXEPOCH`, `JULIANDAY`, `STRFTIME`, `TIME_PARSE`, `TIME_TRUNC`, `TIME_SUB`, `TIME_FMT_DATETIME`.
- **Window**: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `PERCENT_RANK`, `CUME_DIST`, `NTILE`, `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE`.
- **Rejected (`function_not_allowed`)**: `INSTR`, `REPLACE`, `TRIM`, `LTRIM`, `RTRIM`, `CONCAT`, `CONCAT_WS`, `PRINTF`, `FORMAT`, `HEX`, `UNHEX`, `UNICODE`, `CHAR`, `QUOTE`, `REGEXP` / `REGEXP_LIKE`, `OCTET_LENGTH`, `IIF`, `TOTAL`, `STDDEV`, `SQRT`, `POW` / `POWER`, `LN`, `LOG` / `LOG10`, `EXP`, `RANDOM`, `CHANGES`, `SQLITE_VERSION`, and `TEXT_*` (`sqlean` text helpers). When a query fails with `function_not_allowed` on string manipulation, match and slice with `LIKE`, `GLOB`, `SUBSTR`/`SUBSTRING`, `LOWER`/`UPPER`, and `CASE WHEN`, or filter projected rows in code mode.

## Dual-Emitter Deduplication & Subagent Correlation

- **Dual-emitter deduplication**: When both framework tracer hooks (`claude/*` spans carrying prose steps) and native runtime telemetry (`claude_code.llm_request` spans carrying priced token usage) emit on a session across separate traces, outlines merge assistant prose with token metrics while cost queries exclude `s.name LIKE 'claude/%'` on sessions containing `claude_code.llm_request` to prevent double-counting. On deployments without dual emitters, those predicates evaluate to false and act as neutral no-ops.
- **Built-in pricing**: Phoenix prices spans server-side into `span_costs` / `span_cost_details` via `generative_models` and `token_prices`. Prefer `span_costs` / GraphQL `costSummary` over maintaining custom model price tables.
- **Subagent correlation**:
  - Shared-session subagents: In-process subagents emit spans under the parent's `session.id`.
  - Isolated-session subagents: Subagents running in distinct child conversations record `invoke_subagent` / `Agent` tool spans on the parent session with the child `conversationId` in the tool output. A non-blocking parent dispatch span's duration measures launch time rather than child wall-clock runtime.
  - Discover child sessions by querying `invoke_subagent` spans on the parent or querying `project_sessions` starting within the parent's execution window.

## Other Phoenix MCP Tool Groups

- **Annotations**: `listSpanAnnotations` and `upsertSpanAnnotations` for ground-truth labels, review scores, or error classifications.
- **Datasets & Experiments**: `listDatasets`, `getDataset`, and experiment evaluation runners for offline benchmarking and prompt evaluations.
- **Prompts**: `listPrompts` and prompt version tracking for versioned prompt templates.
