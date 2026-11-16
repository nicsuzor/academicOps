-- Placeholders:
--   <START_UTC>: Start UTC timestamp ISO-8601 (e.g. '2026-11-01T00:00:00Z')
--   <END_UTC>: End UTC timestamp ISO-8601 (e.g. '2026-11-16T00:00:00Z')
--   <SEARCH_TERM>: Pattern to match in input/output payloads (e.g. '%error%')
--   <PARENT_SESSION_ID>: Full session UUID of the dispatching parent session
--   <SPAN_ID>: 16-character hex span identifier

-- === QUERY 1: Time-bounded cross-session text/tool/error search ===
SELECT
  ps.session_id,
  p.name AS project,
  s.span_id,
  s.span_kind,
  s.name,
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
  s.name,
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
