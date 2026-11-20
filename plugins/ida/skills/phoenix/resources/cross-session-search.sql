-- Placeholders:
--   <START_UTC>: Start UTC timestamp ISO-8601 (e.g. '2026-11-01T00:00:00Z')
--   <END_UTC>: End UTC timestamp ISO-8601 (e.g. '2026-11-16T00:00:00Z')
--   <CHUNK_START>, <CHUNK_END>: Small UTC window bounds (e.g. 30m–2h) for Query 5
--   <SEARCH_TERM>: Pattern to match in input/output payloads (e.g. '%error%')
--   <PARENT_SESSION_ID>: Full session UUID of the dispatching parent session
--   <SPAN_ID>: 16-character hex span identifier

-- === QUERY 1: Time-bounded cross-session text/tool/error search ===
SELECT
  ps.session_id,
  p.name AS project,
  s.span_id,
  s.span_kind,
  SUBSTR(s.name, 1, 160) AS name,
  s.status_code,
  s.start_time,
  ROUND(s.latency_ms, 1) AS latency_ms,
  SUBSTR(s.attributes->>'$.input.value', 1, 300) AS input_excerpt,
  SUBSTR(s.attributes->>'$.output.value', 1, 300) AS output_excerpt
FROM spans s
JOIN traces t ON t.id = s.trace_rowid
JOIN projects p ON p.id = t.project_rowid
LEFT JOIN project_sessions ps ON ps.id = t.project_session_rowid
WHERE s.start_time >= '<START_UTC>'
  AND s.start_time < '<END_UTC>'
  AND (
    s.status_code = 'ERROR'
    OR s.attributes->>'$.input.value' LIKE '<SEARCH_TERM>'
    OR s.attributes->>'$.output.value' LIKE '<SEARCH_TERM>'
  )
ORDER BY s.start_time DESC
LIMIT 50;

-- === QUERY 2: Subagent session discovery from parent session or time window ===
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

-- === QUERY 4: Find the user's own prompts on root CHAIN spans across sessions ===
-- The user's own prompts are the input.value of root CHAIN spans (span_kind = 'CHAIN'
-- AND (parent_id IS NULL OR parent_id = '')), and Telegram prompts start with
-- source="plugin:ida-telegram. Omit the source predicate to search across all surfaces.
-- In start_time >= '<START_UTC>', include a time of day whenever an offset is attached
-- (for example '2026-11-15T00:00:00+00:00' or '2026-11-15 00:00:00+00:00'), or pass a
-- bare date with no offset ('2026-11-15', read as UTC); a bare date followed directly
-- by an offset ('2026-11-15+00:00') fails with unsupported_syntax.
SELECT
  JSON_EXTRACT(s.attributes, '$.session.id') AS sid,
  s.span_id,
  s.start_time,
  SUBSTR(s.attributes->>'$.input.value', 1, 400) AS snip
FROM spans s
WHERE s.span_kind = 'CHAIN'
  AND (s.parent_id IS NULL OR s.parent_id = '')
  AND s.start_time >= '<START_UTC>'
  AND s.attributes->>'$.input.value' LIKE '%source="plugin:ida-telegram%'
  AND LOWER(s.attributes->>'$.input.value') LIKE '<SEARCH_TERM>'
ORDER BY s.start_time ASC
LIMIT 50;

-- === QUERY 5: Windowed cross-session user prompts, hook deduplication, and outbound replies ===
-- Unlike QUERY 4 (which filters root CHAIN spans to plugin:ida-telegram with a search term),
-- QUERY 5 sweeps all surfaces in a time chunk: non-debug root CHAIN turns (with paired
-- input/output excerpts), server-side deduplicated aops-debug.UserPromptSubmit hook spans
-- (collapsing repeated PreInvocation fires), and outbound reply/send_message TOOL spans.
-- Keep WHERE free of s.attributes predicates and loop over small start_time chunks
-- (e.g. 30m–2h, halving on timeout) so SQLite uses the start_time index (~0.3s/chunk).
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
