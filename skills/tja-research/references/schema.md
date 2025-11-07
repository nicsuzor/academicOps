# TJA Database Schema Reference

## Core Tables

### stg_flows

The authoritative table for all pipeline execution traces. Every stage (source, judge, scorer) creates a row here.

**Key Columns:**

- `call_id` (VARCHAR): Unique identifier for this execution
- `parent_call_id` (VARCHAR): Links to parent stage (judges link to sources, scorers link to judges)
- `agent_role` (VARCHAR): Stage type - 'SOURCE', 'JUDGES', 'SCORERS'
- `agent_model` (VARCHAR): LLM model used (e.g., 'gemini25pro', 'claude45sonnet')
- `timestamp` (TIMESTAMP): When this stage executed
- `outputs` (JSON): Stage-specific output data
- `judge_criteria` (VARCHAR): For JUDGES/SCORERS - which guideline was evaluated

**JSON Output Structure by Role:**

**SOURCE:**

```json
{
  "headline": "Article title",
  "text": "Full article text",
  "url": "https://...",
  "ground_truth": {
    "violates": true,
    "key_points": ["Expected finding 1", "Expected finding 2"]
  }
}
```

**JUDGES:**

```json
{
  "violates": true,
  "reasoning": "The article uses outdated terminology...",
  "confidence": "high",
  "specific_violations": ["Uses 'transgender issues' instead of specific topics"]
}
```

**SCORERS (QualScore format - Nov 2025 onwards):**

```json
{
  "confidence": "high",
  "critical_errors": {
    "misinterpreted_fact": false,
    "hallucinated_fact": false,
    "hallucinated_rule": false,
    "logical_error": false,
    "misapplied_rule": false,
    "abuse_of_discretion": false,
    "reasons": []
  },
  "ground_truth_alignment": [
    {
      "key_point": "Expected violation",
      "key_point_type": "required",
      "key_point_mentioned": true,
      "alignment": "Correct"
    }
  ],
  "summary": "Judge correctly identified..."
}
```

### judge_scores

Denormalized view joining judges with their source articles and scorer evaluations.

**Key Columns:**

- `call_id`: Judge call_id
- `agent_model`: Judge model
- `judge_criteria`: Guideline evaluated
- `prediction_label`: Judge's verdict (violates/doesn't violate)
- `ground_truth_label`: Actual ground truth
- `prediction_correct`: Boolean - did judge get it right?
- `score_quality`: From old scorer format - 'valid', 'missing_score', 'invalid'
- `scorer_correctness`: From old scorer format - 'correct', 'incorrect'
- `article_id`: Source article call_id
- `headline`: Article headline

### scorer_binary_assessments

Aggregated metrics for scorer performance across different criteria.

**Key Columns:**

- `agent_role`: Usually 'SCORERS'
- `agent_model`: Scorer model
- `criteria`: Guideline being scored
- `prediction_correct`: Count of judges that were correct
- `total_predictions`: Total judges evaluated

## Common Query Patterns

### Find All Stages for a Specific Article

```sql
-- Get article headline, all judge predictions, and scorer assessments
WITH article AS (
  SELECT call_id, outputs->>'headline' as headline
  FROM stg_flows
  WHERE agent_role = 'SOURCE'
    AND outputs->>'headline' LIKE '%keyword%'
)
SELECT
  a.headline,
  j.call_id as judge_id,
  j.agent_model as judge_model,
  j.judge_criteria,
  j.outputs->>'violates' as judge_verdict,
  s.agent_model as scorer_model,
  s.outputs->>'confidence' as scorer_confidence,
  s.outputs->'critical_errors'->>'reasons' as errors_found
FROM article a
LEFT JOIN stg_flows j ON j.parent_call_id = a.call_id AND j.agent_role = 'JUDGES'
LEFT JOIN stg_flows s ON s.parent_call_id = j.call_id AND s.agent_role = 'SCORERS'
ORDER BY j.judge_criteria, j.agent_model
```

### Investigate Scorer Error Patterns

```sql
-- Find which error types scorers are flagging most
SELECT
  scorer.outputs->'critical_errors'->'reasons'[0]->>'error_type' as error_type,
  COUNT(*) as occurrences,
  scorer.agent_model
FROM stg_flows scorer
WHERE scorer.agent_role = 'SCORERS'
  AND scorer.timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND JSON_ARRAY_LENGTH(scorer.outputs->'critical_errors'->'reasons') > 0
GROUP BY error_type, scorer.agent_model
ORDER BY occurrences DESC
```

