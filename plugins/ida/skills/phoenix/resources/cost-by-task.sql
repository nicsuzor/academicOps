-- Placeholders:
--   <START_UTC>: Start UTC timestamp ISO-8601 (e.g. '2026-11-01T00:00:00Z')
--   <END_UTC>: End UTC timestamp ISO-8601 (e.g. '2026-11-16T00:00:00Z')

-- === Rollup token usage and spend by task and model (time-bounded) ===
SELECT
  COALESCE(s.attributes->>'$.task.id', s.attributes->>'$.tag.task_id', 'unassigned') AS task_id,
  COALESCE(gm.name, s.attributes->>'$.llm.model_name', 'unknown') AS model,
  COUNT(DISTINCT s.id) AS span_count,
  ROUND(SUM(sc.prompt_tokens), 0) AS prompt_tokens,
  ROUND(SUM(sc.completion_tokens), 0) AS completion_tokens,
  ROUND(SUM(sc.total_tokens), 0) AS total_tokens,
  ROUND(SUM(sc.total_cost), 6) AS cost_usd
FROM spans s
JOIN traces t ON t.id = s.trace_rowid
JOIN span_costs sc ON sc.span_rowid = s.id
LEFT JOIN generative_models gm ON gm.id = sc.model_id
LEFT JOIN project_sessions ps ON ps.id = t.project_session_rowid
WHERE s.start_time >= '<START_UTC>'
  AND s.start_time < '<END_UTC>'
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
