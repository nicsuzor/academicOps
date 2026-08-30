---
name: session-trace
description: Fetch and review a Claude Code session's OTel trace from Arize Phoenix by session id, exporting full and controller-only JSON
---

# Session Trace

## Overview

Export one session's OpenTelemetry spans from an Arize Phoenix span store and read them as
evidence. Phoenix holds the higher-fidelity record: attribute values are stored whole, so a tool
output the markdown transcript truncated is complete here.

Two shapes come out of one fetch:

- **full** — every span verbatim, nested into a `parent_id` forest, plus, under `orphans`, the
  spans no root reaches. Always a partition of the fetch: nothing is dropped.
- **controller** — the controller trunk only, with subagent work collapsed into a dispatch index.
  Its counts are named `session_*` and `controller_*` so the two populations never blur.

## Quick Start

```bash
export PHOENIX_BASE_URL=<phoenix-base-url>
export PHOENIX_PROJECT_NAME=<phoenix-project>

# What the server still holds
python3 scripts/phoenix_trace.py --list-sessions

# Full export (every span, nested)
python3 scripts/phoenix_trace.py <session-id> --mode full --out ./traces

# Controller-only export
python3 scripts/phoenix_trace.py <session-id> --mode controller --out ./traces

# Markdown transcript generation
python3 scripts/phoenix_trace.py <session-id> --mode markdown --out ./transcripts

# Full, controller, and markdown export
python3 scripts/phoenix_trace.py <session-id> --mode all --out ./traces

# A one-off project, without touching the environment
python3 scripts/phoenix_trace.py <session-id> --project <phoenix-project> --out ./traces

# Explain the orphans: fetch the parent spans they point at, tagged with their owner
python3 scripts/phoenix_trace.py <session-id> --mode full --resolve-orphan-parents --out ./traces
```

Both `PHOENIX_BASE_URL` (or `--base-url`) and `PHOENIX_PROJECT_NAME` (or `--project`) are
required. Neither has a default: the exporter exits non-zero naming the flag and the variable,
and — when the server is reachable — the projects it actually holds.

Written as `<session-id>.trace.json` and `<session-id>.trace.controller.json`.

## Options

| Flag                       | Effect                                                                           |
| -------------------------- | -------------------------------------------------------------------------------- |
| `--mode`                   | `full`, `controller`, `markdown`, `all`, or `both` (default `both`)              |
| `--out`                    | output directory; defaults to `$AOPS_SESSIONS/traces/`, else the working dir     |
| `--project`                | Phoenix project name or id; required, falls back to `$PHOENIX_PROJECT_NAME`      |
| `--base-url`               | Phoenix base URL, overriding the environment                                     |
| `--transcript`             | explicit path to the session's `<base>.controller.md`                            |
| `--tolerance-ms`           | transcript join window in milliseconds (default `500`)                           |
| `--page-limit`             | spans requested per API page (default `1000`); lower it to exercise paging       |
| `--from-file`              | read spans from a saved JSON payload instead of the server                       |
| `--no-contamination-check` | skip `meta.trace_contamination`, saving one batched span query                   |
| `--resolve-orphan-parents` | fetch the parents `parent_not_in_fetch` orphans point at, into `foreign_parents` |
| `--list-sessions`          | list retained sessions with start, end, and trace count                          |

## Environment

- `PHOENIX_BASE_URL` — the Phoenix server. `PHOENIX_COLLECTOR_ENDPOINT` is read as a fallback.
  Without one of these, or `--base-url`, the script exits non-zero.
- `PHOENIX_PROJECT_NAME` — the Phoenix project, by name or id. Without it, or `--project`, the
  script exits non-zero and names both, plus the projects the server holds. No project name is
  baked into the artifact.
- `AOPS_SESSIONS` — the transcripts repository. Supplies the default output directory and the
  markdown transcript that controller attribution needs.

## Reading the output

In the **full** export, `meta` carries the counts: `span_count`, `trace_count`, `time_range`,
`span_kind_counts`, `status_counts`, `error_count`, `token_totals`, `fetch_pages`, and the
transcript paths used. That document holds the whole session, so the bare names are unambiguous.

The **controller** export contains only the controller trunk, so every population-dependent count
is named twice and never bare:

| Prefix         | Population                                        |
| -------------- | ------------------------------------------------- |
| `session_*`    | every span in the session, subagent work included |
| `controller_*` | only the spans in this document's `events[]`      |

So `meta.session_span_count` is the whole session; `meta.controller_span_count` equals
`len(events)`. Reading `session_error_count` as if it described `events[]` is the mistake this
split exists to prevent: on a session with 42 subagents, the errors are almost all in subagent
work that this document does not contain.

`roots` is a forest. Each root is a `CHAIN` span named `claude-code-turn` — one controller turn,
holding the user prompt in `attributes["input.value"]`. Children nest by `parent_id`, which points
at a parent's `context.span_id`.

