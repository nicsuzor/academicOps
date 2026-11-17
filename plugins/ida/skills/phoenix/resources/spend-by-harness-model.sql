-- Spend by harness and model over a long window (a week). Never aggregate LLM spans over
-- a day or week in one executeSql: it times out (MCP error -32001, ~60 s), and an
-- unwindowed ORDER BY start_time never returns. Sum on the server in small start_time
-- chunks (ids and sums only, never payload columns) and add chunks up in the caller; a
-- 6-hour chunk can still time out under heavy traffic, so halve it and retry.
-- Harness is attributes->>'aops.surface' (claude-code, agy). Duplicate LLM spans share
-- llm.message.id: group on it so they count once (spans without one, such as Gemini,
-- fall back to span_id).
-- Cache keys are nested: llm.token_count.prompt_details.cache_read / .cache_write (the
-- older llm.prompt_details.cache_read does not exist and sums to NULL/0). `prompt`
-- already includes both cache counts: fresh input = prompt - cache_read - cache_write.
-- Ready-made loop: scripts/phoenix_token_cost.py --since <t> --by harness-model
SELECT h, m, COUNT(*) n, SUM(p) p, SUM(o) o, SUM(cr) cr, SUM(cw) cw FROM (
  SELECT attributes->>'aops.surface' h, attributes->>'llm.model_name' m,
         MAX(attributes->>'llm.token_count.prompt') p,
         MAX(attributes->>'llm.token_count.completion') o,
         MAX(attributes->>'llm.token_count.prompt_details.cache_read') cr,
         MAX(attributes->>'llm.token_count.prompt_details.cache_write') cw
  FROM spans WHERE span_kind='LLM'
    AND start_time >= '<CHUNK_START>+00:00' AND start_time < '<CHUNK_END>+00:00'
  GROUP BY COALESCE(attributes->>'llm.message.id', span_id)
) GROUP BY h, m
