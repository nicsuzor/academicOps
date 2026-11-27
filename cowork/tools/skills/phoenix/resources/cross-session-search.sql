-- Placeholders:
--   <START_UTC>, <END_UTC>: ISO-8601 UTC bounds (e.g. '2026-11-01T00:00:00Z').
--     Include a time of day whenever an offset is attached ('2026-11-15T00:00:00Z' or
--     '2026-11-15 00:00:00+00:00'), or pass a bare date ('2026-11-15', read as UTC);
--     a bare date followed directly by an offset ('2026-11-15+00:00') fails with unsupported_syntax.
--   <CHUNK_START>, <CHUNK_END>: Small UTC chunk bounds (30m-2h for Query 5; 2h-6h for busy days in Query 6).
--   <SEARCH_TERM>: Lowercase LIKE pattern (e.g. '%error%').
--   <TOOL_PATTERN>: Tool name LIKE pattern (e.g. '%update_task%').
--   <PARENT_SESSION_ID>: Full session UUID of the dispatching parent session.
--   <SPAN_ID>: 16-character hex span identifier.

-- === QUERY 1: Time-bounded cross-session error search (no JSON reads; fast across days) ===
SELECT
  ps.session_id,
  p.name AS project,
  s.span_id,
  s.span_kind,
  SUBSTR(s.name, 1, 120) AS name,
  SUBSTR(s.status_message, 1, 200) AS status_msg,
  s.start_time,
  ROUND(s.latency_ms, 1) AS latency_ms
FROM spans s
JOIN traces t ON t.id = s.trace_rowid
JOIN projects p ON p.id = t.project_rowid
LEFT JOIN project_sessions ps ON ps.id = t.project_session_rowid
WHERE s.start_time >= '<START_UTC>'
  AND s.start_time < '<END_UTC>'
  AND s.status_code = 'ERROR'
  AND s.name NOT LIKE 'aops-debug.%'
ORDER BY s.start_time DESC
LIMIT 50;

-- === QUERY 2: Subagent session discovery from parent session ===
SELECT
  s.span_id,
  SUBSTR(s.name, 1, 160) AS name,
  s.span_kind,
  s.status_code,
  s.start_time,
  ROUND(s.latency_ms, 1) AS latency_ms,
  COALESCE(
    s.attributes->>'$.subagent.type',
    s.attributes->>'$.agent.name',
    s.attributes->>'$.subagent_type'
  ) AS subagent_type,
  COALESCE(
    s.attributes->>'$.conversationId',
    s.attributes->>'$.child_session_id',
    s.attributes->>'$.subagent.session_id'
  ) AS child_session_id,
  SUBSTR(COALESCE(s.attributes->>'$.input.value', ''), 1, 300) AS input_excerpt,
  SUBSTR(COALESCE(s.attributes->>'$.output.value', ''), 1, 300) AS output_excerpt
FROM project_sessions ps
JOIN traces t ON t.project_session_rowid = ps.id
JOIN spans s ON s.trace_rowid = t.id
WHERE ps.session_id = '<PARENT_SESSION_ID>'
  AND (
    s.name IN ('invoke_subagent', 'Agent', 'subagent')
    OR s.attributes->>'$.tool.name' IN ('invoke_subagent', 'Agent')
    OR s.attributes->>'$.ToolName' IN ('invoke_subagent', 'Agent')
    OR s.span_kind = 'AGENT'
  )
ORDER BY s.start_time ASC;

-- === QUERY 3: Single-span full payload drill-down ===
SELECT
  s.span_id,
  s.name,
  s.span_kind,
  s.status_code,
  s.status_message,
  s.start_time,
  ROUND(s.latency_ms, 1) AS latency_ms,
  s.attributes->>'$.input.value' AS input_value,
  s.attributes->>'$.output.value' AS output_value,
  s.events
FROM spans s
WHERE s.span_id = '<SPAN_ID>';

