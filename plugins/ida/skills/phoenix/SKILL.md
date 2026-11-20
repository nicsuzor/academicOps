---
name: phoenix
description: Query Arize Phoenix telemetry efficiently -- read built-in token and cost totals via GraphQL/SQL without whole-span fetches, generate condensed <slug>.outline.md session outlines from lean column projections, profile tool and upstream MCP calls, search across sessions, and inspect targeted spans, datasets, annotations, or prompts. Use when investigating session activity, decisions, bottlenecks, or token spend. Exclude for live container driving or tmux attachment (use debug); never falls back to local .jsonl logs.
---

# Phoenix Telemetry & Session Outlines

Query Arize Phoenix telemetry, audit built-in token spend and tool usage on the server, and generate readable, scannable session outlines from lean column projections without loading whole-span payload archives into context.

## 1. Core Query Discipline

- **Execute reads via authenticated Phoenix MCP**: Use `phoenix_execute` (calling `executeGraphqlQuery`, `executeSql`, and `describeSqlSchema`) and structured Phoenix MCP tools. Surface errors verbatim; never fall back to local `.jsonl` files, invent default URLs, or guess project names.
- **Dialect and schema awareness**: Run `describeSqlSchema()` before writing custom SQL so queries match the active SQL dialect (SQLite vs PostgreSQL) and allowlisted schema (`spans.trace_id` and `spans.project_name` do not exist -- join `project_sessions -> projects -> traces -> spans`).
- **Query size & payload bounds**: Keep every SQL query <= 2,048 UTF-8 bytes, bound cross-session scans on indexed `s.start_time`, and never select raw `s.attributes` or `s.events` blobs in list, cost, or outline queries. Keep code-mode returns compact (< 20 KB) by paging outline batches (`LIMIT 25` on `s.id > <cursor_id>`), and write local files with native file tools.

## 2. Routing to Declarative Resources

Load only the resource needed for the task from `resources/`:

- For identifier resolution (`session.id` UUID, 6-8 char slug, 32-hex `trace_id`, or `task.id`), dual-emitter deduplication, client-specific span storage/emitter details, and subagent correlation: read `resources/span-store.md` before querying.
- For project-level spend (token totals, cost summaries, top models) or single-session cost: read `resources/session-costs.graphql` (`GetProjectCosts`, `GetSessionCosts` -- one operation per call, zero span fetches).
- For per-model spend (deduplicating dual-emitted model spans) or per-tool / upstream MCP service call counts, latencies, errors, and payload bytes: read `resources/session-audit.sql`.
- For keyset-pageable, column-projected chronological steps: read `resources/session-outline.sql`.
- For task-level spend rollups or ranking top sessions by USD spend over a window: read `resources/cost-by-task.sql`.
- For spend per harness (`aops.surface`) and model over a long window (a week), with nested cache keys (`llm.token_count.prompt_details.cache_read` / `.cache_write`): read `resources/spend-by-harness-model.sql`, or run `uv run python "${CLAUDE_SKILL_DIR:-plugins/ida/skills/phoenix}/scripts/phoenix_token_cost.py" --since <time> --by harness-model` (server-side sums in adaptive time chunks, halved on timeout, deduped on `llm.message.id`). Keep `--by session` (default) or `--by task` to a few hours because they download every span in the window. Prices are comparable list prices per million tokens (per-call long-context tiers do not apply in `--by harness-model` rollups); if you need client-specific emitter or model-alias mapping details, read `resources/span-store.md` before computing totals.
- For cross-session text/tool/error searches, windowed user-prompt and reply sweeps, subagent session discovery, or single-span payload drill-down: read `resources/cross-session-search.sql`.

Note: Phoenix holds nothing before 2026-11-12 01:39 UTC, so older windows return empty chunks.

## 3. Generating & Persisting `<slug>.outline.md`

Generate a single condensed outline `<slug>.outline.md` using the layout below (no full-payload transcript variant):

1. **Top-level heading & session header**: `# Session Outline: <slug>`, followed by session ID, project name, UTC start/end timestamps, wall duration, turn/model/tool/error counts, token breakdown (`input`, `cache_read`, `cache_write`, `output`), comparable USD cost from `session-costs.graphql` or `session-audit.sql`, subagent labels, and Phoenix redirect link (`/redirects/sessions/<session_id>`) when UI URL is known.
2. **`## Overview` executive summary tables**:
   - `### Turns`: turn number linked to `#t<n>`, concise ~5-8 word title, start UTC, duration, model/tool counts, output tokens, and turn cost.
   - `### Cost & Tool Profile`: per-model calls, tokens, and cost, plus per-tool / upstream MCP call count, total/max latency, and error count from `session-audit.sql`.
   - `### Errors`: included when errors > 0, listing step link `#t<n>-<m>`, failing span/tool name, and status message.
3. **Chronological turn sections (`<a id="t<n>"></a>`, `## Turn <n> · <title>`)**:
   - Turn metadata line (UTC timestamp, duration, model/tool counts, turn cost, `[session]` and `[span]` `/redirects/spans/<root_span_id>` links when UI URL is known) and substantive prompt blockquote (stripping `<system-reminder>`, `<skill>`, and `<ADDITIONAL_METADATA>` wrappers).
   - Ordered model prose steps (`<a id="t<n>-<m>"></a>`, `### <n>.<m>`) showing model, measured duration (omit when `latency_ms` is `NULL`), cost, tokens, and assistant reasoning prose from `reasoning_excerpt` / `output_excerpt` (omitting raw tool-call JSON, collapsing duplicate hook/native pairs, omitting prose-free tool-only headings, and trimming truncated `...` excerpts back to the last complete word).
   - Interleaved single-line tool/subagent bullets (`* <a id="t<n>-<m>"></a><n>.<m>`) with action summary, tool/service, duration, error status, and single-line target/args, plus `### Turn <n> reply` blockquote when final reply differs from the last model step.

### Durable Persistence & Targeted Drill-Down

- **Durable persistence**: Save `<slug>.outline.md` to durable storage (knowledge note `out-<slug>` with `~/...` host paths sanitized, or committed to a designated repository path) -- never leave only in ephemeral scratch.
- **Targeted drill-down**: When answering a decision question requires untruncated payload text at step `#t<n>-<m>`, execute Query 3 in `resources/cross-session-search.sql` for that `span_id` only and cite `#t<n>-<m>`.
