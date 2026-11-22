# Token Usage & Context Bloat Diagnostics

Connect span-level token mechanics (fresh input, cache reads, cache writes, cold-cache re-bills) to specific tool payloads, context trajectories, and the instruction or hook rules driving agent behavior.

## 1. Pricing & Coverage Hygiene

- **Coverage boundaries**: Query `MIN(start_time)` and `MAX(start_time)` and state any missing hours or days upfront.
- **Unpriced aliases**: List all distinct `llm.model_name` values with `$0` or missing cost; map each explicitly to its underlying provider family rate and state assumptions.
- **Per-call long-context tiers**: Compute long-context pricing per call from that call's total prompt size (`in + cache_read + cache_write`), never from a flat session average.
- **Provider accounting**: Anthropic spans separate uncached new tokens into `cache_write` and `in`; Gemini/`agy` spans often report `cache_write = 0` and bundle fresh tokens + cold misses into `prompt - cache_read`. Verify surface accounting before computing fresh-input shares.
- **Role ground truth**: Subagent `agent.name` labels can be inherited by child helpers; verify actual `llm.model_name` and loaded instructions on spans.

## 2. Four Causal Spend Buckets

Never conclude "fresh input is the problem" (or "cache reads are the problem") from top-line sums alone. Decompose per-call prompt spend into four mechanisms:

1. **Spawn tax (Turn-1 cache writes)**: Step-1 `cache_write` of each main session or newly spawned subagent -- measures fixed preload overhead (system prompts, loaded instructions, axioms, skills, MCP schemas).
2. **Delta new content**: Incremental tokens added on step $t$ (`Prompt_t - Prompt_{t-1} - Out_{t-1}`), capturing file reads, shell outputs, search results, and handbacks entering context for the first time.
3. **Cold-cache re-bills**: Post-step-1 calls where `cache_read` drops near `0` or a large `cache_write` re-occurs. Attribute to idle gap exceeding cache TTL (>5 min), mid-session model switch, or auto-compaction reset.
4. **Warm-cache drag (lifetime multiplier)**: Repeated `cache_read` across $N$ steps. A 20K-token payload added at step 3 of a 70-step session is paid once on entry and re-read 67 times (plus re-billed cold on any expiry).

## 3. Diagnostic SQL Queries

Use via `phoenix_execute` (`executeSql`), chunked to 1-4 hours for multi-session windows:

### Per-Call Context Trajectory & Cold-Cache Cliffs

```sql
SELECT
  start_time,
  span_id,
  JSON_EXTRACT(attributes, '$.session.id') AS session_id,
  JSON_EXTRACT(attributes, '$.agent.name') AS agent_name,
  JSON_EXTRACT(attributes, '$.llm.model_name') AS model,
  llm_token_count_prompt AS prompt_toks,
  CAST(JSON_EXTRACT(attributes, '$.llm.token_count.prompt_details.cache_read') AS INTEGER) AS cache_read,
  CAST(JSON_EXTRACT(attributes, '$.llm.token_count.prompt_details.cache_write') AS INTEGER) AS cache_write,
  llm_token_count_completion AS out_toks
FROM spans
WHERE span_kind = 'LLM'
  AND start_time >= '<START_UTC>'
  AND start_time < '<END_UTC>'
ORDER BY start_time ASC
```

Classify each call in stream order per `(session_id, agent_id)`: step 0 -> `spawn_tax`; `cache_read == 0` with `prev_total_prompt > 20000` -> `cold_cache_rebill`; `gap_seconds > 300` and `cache_write > 0.5 * prev_total_prompt` -> `ttl_expiry_rebill`; model change with high `cache_write` -> `model_switch_rebill`; otherwise `incremental_step`.

### Tool & Hook Payload Bloat

```sql
SELECT
  name AS tool_name,
  JSON_EXTRACT(attributes, '$.agent.name') AS agent_name,
  COUNT(*) AS calls,
  SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS errors,
  SUM(LENGTH(attributes->>'output.value')) AS total_output_chars,
  MAX(LENGTH(attributes->>'output.value')) AS max_output_chars,
  AVG(LENGTH(attributes->>'output.value')) AS avg_output_chars
FROM spans
WHERE span_kind = 'TOOL'
  AND start_time >= '<START_UTC>'
  AND start_time < '<END_UTC>'
GROUP BY 1, 2
ORDER BY total_output_chars DESC
```

Join high-byte `TOOL` spans to the immediately following `LLM` span's $\Delta \text{Context}_t$ weighted by receiving model tier. Watch for unbounded MCP fetches (`detail="full"` / `include_routes=true`), whole-file or raw-diff reads in flagship coordinator contexts, mis-triggered hooks firing on internal handbacks, and schema-error retry loops inside 150K+ contexts.

## 4. Behavioral Root-Cause Audit

Models follow incentives in their prompts, skills, and harness. Pair every major spend driver with the governing instruction or hook:

- **Pre-paid reading in coordinator context**: Supervisor reads large files or diffs directly instead of delegating bounded extraction to `fast`-tier subagents (or local headless `agy` in Claude Code).
- **Long-lived "God Subagent" reuse**: Resuming one subagent across unrelated topics or >5-minute idle gaps pushes context past 200K+, triggering compaction and cold-cache re-bills.
- **In-turn polling**: Multi-turn `sleep` / status checks inside a large context re-pay full cache reads on every wakeup.
- **Ceremony & `REVISE` ping-pong**: Unnecessary multi-hop delegations or format-nit revision loops on routine work.
- **Late-stage release failures**: Workers failing final PKB writes on schema errors and exiting unreleased, forcing full re-runs.

## 5. Report Structure

Distinguish directly measured span counters from inferred attribution models (e.g., char-to-token estimates), and present:

1. **Executive Cost Breakdown**: Role + tier, calls, fresh input, cold-cache re-bills, warm cache reads, cache writes, output, and total USD.
2. **Top Context Bloaters**: Tool/hook, single-call size, steps carried forward, and lifetime USD drag.
3. **Root-Cause Mapping**: Observed waste paired with exact governing instruction, skill, or hook path.
4. **Ranked Savings**: Concrete instruction edits vs. tool/harness fixes ordered by estimated savings.
