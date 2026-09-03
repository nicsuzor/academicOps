# Phoenix SQL recipes

Read [`../../../../lib/telemetry/phoenix-span-store.md`](../../../../lib/telemetry/phoenix-span-store.md)
first — it holds the identifier-shape table and the `session.id`-vs-`trace_id`
filtering rule every recipe below depends on.

The backend is an allowlisted SQLite database; use JSON extraction (`->>` or
`JSON_EXTRACT`).

**A0 — resolve a `trace_id` to its `session.id`.** Then pivot every subsequent
query onto `session.id`.

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id,
       project_name, COUNT(*) AS span_count,
       MIN(start_time) AS first_seen, MAX(start_time) AS last_seen
FROM spans
WHERE trace_id = '<32_HEX_TRACE_ID>'
GROUP BY session_id, project_name
```

**A — session discovery and error check.**

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id,
       COUNT(*) AS span_count,
       SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS error_count,
       MIN(start_time) AS first_seen, MAX(start_time) AS last_seen
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') LIKE '%<SESSION_SLUG_OR_UUID>%'
GROUP BY session_id
ORDER BY last_seen DESC
LIMIT 10
```

**B — chronological execution.** Add `AND span_kind = 'TOOL'` to audit tool
calls only; swap the `SUBSTRING(...)` for the bare column to read payloads
whole.

```sql
SELECT span_id, parent_id, name, span_kind, status_code, latency_ms,
       SUBSTRING(attributes->>'input.value', 1, 120) AS input_preview,
       SUBSTRING(attributes->>'output.value', 1, 120) AS output_preview
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
ORDER BY start_time ASC
```

**C — errors and tool failures, untruncated.**

```sql
SELECT span_id, name, span_kind, status_message, latency_ms,
       attributes->>'input.value' AS full_input,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND status_code = 'ERROR'
ORDER BY start_time ASC
```

**D — tool-call fingerprint.** Proves what the agent actually invoked, against
what it claims.

```sql
SELECT name, COUNT(*) AS invocations,
       ROUND(AVG(latency_ms), 1) AS avg_ms, MAX(latency_ms) AS max_ms
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND span_kind = 'TOOL'
GROUP BY name
ORDER BY invocations DESC
```

Ground every claim about what a report asserts in these spans, and distinguish
the two zero cases when you write it up. Zero tool calls for an item is
"the agent did not execute actions for these items", not "these items are not
done". One fuzzy `task_search` returning nothing is a search miss, not proof the
target does not exist.

**E — token accounting and cache ratio.**

```sql
SELECT name,
       SUM(llm_token_count_prompt) AS prompt_tokens,
       SUM(llm_token_count_completion) AS completion_tokens,
       SUM(CAST(JSON_EXTRACT(attributes, '$.\"llm.prompt_details.cache_read\"') AS INTEGER)) AS cache_read_tokens
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND span_kind = 'LLM'
GROUP BY name
```

**F — correlate a spawned subagent's own session.** The child carries no
attribute pointing at the parent. Match its root turn to the exact prompt text
the parent's `Agent` call sent (visible in the parent's `AGENT` span, Recipe G)
and to time proximity — the child's first span lands within seconds. A named
subagent's root turn opens `<teammate-message teammate_id="team-lead">...`, so
match on the tail of the parent's prompt. Then pull the child's full span list
with Recipe B.

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id, span_id, start_time,
       SUBSTR(attributes->>'input.value', 1, 300) AS input_preview
FROM spans
WHERE span_kind = 'CHAIN' AND (parent_id IS NULL OR parent_id = '')
  AND start_time >= '<WINDOW_START>+00:00' AND start_time <= '<WINDOW_END>+00:00'
  AND attributes->>'input.value' LIKE '%<DISTINCTIVE PHRASE FROM THE PROMPT>%'
ORDER BY start_time ASC
```

**G — dispatch-mode fingerprint.** Read the `AGENT` spans' `output.value` to
tell a named host teammate from a background task from a container.

```sql
SELECT span_id, status_code, latency_ms, start_time,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<PARENT_SESSION_UUID>'
  AND span_kind = 'AGENT'
ORDER BY start_time ASC
```

- **Named teammate (host)** — output is
  `{"status": "teammate_spawned", "teammate_id": "<name>@session-<slug>", "agent_type": "...", "tmux_session_name": "...", ...}`
  and it emits `<teammate-message>` turns to the parent. A payload
  `{"type":"idle_notification","idleReason":"available"}` is the teammate bus,
  which polecat containers cannot reach — so seeing it proves the worker was a
  named host session, not a container. `available` means only that the agent
  finished its turn with an empty queue; it claims nothing about what got done.
  Its span's duration is spawn latency, not the worker's runtime (see the
  span-store facts read above).
- **Unnamed background task** — output is
  `{"isAsync": true, "status": "async_launched", "agentId": "...", "outputFile": "...", "canReadOutputFile": false}`.
  This mode does have an OTel-visible close: search the parent session for
  `attributes->>'input.value' LIKE '%task-notification%'` to find
  `<task-notification><status>completed</status>...<usage><duration_ms>N</duration_ms></usage></task-notification>`.
- **Polecat container** — writes `$AOPS_SESSIONS/logs/.../run.json`,
  `polecat-session-hooks.jsonl`, and container stdout logs. Never emits teammate
  bus messages.

**H — did the agent structurally have the tool it needed?** Before concluding a
silent agent "failed to report", check whether it ever called the tool
reporting requires, and whether its `agent_type` even grants it.

```sql
SELECT name, span_kind, COUNT(*) AS n
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<CHILD_SESSION_UUID>'
GROUP BY name, span_kind
ORDER BY n DESC
```

Zero `SendMessage`/`send_message` rows in a named-teammate session, alongside
real work in `Bash` and other tool spans and `status_code: UNSET` throughout,
means the agent did its job and had no channel to report it. Cross-check the
agent type's declared `Tools:` allowlist before attributing silence to a bug in
its behaviour rather than its tool grant.

Phoenix's `execute` tool runs an async Python block that can `await
call_tool("executeSql", {"sql": ...})` several times and return one object — use
it to collapse a multi-query pass into a single round-trip.
