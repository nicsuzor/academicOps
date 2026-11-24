-- Placeholders:
--   <CHUNK_START>, <CHUNK_END>: ISO-8601 UTC chunk bounds (e.g. '2026-11-22T00:00:00Z').
--
-- Never aggregate LLM spans over a full week in one executeSql call: it hits the ~30-60s timeout.
-- Run either query in a sequential Python loop inside phoenix_execute (keeping each call under ~60s,
-- halving chunks on timeout) and sum the returned groups in the caller. Both queries exclude
-- dual-emitted `claude/%` spans on sessions carrying `claude_code.llm_request` (neutral no-op on
-- single-emitter deployments).

-- === QUERY 1: Token sums by surface (aops.surface) and model (2h-6h chunks, deduped) ===
-- `llm.message.id` deduplicates same-emitter retries (spans without one fall back to span_id);
-- the NOT EXISTS predicate prevents cross-emitter double-counting.
-- Cache keys are nested: llm.token_count.prompt_details.cache_read / .cache_write.
-- `prompt` already includes both cache counts: fresh_input = prompt - cache_read - cache_write.
SELECT h, m, COUNT(*) AS calls, SUM(p) AS prompt, SUM(o) AS output, SUM(cr) AS cache_read, SUM(cw) AS cache_write
FROM (
  SELECT
    MAX(s.attributes->>'$.aops.surface') AS h,
    MAX(s.attributes->>'$.llm.model_name') AS m,
    MAX(CAST(s.attributes->>'$.llm.token_count.prompt' AS INTEGER)) AS p,
    MAX(CAST(s.attributes->>'$.llm.token_count.completion' AS INTEGER)) AS o,
    MAX(CAST(s.attributes->>'$.llm.token_count.prompt_details.cache_read' AS INTEGER)) AS cr,
    MAX(CAST(s.attributes->>'$.llm.token_count.prompt_details.cache_write' AS INTEGER)) AS cw
  FROM spans s
  JOIN traces t ON t.id = s.trace_rowid
  WHERE s.span_kind = 'LLM'
    AND s.start_time >= '<CHUNK_START>'
    AND s.start_time < '<CHUNK_END>'
    AND NOT (
      s.name LIKE 'claude/%'
      AND t.project_session_rowid IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM traces t2
        JOIN spans s2 ON s2.trace_rowid = t2.id
        WHERE t2.project_session_rowid = t.project_session_rowid
          AND s2.name = 'claude_code.llm_request'
      )
    )
  GROUP BY COALESCE(s.attributes->>'$.llm.message.id', s.span_id)
) AS dedup
GROUP BY h, m;

-- === QUERY 2: Built-in USD spend & token rollup by model (1-day chunks, zero JSON reads) ===
-- Uses Phoenix's built-in span_costs and generative_models tables (no hardcoded price tables)
-- with canonical dual-emitter deduplication (~3-4s per 24h chunk).
SELECT
  COALESCE(gm.name, 'unpriced') AS model,
  COUNT(*) AS spans,
  ROUND(SUM(sc.prompt_tokens), 0) AS prompt_tokens,
  ROUND(SUM(sc.completion_tokens), 0) AS completion_tokens,
  ROUND(SUM(sc.total_cost), 4) AS cost_usd
FROM span_costs sc
JOIN spans s ON s.id = sc.span_rowid
JOIN traces t ON t.id = sc.trace_rowid
LEFT JOIN generative_models gm ON gm.id = sc.model_id
WHERE sc.span_start_time >= '<CHUNK_START>'
  AND sc.span_start_time < '<CHUNK_END>'
  AND NOT (
    s.name LIKE 'claude/%'
    AND t.project_session_rowid IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM traces t2
      JOIN spans s2 ON s2.trace_rowid = t2.id
      WHERE t2.project_session_rowid = t.project_session_rowid
        AND s2.name = 'claude_code.llm_request'
    )
  )
GROUP BY 1
ORDER BY cost_usd DESC;
