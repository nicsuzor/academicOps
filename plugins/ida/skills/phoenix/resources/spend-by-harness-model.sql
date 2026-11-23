-- Placeholders:
--   <CHUNK_START>, <CHUNK_END>: ISO-8601 UTC chunk bounds (e.g. '2026-11-22T00:00:00Z').
--
-- Never aggregate LLM spans over a full week in one executeSql call: it hits the ~30-60s timeout.
-- Run either query in a sequential Python loop inside phoenix_execute (halving chunks on timeout)
-- and sum the returned groups in the caller.

-- === QUERY 1: Token sums by surface (aops.surface) and model (2h-6h chunks, deduped) ===
-- Duplicate LLM spans share llm.message.id (spans without one fall back to span_id).
-- Cache keys are nested: llm.token_count.prompt_details.cache_read / .cache_write.
-- `prompt` already includes both cache counts: fresh_input = prompt - cache_read - cache_write.
SELECT h, m, COUNT(*) AS calls, SUM(p) AS prompt, SUM(o) AS output, SUM(cr) AS cache_read, SUM(cw) AS cache_write
FROM (
  SELECT
    attributes->>'$.aops.surface' AS h,
    attributes->>'$.llm.model_name' AS m,
    MAX(CAST(attributes->>'$.llm.token_count.prompt' AS INTEGER)) AS p,
    MAX(CAST(attributes->>'$.llm.token_count.completion' AS INTEGER)) AS o,
    MAX(CAST(attributes->>'$.llm.token_count.prompt_details.cache_read' AS INTEGER)) AS cr,
    MAX(CAST(attributes->>'$.llm.token_count.prompt_details.cache_write' AS INTEGER)) AS cw
  FROM spans
  WHERE span_kind = 'LLM'
    AND start_time >= '<CHUNK_START>'
    AND start_time < '<CHUNK_END>'
  GROUP BY COALESCE(attributes->>'$.llm.message.id', span_id)
)
GROUP BY h, m;

-- === QUERY 2: Built-in USD spend & token rollup by model (1-day chunks, zero JSON reads) ===
-- Uses Phoenix's built-in span_costs and generative_models tables (no hardcoded price tables).
-- Fast (~2s per 24h chunk); check the 'unpriced' row if any spans lack a matched generative_models row.
SELECT
  COALESCE(gm.name, 'unpriced') AS model,
  COUNT(*) AS spans,
  ROUND(SUM(sc.prompt_tokens), 0) AS prompt_tokens,
  ROUND(SUM(sc.completion_tokens), 0) AS completion_tokens,
  ROUND(SUM(sc.total_cost), 4) AS cost_usd
FROM span_costs sc
LEFT JOIN generative_models gm ON gm.id = sc.model_id
WHERE sc.span_start_time >= '<CHUNK_START>'
  AND sc.span_start_time < '<CHUNK_END>'
GROUP BY 1
ORDER BY cost_usd DESC;