`orphans` holds spans that no root reaches, each tagged with an `orphan_reason`:

- `parent_not_in_fetch` — `parent_id` names a span outside the fetch; typically a turn still in
  flight when the export ran.
- `parent_cycle` — the span sits in a `parent_id` cycle disconnected from every root. One member
  is promoted to an orphan root so the rest are walkable.

`roots + orphans` is always a partition of the fetched spans: walking down from them reaches every
span exactly once. The exporter fails loudly rather than emit a document that lost any.

`meta.trace_contamination` names the traces this session shares with another. One entry per trace
the session's spans appear in — `trace_id`, `in_session_spans`, `foreign_span_count`,
`foreign_session_ids` — plus the rollup `contaminated_trace_count` and `foreign_span_count`, and
the `method` that produced it. `null` means the check was skipped, which is not the same as a clean
result: clean is an entry per trace with `foreign_span_count: 0`. **It is a report, never a
widening** — the export is filtered strictly on `session.id` whatever the report says. A non-zero
`foreign_span_count` is the reason not to trust any tool that resolves session → traces → all spans
in those traces: that query returns another session's work as if it were yours.

`foreign_parents` (full export, `--resolve-orphan-parents` only, otherwise `null`) explains the
`parent_not_in_fetch` orphans. Each entry under `resolved` is the parent span verbatim plus
`owning_session_id`, `is_foreign_session`, and the `orphan_span_ids` that pointed at it;
`unresolved_parent_ids` lists the parents the server no longer holds. These spans stay in their own
bucket and are never merged into `roots` or `orphans`, because they belong to other sessions and
this document holds one.

Where the detail lives, by span kind:

