-- Placeholders:
--   <SESSION_ID>: Full session UUID (e.g. '00000000-0000-0000-0000-000000000000')

-- === QUERY 1: Per-model & per-token-type spend breakdown (deduplicating dual emitters) ===
SELECT
  COALESCE(gm.name, s.attributes->>'$.llm.model_name', 'unknown') AS model,
  scd.token_type,
  scd.is_prompt,
  COUNT(DISTINCT s.id) AS span_count,
  ROUND(SUM(scd.tokens), 0) AS tokens,
  ROUND(SUM(scd.cost), 6) AS cost_usd
FROM project_sessions ps
JOIN traces t ON t.project_session_rowid = ps.id
JOIN spans s ON s.trace_rowid = t.id
JOIN span_costs sc ON sc.span_rowid = s.id
JOIN span_cost_details scd ON scd.span_cost_id = sc.id
LEFT JOIN generative_models gm ON gm.id = sc.model_id
WHERE ps.session_id = '<SESSION_ID>'
  AND NOT (
    s.name LIKE 'claude/%'
    AND EXISTS (
      SELECT 1 FROM traces t2
      JOIN spans s2 ON s2.trace_rowid = t2.id
      WHERE t2.project_session_rowid = ps.id
        AND s2.name = 'claude_code.llm_request'
    )
  )
GROUP BY 1, 2, 3
ORDER BY model ASC, is_prompt DESC, token_type ASC;

-- === QUERY 2: Per-tool & upstream MCP service profile ===
SELECT
  COALESCE(s.attributes->>'$.service.name', 'unknown') AS service,
  s.span_kind,
  COALESCE(s.attributes->>'$.ServerName', '') AS mcp_server,
  COALESCE(s.attributes->>'$.ToolName', s.attributes->>'$.tool.name', s.name) AS call_name,
  COUNT(*) AS calls,
  SUM(CASE WHEN s.status_code = 'ERROR' THEN 1 ELSE 0 END) AS errors,
  ROUND(SUM(s.latency_ms), 1) AS total_ms,
  ROUND(AVG(s.latency_ms), 1) AS avg_ms,
  ROUND(MAX(s.latency_ms), 1) AS max_ms,
  SUM(LENGTH(COALESCE(s.attributes->>'$.input.value', ''))) AS input_bytes,
  SUM(LENGTH(COALESCE(s.attributes->>'$.output.value', ''))) AS output_bytes
FROM project_sessions ps
JOIN traces t ON t.project_session_rowid = ps.id
JOIN spans s ON s.trace_rowid = t.id
WHERE ps.session_id = '<SESSION_ID>'
  AND s.span_kind IN ('TOOL', 'AGENT')
  AND s.name NOT LIKE 'aops-debug.%'
GROUP BY 1, 2, 3, 4
ORDER BY total_ms DESC, calls DESC;
