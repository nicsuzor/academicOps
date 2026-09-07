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
