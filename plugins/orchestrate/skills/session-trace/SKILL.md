---
name: session-trace
description: Export one session's OpenTelemetry spans from an Arize Phoenix span store and read them as evidence — a full nested export of every span, plus a controller-only export with subagent work collapsed into a dispatch index. Use when asked to pull, export, or review a session trace by session id or short slug; to establish what a session actually did; to audit its tool calls, errors, latencies, token spend, or subagent dispatches; or when the markdown transcript truncated a value you need whole. Not for reading markdown transcripts, and not a live tail — it reads a span store after the fact.
---

# Session Trace

Phoenix holds the higher-fidelity record: attribute values are stored whole, so
a tool output the markdown transcript truncated is complete here. One fetch
yields two shapes:

- **full** — every span verbatim, nested into a `parent_id` forest, plus, under
  `orphans`, the spans no root reaches. Always a partition of the fetch.
- **controller** — the controller trunk only, with subagent work collapsed into
  a dispatch index. Its counts are named `session_*` and `controller_*` so the
  two populations never blur.

## Quick start

```bash
export PHOENIX_BASE_URL=<phoenix-base-url>
export PHOENIX_PROJECT_NAME=<phoenix-project>

# What the server still holds
python3 scripts/phoenix_trace.py --list-sessions

python3 scripts/phoenix_trace.py <session-id> --mode full --out ./traces
python3 scripts/phoenix_trace.py <session-id> --mode controller --out ./traces
python3 scripts/phoenix_trace.py <session-id> --mode markdown --out ./transcripts
python3 scripts/phoenix_trace.py <session-id> --mode all --out ./traces

# A one-off project, without touching the environment
python3 scripts/phoenix_trace.py <session-id> --project <phoenix-project> --out ./traces

# Explain the orphans: fetch the parent spans they point at, tagged with their owner
python3 scripts/phoenix_trace.py <session-id> --mode full --resolve-orphan-parents --out ./traces
```

Output lands as `<session-id>.trace.json` and
`<session-id>.trace.controller.json`.

Both the base URL and the project are required and neither has a default. Absent
one, the exporter exits non-zero naming the flag and the variable, and — when
the server is reachable — the projects it actually holds.

## Options

| Flag                       | Effect                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| `--mode`                   | `full`, `controller`, `markdown`, `all`, or `both` (default `both`)                              |
| `--out`                    | output directory; defaults to `$AOPS_SESSIONS/traces/`, else the working dir                     |
| `--project`                | Phoenix project name or id; required, falls back to `$PHOENIX_PROJECT_NAME`                      |
| `--base-url`               | Phoenix base URL; required, falls back to `$PHOENIX_BASE_URL` then `$PHOENIX_COLLECTOR_ENDPOINT` |
| `--transcript`             | explicit path to the session's `<base>.controller.md`; otherwise found under `$AOPS_SESSIONS`    |
| `--tolerance-ms`           | transcript join window in milliseconds (default `500`)                                           |
| `--page-limit`             | spans requested per API page (default `1000`); lower it to exercise paging                       |
| `--from-file`              | read spans from a saved JSON payload instead of the server                                       |
| `--no-contamination-check` | skip `meta.trace_contamination`, saving one batched span query                                   |
| `--resolve-orphan-parents` | fetch the parents `parent_not_in_fetch` orphans point at, into `foreign_parents`                 |
| `--list-sessions`          | list retained sessions with start, end, and trace count                                          |

## Reading the output

In the **full** export, `meta` carries `span_count`, `trace_count`,
`time_range`, `span_kind_counts`, `status_counts`, `error_count`,
`token_totals`, `fetch_pages`, and the transcript paths used. That document
holds the whole session, so the bare names are unambiguous.

The **controller** export names every population-dependent count twice, never
bare:

| Prefix         | Population                                        |
| -------------- | ------------------------------------------------- |
| `session_*`    | every span in the session, subagent work included |
| `controller_*` | only the spans in this document's `events[]`      |