### Compare Judge Performance Across Models

```sql
-- Which models make the most accurate predictions?
SELECT
  agent_model,
  judge_criteria,
  COUNT(*) as total_judgments,
  SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct,
  ROUND(100.0 * SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy_pct
FROM judge_scores
GROUP BY agent_model, judge_criteria
ORDER BY accuracy_pct DESC
```

### Find Judges with Critical Errors

```sql
-- Get judges that scorers flagged for hallucinating facts
SELECT
  judge.call_id as judge_id,
  judge.agent_model,
  source.outputs->>'headline' as article,
  judge.judge_criteria,
  scorer.outputs->'critical_errors'->'reasons' as error_details
FROM stg_flows scorer
JOIN stg_flows judge ON scorer.parent_call_id = judge.call_id
JOIN stg_flows source ON judge.parent_call_id = source.call_id
WHERE scorer.agent_role = 'SCORERS'
  AND scorer.outputs->'critical_errors'->>'hallucinated_fact' = 'true'
ORDER BY scorer.timestamp DESC
```

### Trace Judge Reasoning to Source Material

```sql
-- Verify what the judge saw vs what they claimed
SELECT
  source.outputs->>'headline' as article,
  judge.judge_criteria,
  judge.outputs->>'reasoning' as judge_reasoning,
  scorer.outputs->'critical_errors'->'reasons'[0]->>'source_excerpt' as actual_text,
  scorer.outputs->'critical_errors'->'reasons'[0]->>'explanation' as what_judge_got_wrong
FROM stg_flows scorer
JOIN stg_flows judge ON scorer.parent_call_id = judge.call_id
JOIN stg_flows source ON judge.parent_call_id = source.call_id
WHERE scorer.outputs->'critical_errors'->>'misinterpreted_fact' = 'true'
```

### Find Disagreements Between Judges and Scorers

```sql
-- Cases where scorer says judge was wrong
SELECT
  judge.call_id,
  judge.agent_model,
  judge.outputs->>'violates' as judge_says_violates,
  scorer.outputs->'ground_truth_alignment' as scorer_alignment,
  scorer.outputs->>'summary' as scorer_assessment
FROM stg_flows judge
JOIN stg_flows scorer ON scorer.parent_call_id = judge.call_id
WHERE scorer.agent_role = 'SCORERS'
  AND scorer.outputs->'ground_truth_alignment' @> '[{"alignment":"Incorrect"}]'::jsonb
```

## Data Refresh Workflow

The DuckDB cache is synced from BigQuery via dbt:

```bash
# Update cache with latest data
cd /home/nic/src/automod/tja/tjadbt
./refresh

# This runs:
# 1. dbt run --project-dir . (transforms data in BigQuery)
# 2. sync_to_duckdb.py (copies marts to local DuckDB)
```

**Always refresh before analysis** to ensure you're working with latest data.

## Python Access Examples

```python
import duckdb

# Connect to cache
db = duckdb.connect("/home/nic/src/automod/tja/data/local_cache.duckdb", read_only=True)

# Query scorers with structured output
scorers_df = db.sql("""
    SELECT
        call_id,
        agent_model,
        judge_criteria,
        outputs
    FROM stg_flows
    WHERE agent_role = 'SCORERS'
      AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
""").df()

# Parse JSON outputs
import json

for _, row in scorers_df.iterrows():
    output = json.loads(row["outputs"])
    print(f"Confidence: {output['confidence']}")
    if output["critical_errors"]["reasons"]:
        for error in output["critical_errors"]["reasons"]:
            print(f"  - {error['error_type']}: {error['explanation']}")
```

## Important Notes

1. **Role naming:** Recent data uses 'SCORERS' (plural), older data may use 'SCORER' (singular)
2. **Output formats:** Scorers before Nov 2025 use old format with 'score_quality' field. After Nov 2025, use QualScore structured format.
3. **JSON navigation:** Use `->` for JSON objects, `->>` for JSON strings in DuckDB/PostgreSQL
4. **Timestamps:** All in UTC
5. **NULL parent_call_id:** SOURCE records have no parent since they're the start of the pipeline
