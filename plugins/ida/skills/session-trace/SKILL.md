---
name: session-trace
description: Export OpenTelemetry spans from Arize Phoenix to inspect session execution, tool calls, errors, latencies, token usage, or subagent dispatches. Use when reviewing session performance or resolving truncated values from transcripts. Not for live tails.
---

# Session Trace

Export OpenTelemetry spans from Phoenix for post-hoc session auditing. Phoenix retains untruncated tool calls, token usage, and subagent trees.

## Quick Start

```bash
export PHOENIX_BASE_URL=<url>
export PHOENIX_PROJECT_NAME=<project>

# List retained sessions
python3 scripts/phoenix_trace.py --list-sessions

# Export full trace or controller index
python3 scripts/phoenix_trace.py <session-id> --mode full --out ./traces
python3 scripts/phoenix_trace.py <session-id> --mode controller --out ./traces
python3 scripts/phoenix_trace.py <session-id> --mode full --resolve-orphan-parents --out ./traces
```

## Command Options

| Flag                       | Description                                                                        |
| -------------------------- | ---------------------------------------------------------------------------------- |
| `--mode`                   | Export format: `full`, `controller`, `markdown`, `all`, or `both` (default `both`) |
| `--out`                    | Output directory (default `$AOPS_SESSIONS/traces/`, else working directory)        |
| `--project`                | Phoenix project name (fallback `$PHOENIX_PROJECT_NAME`)                            |
| `--base-url`               | Phoenix base URL (fallback `$PHOENIX_BASE_URL` or `$PHOENIX_COLLECTOR_ENDPOINT`)   |
| `--transcript`             | Explicit path to `<base>.controller.md`                                            |
| `--tolerance-ms`           | Transcript join window in milliseconds (default `500`)                             |
| `--page-limit`             | Spans requested per API page (default `1000`)                                      |
| `--from-file`              | Load spans from local JSON payload instead of server                               |
| `--no-contamination-check` | Skip trace contamination check                                                     |
| `--resolve-orphan-parents` | Fetch missing parent spans for orphan nodes                                        |
| `--list-sessions`          | List retained sessions with timestamps and span counts                             |

## Token Cost by Session / Task

`scripts/phoenix_token_cost.py` prints one screen of token usage and estimated USD per session (or per session x task), ranked by cost. It reads the Phoenix REST API only (`GET /v1/projects/{id}/spans?span_kind=LLM&start_time=&end_time=`, paged on `next_cursor`), so it runs anywhere Phoenix is reachable over HTTP; the Phoenix MCP is not required.

```bash
# Today, Brisbane time, per session
python3 scripts/phoenix_token_cost.py --since "2026-09-12 00:00" --tz +10:00

# Split each session across the PKB tasks it touched; machine-readable
python3 scripts/phoenix_token_cost.py --since 2026-09-11T14:00:00Z --by task --json

# Markdown table for pasting onto a task node; keep the raw spans for an offline rerun
python3 scripts/phoenix_token_cost.py --since "2026-09-12 00:00" --tz +10:00 --markdown --save-spans spans.json
python3 scripts/phoenix_token_cost.py --since "2026-09-12 00:00" --tz +10:00 --from-file spans.json
```

| Flag                           | Description                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| `--since`                      | Window start: ISO-8601, or `YYYY-MM-DD [HH:MM]` read in `--tz` (required)             |
| `--until`                      | Window end (default: now)                                                             |
| `--tz`                         | Offset for naive `--since`/`--until`, e.g. `+10:00` (default `+00:00`)                |
| `--by`                         | Row grain: `session` (default) or `task`                                              |
| `--session`                    | Restrict to one session id (prefix accepted)                                          |
| `--labels`                     | JSON file mapping session-id prefix to an agent/role label                            |
| `--prices`                     | JSON file of `model -> {in, out, cache_read, cache_write}` USD/M, overriding `PRICES` |
| `--json` / `--markdown`        | Output shape (default: fixed-width screen)                                            |
| `--save-spans` / `--from-file` | Persist the fetched spans, or rerun from a saved file offline                         |

Method, in brief (the script docstring has the full account):

- `LLM` spans: `llm.model_name`, `llm.token_count.prompt` (includes cache tokens), `.completion`, `.prompt_details.cache_read`, `.prompt_details.cache_write`. Fresh input is `prompt - cache_read - cache_write`.
- Exact re-emissions (same `session.id`, `start_time`, `output.value`; about a sixth of Opus spans) are collapsed before summing.
- `session.id` is the unit; subagents inherit it. `task.id` / `tag.task_id` are the constant `academicOps`, so the task column comes from `TOOL` spans (`claim_task`, `release_task`, `get_task`, `update_task`, `append`, ...) whose `input.value` names an id. `--by task` attributes each LLM call to the task most recently claimed, else read, before it.
- Agent/role is a label: `--labels` file, else the name the session printed in a `ListAgents` call, else the channel it fronts, else its first human prompt in the window.
- Gemini spans carry no token counts and appear as calls only. Unpriced models cost 0 and are named in the footer.
- Prices are Anthropic list prices per million tokens (cache read 0.1x input, 5-minute cache write 1.25x). Claude Code subscription usage is not invoiced at these rates; the USD column is comparable spend, not a bill.

## Span Data Reference

| Kind    | Target Fields                                                                   |
| ------- | ------------------------------------------------------------------------------- |
| `TOOL`  | `tool.name`, `input.value`, `output.value`, `tool.json_schema`                  |
| `LLM`   | `llm.model_name`, `llm.token_count.*`, `llm.prompt_details.*`                   |
| `AGENT` | `agent.name`, `input.value` (dispatch prompt), `output.value` (status ack)      |
| `CHAIN` | `claude-code-turn` turn root, prompt in `input.value`, result in `output.value` |

Output produces `<session-id>.trace.json` (`full` forest with `roots` and `orphans`) and `<session-id>.trace.controller.json` (`controller` summary). In controller exports, `session_*` fields aggregate all subagent work, while `controller_*` fields isolate the root turn.

## Review Checklist

1. **Errors**: Check `meta.session_error_count` and inspect spans with `status_code == "ERROR"`.
2. **Orphans**: Review `orphans` array for unattached spans; use `--resolve-orphan-parents` if needed.
3. **Contamination**: Check `meta.trace_contamination` to verify no cross-session span mixing.
4. **Token spend**: Compare `prompt` vs `cache_read` in `meta.session_token_totals`.
5. **Subagents**: Rank `subagents[]` by `collapsed_span_count` to identify expensive execution branches.
6. **Large payloads**: Inspect spans with high `input_chars` or `output_chars` in full export.

## Key Constraints

- Filter on `session.id`, never `trace_id` (a trace can span multiple sessions).
- Root `CHAIN` spans have null parent IDs. Subagent spans carry `agent.id` and the root `session.id`.
- Match short session slugs (e.g. `413914d7`) via `--list-sessions` to find the full UUID.