`meta.controller_span_count` equals `len(events)`. Reading `session_error_count`
as if it described `events[]` is the mistake this split exists to prevent: on a
session with 42 subagents the errors are almost all in subagent work this
document does not contain.

`roots` is a forest. Each root is a `CHAIN` span named `claude-code-turn` — one
controller turn, holding the user prompt in `attributes["input.value"]`.
Children nest by `parent_id`, which points at a parent's `context.span_id`.

`orphans` holds spans no root reaches, each tagged with an `orphan_reason`:
`parent_not_in_fetch` (the parent sits outside the fetch — typically a turn
still in flight when the export ran, or a parent belonging to another session)
or `parent_cycle` (a `parent_id` loop disconnected from every root; one member
is promoted to an orphan root so the rest are walkable, and this is an
instrumentation bug, not a session fault).

`roots + orphans` is always a partition of the fetched spans. The exporter fails
loudly rather than emit a document that lost any.

`meta.trace_contamination` names the traces this session shares with another:
one entry per trace the session's spans appear in — `trace_id`,
`in_session_spans`, `foreign_span_count`, `foreign_session_ids` — plus the
rollup `contaminated_trace_count` and `foreign_span_count`, and the `method`
that produced it. `null` means the check was skipped, which is not the same as
clean; clean is an entry per trace with `foreign_span_count: 0`. **It is a
report, never a widening** — the export filters strictly on `session.id`
whatever the report says. A non-zero `foreign_span_count` is the reason not to
trust any tool that resolves session → traces → all spans in those traces: that
query returns another session's work as if it were yours.

`foreign_parents` (full export, `--resolve-orphan-parents` only, otherwise
`null`) explains the `parent_not_in_fetch` orphans. Each entry under `resolved`
is the parent span verbatim plus `owning_session_id`, `is_foreign_session`, and
the `orphan_span_ids` that pointed at it; `unresolved_parent_ids` lists the
parents the server no longer holds. These stay in their own bucket and are never
merged into `roots` or `orphans`.

Where the detail lives, by span kind:

