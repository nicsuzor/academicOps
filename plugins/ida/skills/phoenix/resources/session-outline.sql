-- Placeholders:
--   <SESSION_ID>: Full session UUID (e.g. '00000000-0000-0000-0000-000000000000')
--   <CURSOR_ID>: Integer cursor for keyset paging (initial: 0, next: last seen span_rowid)
--   <SLUG>: 6-8 character session slug prefix (e.g. 'da121570')
--   <TRACE_ID>: 32-character hex trace identifier

-- === QUERY 1: Keyset-pageable chronological step query for session outline ===
-- Page by primary key s.id ASC (LIMIT 25 keeps each page < 20 KB); sort collected rows by start_time when rendering turns.
SELECT
  s.id AS span_rowid,
  s.span_id,
  s.parent_id,
  t.trace_id,
  s.span_kind,
  s.name,
  s.status_code,
  SUBSTR(s.status_message, 1, 240) AS status_msg,
  s.start_time,
  CASE WHEN s.span_kind = 'LLM' AND s.latency_ms <= 1.5 THEN NULL ELSE ROUND(s.latency_ms, 1) END AS latency_ms,
  COALESCE(gm.name, s.attributes->>'$.llm.model_name', s.attributes->>'$.gen_ai.request.model') AS model,
  COALESCE(s.attributes->>'$.agent.name', s.attributes->>'$.subagent.type', s.attributes->>'$.service.name') AS actor,
  COALESCE(s.attributes->>'$.tool.name', s.attributes->>'$.ToolName') AS tool_name,
  SUBSTR(COALESCE(s.attributes->>'$.tool.summary', s.attributes->>'$.toolSummary'), 1, 180) AS tool_summary,
  sc.prompt_tokens,
  sc.completion_tokens,
  ROUND(sc.total_cost, 6) AS total_cost,
  CASE WHEN LENGTH(s.attributes->>'$.llm.reasoning') > 900 THEN SUBSTR(s.attributes->>'$.llm.reasoning', 1, 897) || '...' ELSE s.attributes->>'$.llm.reasoning' END AS reasoning_excerpt,
  CASE WHEN LENGTH(s.attributes->>'$.input.value') > 450 THEN SUBSTR(s.attributes->>'$.input.value', 1, 447) || '...' ELSE s.attributes->>'$.input.value' END AS input_excerpt,
  CASE WHEN LENGTH(s.attributes->>'$.output.value') > 800 THEN SUBSTR(s.attributes->>'$.output.value', 1, 797) || '...' ELSE s.attributes->>'$.output.value' END AS output_excerpt
FROM project_sessions ps
JOIN projects p ON p.id = ps.project_id
JOIN traces t ON t.project_session_rowid = ps.id
JOIN spans s ON s.trace_rowid = t.id
LEFT JOIN span_costs sc ON sc.span_rowid = s.id
LEFT JOIN generative_models gm ON gm.id = sc.model_id
WHERE ps.session_id = '<SESSION_ID>'
  AND s.name NOT LIKE 'aops-debug.%'
  AND s.span_kind IN ('CHAIN', 'AGENT', 'LLM', 'TOOL')
  AND s.id > <CURSOR_ID>
ORDER BY s.id ASC
LIMIT 25;

-- === QUERY 2: Resolve slug or trace_id to session_id ===
SELECT DISTINCT
  ps.session_id,
  p.name AS project_name,
  ps.start_time,
  ps.end_time
FROM project_sessions ps
JOIN projects p ON p.id = ps.project_id
LEFT JOIN traces t ON t.project_session_rowid = ps.id
WHERE ps.session_id LIKE '<SLUG>%'
   OR t.trace_id = '<TRACE_ID>'
ORDER BY ps.start_time DESC
LIMIT 5;
