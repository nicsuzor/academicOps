# Phoenix span-store facts

Canonical facts about the Arize Phoenix OpenTelemetry span store, shared by
every skill that queries or exports it. Read this before writing a query,
sorting spans, or trusting a span's `duration_ms`. Reconciled against
`kb_e6180e88` (deployment, port map, working query recipe) and `kb_b3308a41`
(the session-id groupability ruling) in the PKB.

## Classify the identifier before you query

Searching `session.id` with a `trace_id` returns `{"data":[],"next_cursor":null}`
silently, which reads as "telemetry not retained" and is not.

| Identifier       | Shape                       | Example                                | Query pattern                                                       |
| ---------------- | --------------------------- | -------------------------------------- | ------------------------------------------------------------------- |
| **`trace_id`**   | 32 hex chars, **no dashes** | `c75f0a20a67140e791244eb5dfa64be5`     | `WHERE trace_id = '<32_HEX>'` — resolve to `session.id`, then pivot |
| **`session.id`** | 36 chars, **dashed UUID**   | `22ec8f3e-72c1-4b15-9988-123456789abc` | `WHERE JSON_EXTRACT(attributes, '$.session.id') = '<UUID>'`         |
| **session slug** | 6–8 hex chars               | `22ec8f3e`                             | `WHERE JSON_EXTRACT(attributes, '$.session.id') LIKE '%<slug>%'`    |
| **`span_id`**    | 16 hex chars, **no dashes** | `a1b2c3d4e5f60718`                     | `WHERE span_id = '<16_HEX>'`                                        |

A query returning 0 rows is a reason to re-check the identifier's shape, never
by itself a finding that telemetry was dropped.

## Filter on `session.id`, never `trace_id`

A trace is not session-scoped: OTel context propagates across inter-agent
messages, so one trace can carry spans from more than one session. Verified
case: trace `3f52bfc5eaabe0fed6a557dae5d590b7` carried spans from two
different sessions (`kb_e6180e88`). Grouping by `trace_id` silently mixes
sessions together. Use `trace_id` only to resolve the owning `session.id`,
then pivot every subsequent query onto `session.id`
(`attributes->>'session.id'` / `JSON_EXTRACT(attributes, '$.session.id')`).

The session-id groupability ruling (`kb_b3308a41`) guarantees every span and
turn-trace belonging to a session carries a consistent `session.id`, across
both harnesses (`claude` and `agy`) and across subagent activity. It does
**not** guarantee nested parent/child span structure, and it does not give
per-agent attribution: a subagent shares the dispatching session's
`session.id` by design, with no attribute marking which agent produced a
given span.

## `turn_number` is not a reliable turn counter

`turn_number` (and `arthur.turn_number`) is scoped per tracer-state file and
resets at that file's init, so every subagent has its own counter sharing the
parent's `session.id` — the numbers overlap and repeat within one exported
session. In practice it has been observed to take only the values 1 or 2: a
hook-ordering artifact, not a genuine per-turn counter (`kb_e6180e88`). Never
sort or discriminate on it. Sort by `start_time` for session-wide chronology.

## A `teammate_spawned` span's duration is not the worker's runtime

A named-teammate dispatch's `AGENT` span closes in ~150–250 ms, on the spawn
acknowledgement, and has no OTel-visible close event tied to the teammate's
actual work. Never read its `duration_ms` as how long the spawned worker ran.