| Kind    | Read                                                                                                                                                                                                           |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TOOL`  | `tool.name`, `input.value` (JSON string), `output.value`, `tool.json_schema`                                                                                                                                   |
| `LLM`   | `llm.model_name`, `llm.finish_reason`, `llm.input_messages.N.message.{role,content}`, `llm.output_messages.N.message.{role,content}`, `llm.output_messages.N.message.tool_calls.N.tool_call.function.name`     |
| `AGENT` | `agent.name` (the subagent type), `input.value` (dispatch prompt), `output.value` — a dispatch **acknowledgement**, `{"status": "teammate_spawned"}` or `{"status": "completed"}`, never the subagent's result |
| `CHAIN` | `input.value` (user prompt), `output.value` (turn result)                                                                                                                                                      |

Token counts sit on `LLM` spans: `llm.token_count.prompt`, `.completion`,
`.total`, `.prompt_details.cache_read`, `.prompt_details.cache_write`. Errors
sit on `status_code` (`ERROR` or `UNSET`) with detail in `status_message`.

**Latency is not a field.** Every node carries a computed `duration_ms`;
anywhere else, subtract `start_time` from `end_time`.

The controller export mirrors the controller markdown transcript: `meta` (with
an `attribution` block), then `subagents[]` as the dispatch index, then
`events[]` in chronological order. Each event is a one-line summary — previews
are capped and the true length is recorded in `input_chars` / `output_chars` —
and an event that dispatched a subagent carries `collapsed_subagent_spans`.
`unattributed_span_count` counts subagent spans tied to no dispatch. Each
`subagents[]` entry carries `parent_id`, `root_span_id`, and `trace_id` so a
dispatch can be placed in the call tree without a tree renderer, plus a
`duration_is_dispatch_only` flag.

## Review checklist

Field names below are the **controller** export's; in the full export drop the
`session_` prefix.

1. `meta.session_error_count`, then every span with `status_code == "ERROR"` in
   the **full** export — read `status_message` and the parent chain around it.
   `meta.controller_error_count` is the subset this document contains; the
   difference is subagent errors, visible only in the full export.
2. `orphans` (full export) — check `orphan_reason`. Re-export once the session
   ends, or settle a foreign parent with `--resolve-orphan-parents`.
3. `meta.trace_contamination.contaminated_trace_count` — non-zero warns against
   any trace-scoped reading of the same data, and against correlating this
   session with a trace id. Nothing is wrong with the export itself.
4. `meta.session_token_totals` — compare `cache_read` against `prompt`. A low
   cache-read ratio on a long session means the context is being rebuilt each
   turn. `controller_token_totals` isolates the controller's own spend.
5. `subagents[]` — rank by `collapsed_span_count`: it counts the spans the
   dispatch actually produced, so the largest marks the expensive branch. **Only
   read `duration_ms` where `duration_is_dispatch_only` is `false`.** A
   `teammate_spawned` dispatch's AGENT span closes on the spawn
   acknowledgement, so its `duration_ms` is ~100 ms however long the subagent
   ran, and sorting such a set by it ranks nothing but spawn latency. Then check
   `status` and `status_code` for dispatches that did not complete.
6. `meta.controller_span_count` against the controller transcript's event count
   — like for like, and they should be close. A shortfall on the _controller_
   figure means spans were dropped or the exporter ran mid-session.
   `meta.session_span_count` exceeding it by the subagent work is expected, not
   a finding.
7. `meta.attribution` — `unmatched` splits into two causes needing opposite
   responses. `collisions` counts calls that lost an in-window span to a nearer
   call, and widening `--tolerance-ms` makes those worse; only the remainder,
   which found no candidate at all, may warrant a wider window. `warnings` is
   capped at the first 20 lines plus a suppressed count. A high
   `unattributed_span_count` means subagent work could not be tied to a
   dispatch.
8. The largest `input_chars` / `output_chars` in `events[]` — the spans worth
   opening in the full export for their untruncated values.

## Limits

- Retention is bounded by the server's storage configuration, and an instance
  may hold only a short window. Run `--list-sessions` before concluding a
  session is missing.
- Users identify sessions by short slug (`413914d7`) as often as by full UUID.
  Resolve by substring match against `--list-sessions` or local transcripts;
  Phoenix stores and queries full UUIDs for `session.id`.
- An out-of-process subagent runs its own tracer, its own state file, and its
  own traces -- it does not nest inside the dispatching session's trace. Its
  spans are **deliberately** grouped under the root session's `session.id`,
  resolved once at session init from `$AOPS_SESSION_ID` and stamped on every
  span, so one fetch returns the controller and every subagent together.
- Spans emitted by subagents carry `agent.id` (and `subagent.id`) matching their
  distinct conversation UUID, and `parent.session_id` pointing to the root
  session UUID. Tool spans carry `tool.call_id` when supplied by the harness.
  Controller attribution in `phoenix_trace.py` joins against the local markdown
  controller transcript to isolate controller-only events.
- Do not compare command text between a span and the transcript. Hooks may
  rewrite a command before it runs, so the span holds the rewritten form. Align
  on name and time only.
- `turn_number` is monotonic **per tracer state file**, reset to `0` at
  that file's init. Every subagent has its own counter and they all share one
  `session.id`, so within an exported session the numbers overlap and repeat.
  Sort by `start_time`.
- Root `CHAIN` spans have no parent: the tracer emits `claude-code-turn` as a
  genuine trace root with no `parent_span_id`, subagent turns included. Treat a
  null-parent `CHAIN` as the turn root.
- One trace can span two sessions, because OTel context propagates across
  inter-agent messages. Filter by session id, never by trace id.
- Instrumentation is not uniform. Some runs — container-dispatched ones
  especially — emit `CHAIN` spans only. The export still succeeds, the missing
  kinds show as zero in `meta.span_kind_counts`, and the transcript join
  short-circuits to a single warning naming the instrumentation gap.
