# Dashboard Data Pipeline Architecture

> Decision recorded 2026-03-08. Supersedes the old Python bridge (`dump_dashboard_data.py`).

## Pipeline Flow

1. **`/dump` skill** → writes per-session summary to `$ACA_DATA/dashboard/sessions/{hash}.summary.json` via `aops-core/lib/session_summary.py`
2. **Cross-machine aggregation** → script does mechanical merge of session summaries from all machines; `/daily` does interpretive synthesis
3. **`/daily` (or script)** → writes `$ACA_DATA/dashboard/synthesis.json` with keys: narrative, accomplishments, alignment, context, waiting_on, skill_insights, suggestion
4. **Dashboard reads** → `synthesis.json` + session summaries + live session state

## Data Sources

| Panel              | Source                               |
| ------------------ | ------------------------------------ |
| Current Activity   | `sessions/status/*.json` (last 1h)   |
| Where You Left Off | Session state files (last 24h)       |
| LLM Synthesis      | `$ACA_DATA/dashboard/synthesis.json` |
| Daily Story        | Session transcripts                  |

## Key Files

- `aops-core/lib/session_summary.py` — `SessionSummary` TypedDict, `save_session_summary()`, `synthesize_session()`
- `$ACA_DATA/dashboard/synthesis.json` — aggregated synthesis output

## SvelteKit Migration

The SvelteKit rewrite needs to expose these same data sources via SvelteKit API routes (`+server.ts`) or static JSON generation. The Python bridge was removed (2026-03-07). Options:

1. **SvelteKit API routes** (`+server.ts`) — fetch from files at request time
2. **Static JSON generation** — pre-build dashboard data alongside `tasks.json`
3. **Direct PKB MCP integration** — browser-side MCP client (if feasible)

See also: `qa/svelte-dashboard-qa-results-2026-03-07.md` (P1 issue — dashboard panels empty)
