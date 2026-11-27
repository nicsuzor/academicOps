-- Placeholders:
--   <START_UTC>: Start UTC timestamp ISO-8601 (e.g. '2026-11-16T00:00:00Z')
--   <END_UTC>: End UTC timestamp ISO-8601 (e.g. '2026-11-16T02:00:00Z')

-- === QUERY 1: Rollup token usage and spend by task and model (time-bounded) ===
-- Keep windows tight (e.g. 1-2h slices on large SQLite stores) because extracting task.id reads LLM span attributes.
SELECT
  COALESCE(s.attributes->>'$.task.id', s.attributes->>'$.tag.task_id', 'unassigned') AS task_id,
  COALESCE(gm.name, s.attributes->>'$.llm.model_name', 'unknown') AS model,
  COUNT(DISTINCT sc.span_rowid) AS span_count,
  ROUND(SUM(sc.prompt_tokens), 0) AS prompt_tokens,
  ROUND(SUM(sc.completion_tokens), 0) AS completion_tokens,
  ROUND(SUM(sc.total_tokens), 0) AS total_tokens,
  ROUND(SUM(sc.total_cost), 6) AS cost_usd
FROM span_costs sc
JOIN spans s ON s.id = sc.span_rowid
JOIN traces t ON t.id = sc.trace_rowid
LEFT JOIN generative_models gm ON gm.id = sc.model_id
LEFT JOIN project_sessions ps ON ps.id = t.project_session_rowid
WHERE sc.span_start_time >= '<START_UTC>'
  AND sc.span_start_time < '<END_UTC>'
  AND NOT (
    s.name LIKE 'claude/%'
    AND ps.id IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM traces t2
      JOIN spans s2 ON s2.trace_rowid = t2.id
      WHERE t2.project_session_rowid = ps.id
        AND s2.name = 'claude_code.llm_request'
    )
  )
GROUP BY 1, 2
ORDER BY cost_usd DESC
LIMIT 100;

-- === QUERY 2: Rank sessions by built-in token usage and USD spend (zero JSONB reads) ===
SELECT
  ps.session_id,
  p.name AS project,
  ps.start_time,
  ps.end_time,
  COUNT(DISTINCT sc.trace_rowid) AS priced_traces,
  COUNT(sc.id) AS llm_calls,
  ROUND(SUM(sc.prompt_tokens), 0) AS prompt_tokens,
  ROUND(SUM(sc.completion_tokens), 0) AS completion_tokens,
  ROUND(SUM(sc.total_tokens), 0) AS total_tokens,
  ROUND(SUM(sc.total_cost), 4) AS cost_usd
FROM span_costs sc
JOIN traces t ON t.id = sc.trace_rowid
JOIN project_sessions ps ON ps.id = t.project_session_rowid
JOIN projects p ON p.id = ps.project_id
WHERE sc.span_start_time >= '<START_UTC>'
  AND sc.span_start_time < '<END_UTC>'
GROUP BY ps.session_id, p.name, ps.start_time, ps.end_time
ORDER BY cost_usd DESC
LIMIT 50;