| Kind    | Read                                                                                                                                                                                                           |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TOOL`  | `tool.name`, `input.value` (JSON string), `output.value`, `tool.json_schema`                                                                                                                                   |
| `LLM`   | `llm.model_name`, `llm.finish_reason`, `llm.input_messages.N.message.{role,content}`, `llm.output_messages.N.message.{role,content}`, `llm.output_messages.N.message.tool_calls.N.tool_call.function.name`     |
| `AGENT` | `agent.name` (the subagent type), `input.value` (dispatch prompt), `output.value` — a dispatch **acknowledgement**, `{"status": "teammate_spawned"}` or `{"status": "completed"}`, never the subagent's result |
| `CHAIN` | `input.value` (user prompt), `output.value` (turn result)                                                                                                                                                      |

Token counts sit on `LLM` spans: `llm.token_count.prompt`, `.completion`, `.total`,
`.prompt_details.cache_read`, `.prompt_details.cache_write`.

Errors sit on `status_code` (`ERROR` or `UNSET`) with detail in `status_message`.

**Latency is not a field.** Every node carries a computed `duration_ms`; anywhere else, subtract
`start_time` from `end_time`.

The controller export mirrors the controller markdown transcript: `meta` (with an `attribution`
block), then `subagents[]` as the dispatch index, then `events[]` in chronological order. Each
event is a one-line summary — previews are capped and the true length is recorded in
`input_chars` / `output_chars`. An event that dispatched a subagent carries
`collapsed_subagent_spans`. `unattributed_span_count` counts subagent spans that could not be tied
to any dispatch.

Each `subagents[]` entry carries `parent_id`, `root_span_id`, and `trace_id` so a dispatch can be
placed in the call tree without a tree renderer, and a `duration_is_dispatch_only` flag — see the
checklist item below before reading its `duration_ms`.

## Review checklist

Field names below are the **controller** export's. In the full export drop the `session_` prefix.

1. `meta.session_error_count`, then every span with `status_code == "ERROR"` in the **full**
   export — read `status_message` and the parent chain around it. `meta.controller_error_count` is
   the subset the controller document itself contains; the difference is subagent errors, which
   are only visible in the full export.
2. `orphans` (full export) — check `orphan_reason`. `parent_not_in_fetch` usually means a turn was
   still running at export time, so re-export once the session ends — or the parent belongs to
   another session, which `--resolve-orphan-parents` settles by naming its owner in
   `foreign_parents`. `parent_cycle` means the tracer emitted a `parent_id` loop and is a bug in
   the instrumentation, not in the session.
3. `meta.trace_contamination.contaminated_trace_count` — non-zero means another session's spans
   share a trace with this one. Nothing is wrong with the export; it is a warning about any
   trace-scoped reading of the same data, and about correlating this session with a trace id.
4. `meta.session_token_totals` — compare `cache_read` against `prompt`. A low cache-read ratio on
   a long session means the context is being rebuilt each turn. `controller_token_totals` isolates
   the controller's own spend from its subagents'.
5. `subagents[]` — rank by `collapsed_span_count`, which is the proxy that works: it counts the
   spans the dispatch actually produced, so the largest marks the expensive branch. **Only read
   `duration_ms` where `duration_is_dispatch_only` is `false`.** A `teammate_spawned` dispatch's
   AGENT span closes on the spawn acknowledgement, so its `duration_ms` is on the order of 100 ms
   no matter how long the subagent ran — sorting a `teammate_spawned` set by `duration_ms` ranks
   nothing but spawn latency. Then check `status` and `status_code` for dispatches that did not
   complete.
6. `meta.controller_span_count` against the controller transcript's event count — like for like,
   and they should be close. `meta.session_span_count` is the whole session and will exceed it by
   the subagent work; that excess is expected, not a finding. A shortfall on the _controller_
   figure means spans were dropped or the exporter ran mid-session.
7. `meta.attribution` — `unmatched` splits into two causes that need opposite responses.
   `collisions` counts calls that lost an in-window span to a nearer call; widening
   `--tolerance-ms` makes those worse. The remainder found no candidate at all, and only those may
   warrant a wider window. `warnings` is capped at the first 20 lines plus a suppressed count. A
   high `unattributed_span_count` means subagent work could not be tied to a dispatch.
8. The largest `input_chars` / `output_chars` in `events[]` — the spans worth opening in the full
   export for their untruncated values.

## Limits

- Retention is bounded by the server's storage configuration, and an instance may hold only a short
  window. Run `--list-sessions` before concluding a session is missing.
- **Session Identification & Short Slugs**: Users frequently identify a session by its short slug
  (e.g. `413914d7`) rather than the full UUID. When resolving or searching for a session from user
  input, search using substring match (`slug in session_id`) across `--list-sessions` or local
  transcripts rather than assuming an exact match, because Phoenix stores and queries full UUIDs for
  `session.id`.
- An out-of-process subagent runs its own tracer with its own state file and its own traces — it
  does not nest inside the dispatching session's trace. Its spans are **deliberately** grouped
  under the **root** session's `session.id`, so one fetch returns the controller and every
  subagent together. That is the design, not an accident of inheritance: the tracer resolves the
  grouping id once at session init (`state["phoenix_session_id"] = resolve_session_id(..., prefer_env=True)`,
  sourced from `$AOPS_SESSION_ID`) and stamps it on every span as `"session.id"`.
- Because the grouping is by session and not by trace, and because no span carries an agent
  identity, a span alone cannot say which agent produced it. Controller attribution is therefore a
  timestamp join against the local markdown controller transcript, matching on tool name and
  nearest start time. Without that transcript the export falls back to roots and their direct
  dispatches, and says so in `meta.attribution.method`.
- The tracer records `agent.name` on `AGENT` spans and nothing else identity-bearing — no
  `agent.id`, no `tool.call_id`, and `agent_id` / `agent_type` are never read from the hook
  payload. Attribution stays temporal, so the local transcript remains required. Widen
  `--tolerance-ms` only with care: a wide window creates collisions between same-named calls, and
  the export now names a collision as such rather than reporting it as a tolerance miss.
- Do not compare command text between a span and the transcript. Hooks may rewrite a command before
  it runs, so the span holds the rewritten form. Align on name and time only.
- `arthur.turn_number` is a real, monotonic turn counter — but **per tracer state file**, reset to
  `0` at that file's init. Every subagent has its own state file and its own counter starting at 1,
  and they all share one `session.id`, so within an exported session the numbers overlap and
  repeat. It orders turns within one agent, never across the session. Sort by `start_time`.
- Root `CHAIN` spans have no parent: the tracer emits `claude-code-turn` as a genuine trace root
  with no `parent_span_id`, including for subagent turns. Treat a null-parent `CHAIN` as the turn
  root. (A side-channel that once tried to reparent subagent roots onto the dispatching Agent span
  was removed in `cde7211d2` after never succeeding; spans predating that commit may still show it.)
- One trace can span two sessions, because OTel context propagates across inter-agent messages.
  Filter by session id, never by trace id. `meta.trace_contamination` measures how often that
  happened for this session, and `--resolve-orphan-parents` names the owner of a parent span that
  sits outside it. Both report; neither changes what is exported.
- Instrumentation is not uniform. Some runs — container-dispatched ones especially — emit `CHAIN`
  spans only, with no tool, LLM, or agent spans. The export still succeeds, the missing kinds show
  as zero in `meta.span_kind_counts`, and the transcript join short-circuits to a single warning
  naming the instrumentation gap rather than one per unjoinable transcript line.

## Related

The `audit` workflow (`plugins/aops/workflows/archive/audit.md`) is the complement: forensics over the markdown transcript files.
Use `audit` for the narrative and the subagent call tree, and this skill for the span store, where
values are untruncated and timings are exact.
