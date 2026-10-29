# Phoenix SQL recipes

Read [`span-store.md`](span-store.md) first -- it holds the identifier-shape table and the `session.id`-vs-`trace_id`
filtering rule every recipe below depends on.

The backend is an allowlisted SQLite database; use JSON extraction (`->>` or
`JSON_EXTRACT`). Dispatch queries through the `services` MCP proxy via
`portal_codemode_execute` (`mcp__services__portal_codemode_execute` in Claude
Code) by calling `codemode.phoenix_execute`.

**A0 -- resolve a `trace_id` to its `session.id`.** Then pivot every subsequent
query onto `session.id`. `trace_id` and the project name live on `traces` and
`projects`, not on `spans`; join through `spans.trace_rowid`.

```sql
SELECT JSON_EXTRACT(s.attributes, '$.session.id') AS session_id,
       p.name AS project, COUNT(*) AS span_count,
       MIN(s.start_time) AS first_seen, MAX(s.start_time) AS last_seen
FROM spans s
JOIN traces t ON t.id = s.trace_rowid
JOIN projects p ON p.id = t.project_rowid
WHERE t.trace_id = '<32_HEX_TRACE_ID>'
GROUP BY session_id, p.name
```

**A -- session discovery and error check.**

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

**B -- chronological execution.** Add `AND span_kind = 'TOOL'` to audit tool
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

**C -- errors and tool failures, untruncated.**

```sql
SELECT span_id, name, span_kind, status_message, latency_ms,
       attributes->>'input.value' AS full_input,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND status_code = 'ERROR'
ORDER BY start_time ASC
```

**D -- tool-call fingerprint.** Proves what the agent actually invoked, against
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

**E -- token accounting and cache ratio.**

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

**F -- correlate a spawned subagent's own session.** When a child worker or subagent
runs under its own `session.id` (standard in `agy` via `invoke_subagent`, and in `claude`
for detached/background sessions), the child carries no attribute pointing at the parent.

- In `agy`, the parent's `invoke_subagent` tool span output returns `{"conversationId": "<uuid>"}`,
  which matches the child's `session.id` directly. Messages from the subagent arrive in the parent
  as `<SYSTEM_MESSAGE sender="<uuid>">[Message] ...`. If known, query the child's spans directly with Recipe B.