-- === QUERY 4: Cross-session user prompt search via MATERIALIZED CTE (fast across 1-2 weeks) ===
-- MATERIALIZED forces SQLite to narrow indexed start_time + root CHAIN spans before evaluating
-- LOWER(inp) LIKE, avoiding full-table JSON scans that time out. Searches all surfaces by default;
-- optionally add `AND inp LIKE '%<channel_marker>%'` in the outer WHERE to narrow to one channel.
WITH root_turns AS MATERIALIZED (
  SELECT
    s.attributes->>'$.session.id' AS sid,
    s.span_id,
    s.start_time,
    SUBSTR(s.attributes->>'$.input.value', 1, 1000) AS inp
  FROM spans s
  WHERE s.start_time >= '<START_UTC>'
    AND s.start_time < '<END_UTC>'
    AND s.span_kind = 'CHAIN'
    AND (s.parent_id IS NULL OR s.parent_id = '')
    AND s.name NOT LIKE 'aops-debug.%'
    AND s.name NOT LIKE 'The following is a <SYSTEM_MESSAGE>%'
)
SELECT
  sid,
  span_id,
  start_time,
  SUBSTR(inp, 1, 400) AS snip
FROM root_turns
WHERE LOWER(inp) LIKE '<SEARCH_TERM>'
ORDER BY start_time ASC
LIMIT 50;

-- === QUERY 5: Windowed cross-session user prompts, hook deduplication, and outbound replies ===
-- Keyword-free sweep across all surfaces in a small time chunk (30m-2h, halving on timeout):
-- non-debug root CHAIN turns, server-side deduplicated UserPromptSubmit hook spans, and
-- outbound reply/send_message TOOL spans. Keep WHERE free of s.attributes predicates.
SELECT
  CASE
    WHEN s.span_kind = 'CHAIN' THEN 'turn'
    WHEN s.name = 'aops-debug.UserPromptSubmit' THEN 'prompt_hook'
    ELSE 'reply'
  END AS kind,
  s.attributes->>'$.session.id' AS sid,
  MIN(s.span_id) AS span_id,
  MIN(s.start_time) AS first_seen,
  COUNT(*) AS cnt,
  SUBSTR(COALESCE(s.attributes->>'$.input.value', ''), 1, 250) AS inp,
  MAX(SUBSTR(COALESCE(s.attributes->>'$.output.value', ''), 1, 250)) AS outp
FROM spans s
WHERE s.start_time >= '<CHUNK_START>'
  AND s.start_time < '<CHUNK_END>'
  AND (
    (s.span_kind = 'CHAIN' AND (s.parent_id IS NULL OR s.parent_id = '')
     AND s.name NOT LIKE 'aops-debug.%'
     AND s.name NOT LIKE 'The following is a <SYSTEM_MESSAGE>%')
    OR s.name = 'aops-debug.UserPromptSubmit'
    OR (s.span_kind = 'TOOL' AND (s.name = 'reply' OR s.name LIKE '%send_message%'))
  )
GROUP BY kind, sid, inp
ORDER BY first_seen ASC
LIMIT 500;

-- === QUERY 6: Cross-session tool-call argument search via MATERIALIZED CTE ===
-- TOOL spans are ~10-50x denser than root CHAIN spans: use 2h-6h chunks on busy days
-- (up to 24h on quiet days) and run chunks sequentially to avoid SQLite lock contention.
WITH tool_calls AS MATERIALIZED (
  SELECT
    s.attributes->>'$.session.id' AS sid,
    s.span_id,
    SUBSTR(s.name, 1, 80) AS name,
    s.status_code,
    s.start_time,
    ROUND(s.latency_ms, 1) AS latency_ms,
    SUBSTR(s.attributes->>'$.input.value', 1, 600) AS inp
  FROM spans s
  WHERE s.start_time >= '<CHUNK_START>'
    AND s.start_time < '<CHUNK_END>'
    AND s.span_kind = 'TOOL'
    AND s.name NOT LIKE 'aops-debug.%'
    AND s.name LIKE '<TOOL_PATTERN>'
)
SELECT
  sid,
  span_id,
  name,
  status_code,
  start_time,
  latency_ms,
  SUBSTR(inp, 1, 300) AS input_excerpt
FROM tool_calls
WHERE LOWER(inp) LIKE '<SEARCH_TERM>'
ORDER BY start_time DESC
LIMIT 50;