- If the child `session.id` is not known from the parent, match its root turn to the prompt text the parent
  sent (visible in the parent's dispatch span: `AGENT` / `Agent` in `claude`, `TOOL` / `invoke_subagent` in `agy`)
  and to time proximity -- the child's first span lands within seconds. In `claude`, a named subagent's root turn
  may open `<teammate-message teammate_id="...">...`, so match on the tail of the parent's prompt. Then pull
  the child's full span list with Recipe B.

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id, span_id, start_time,
       SUBSTR(attributes->>'input.value', 1, 300) AS input_preview
FROM spans
WHERE span_kind = 'CHAIN' AND (parent_id IS NULL OR parent_id = '')
  AND start_time >= '<WINDOW_START>+00:00' AND start_time <= '<WINDOW_END>+00:00'
  AND attributes->>'input.value' LIKE '%<DISTINCTIVE PHRASE FROM THE PROMPT>%'
ORDER BY start_time ASC
```

**G -- dispatch-mode fingerprint.** Read dispatch spans (`AGENT` or `TOOL`) to
tell a named host teammate from a background task, an `agy` subagent, or a container.

```sql
SELECT span_id, name, span_kind, status_code, latency_ms, start_time,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<PARENT_SESSION_UUID>'
  AND (span_kind = 'AGENT' OR name = 'invoke_subagent')
ORDER BY start_time ASC
```

- **Claude Code named teammate (host)** -- output is
  `{"status": "teammate_spawned", "teammate_id": "<name>@session-<slug>", "agent_type": "...", "tmux_session_name": "...", ...}`
  and it emits `<teammate-message>` turns to the parent. A payload
  `{"type":"idle_notification","idleReason":"available","result":"..."}` is the teammate bus,
  which polecat containers cannot reach -- so seeing it proves the worker was a
  named host session, not a container. `available` means only that the agent
  finished its turn with an empty queue. `result` is the teammate's final reply
  for that turn: a report, or only a status such as waiting on a peer.
  Its span's duration is spawn latency, not the worker's runtime (see the
  span-store facts read above).
- **Claude Code unnamed background task** -- output is
  `{"isAsync": true, "status": "async_launched", "agentId": "...", "outputFile": "...", "canReadOutputFile": false}`.
  This mode does have an OTel-visible close: search the parent session for
  `attributes->>'input.value' LIKE '%task-notification%'` to find
  `<task-notification><status>completed</status>...<usage><duration_ms>N</duration_ms></usage></task-notification>`.
- **Antigravity (`agy`) subagent** -- `invoke_subagent` tool span output contains
  `{"conversationId": "<child-session-id>"}`. The subagent executes in its own session; replies
  and completions reach the parent as `<SYSTEM_MESSAGE sender="<child-session-id>">[Message] ...`.
- **Polecat container** -- writes `$AOPS_SESSIONS/logs/.../run.json`,
  `polecat-session-hooks.jsonl`, and container stdout logs. Never emits teammate
  bus messages.

**H -- did the agent structurally have the tool it needed?** Before concluding a
silent agent "failed to report", check whether it ever called the tool
reporting requires, and whether its `agent_type` even grants it.

```sql
SELECT name, span_kind, COUNT(*) AS n
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<CHILD_SESSION_UUID>'
GROUP BY name, span_kind
ORDER BY n DESC
```

Zero `SendMessage`/`send_message` rows in a child session are not silence
if the report was returned via another channel: in Claude Code named teammates,
the final reply reaches the parent as the `result` of an `idle_notification`
(Recipe G); in `agy`, a subagent's final output reaches the parent as a
`<SYSTEM_MESSAGE>` (Recipe G). Read the parent session before concluding nothing
was reported. Cross-check the agent type's declared `Tools:` allowlist before
attributing silence to a bug in its behaviour rather than its tool grant.

Dispatch queries through `codemode.phoenix_execute` using an async Python block:

```javascript
await codemode.phoenix_execute({
  code: `
res = await call_tool("executeSql", {
  "sql": "SELECT ... FROM spans WHERE ..."
})
return res
`
})
```

Inside `phoenix_execute`, the block can `await call_tool("executeSql", {"sql": ...})`
several times and return one combined object -- use it to collapse a multi-query
pass into a single round-trip.

## Cross-session search (find text across many sessions)

Use this route when the question has no session id: "every prompt mentioning X",
"which sessions called tool Y". Do not hand-write SQL turn by turn and let each
result sit in your context: every later call re-reads it.

1. **Filter and project on the server.** Put the text match, the agent or tool
   filter and a bounded `start_time` window in `WHERE`; select ids, timestamps and
   `SUBSTR(...)` snippets, never whole `input.value`/`output.value`. A whole-payload
   pull can hit the 4 MiB response limit and fail.
2. **Write rows to a file, not to your context.** In the same `phoenix_execute`
   block, loop pages with `LIMIT`/`OFFSET` (or `start_time` keyset), append the rows
   to a file in session scratch, and return only the row count and the first few ids.
3. **Read by anchor.** `grep -n` or `sed -n` the file for the rows you need and quote
   those. Do not read the whole file back.
4. **One query per block where you can.** Each extra model turn re-reads your whole
   base context, so fewer turns save about as much as smaller returns.

SQL is capped at 2 KiB per call. Keep one-off aggregations in code mode as above.

## Gotchas

| Symptom | Cause | Fix |
| - | - | - |
| `executeSql` result "exceeds maximum allowed tokens", dumped to a `.txt` file | Query returned too many rows, or unbounded `input.value`/`output.value` columns | Narrow with `SUBSTR(...)` and a tighter `WHERE`/`LIMIT`; if already dumped, read the saved file with `jq` rather than re-querying |
| `{"data":[],"next_cursor":null}` searching for a session by id | Queried `session.id` with a 32-hex `trace_id` | Resolve via `WHERE t.trace_id = '<32_HEX>'` on the joined `traces` table (Recipe A0) first |
| MCP tool calls missing from the agent's response | The agent grepped answers off disk instead of executing tools | `SELECT count(*) FROM spans WHERE span_kind='TOOL' AND attributes->>'session.id'='<UUID>'` |
| Report asserts items "not done" or "failed" with no tool evidence | Agent assumed the outcome after 0 tool calls or a single search miss | Recipe D: distinguish 0 tool calls (never attempted) from tool executions that failed |
| Named subagent never returns / repeats `idle_notification` forever | In Claude Code, `name` on `Agent` call spawns a persistent teammate with no OTel-visible exit event (Recipe G) | Do not wait on the tool call; watch the parent for an inbound `<teammate-message>`, and check the child's own session (Recipe F). In `agy`, inspect subagent session via `conversationId` |
| Subagent did real work but sent no report message | Final reply reaches parent via parent channel (`result` of `idle_notification` in Claude Code, `<SYSTEM_MESSAGE>` in `agy`), not necessarily as `SendMessage`/`send_message` | Recipe G: read teammate `idle_notification` or `<SYSTEM_MESSAGE>` in parent session before checking its tool grant (Recipe H) |
| A container run emits only `CHAIN` spans, with zero `TOOL`/`LLM` spans | Telemetry is not being forwarded from the container | Check the trace endpoint variable in the container's environment |
