---
name: tja-research
description: Understand TJA research methodology and trace across the record → judge
  → scorer pipeline to investigate prediction quality and workflow issues. Use when
  exploring scorer evaluations, comparing judge predictions to ground truth, or debugging
  the evaluation workflow.
permalink: skills/tja-research/skill
---

# TJA Research Methodology

## Overview

This skill provides context for the Trans Journalists Association (TJA) research project, which evaluates how well AI models apply editorial guidelines to journalism about trans issues. Use this skill when investigating scorer evaluations, judge performance, or workflow issues in the TJA pipeline.

## Research Objective

**Question:** Can AI models accurately identify when news coverage violates ethical reporting standards for trans issues?

**Approach:**
- 28 hand-coded news articles with ground truth labels
- AI judges evaluate articles against TJA style guide
- AI scorers evaluate judge predictions for quality and correctness
- Compare predictions to ground truth to measure accuracy

## Pipeline Architecture

The TJA evaluation pipeline has three main stages:

```
Record (Article) → Judge (Guideline Assessment) → Scorer (Judge Evaluation)
                                                 ↓
                                        Ground Truth Comparison
```

### 1. Record Stage
- **Data:** News articles about trans issues from `bmdev.tja_records`
- **Contains:** article text, metadata, ground truth labels
- **Table:** `stg_flows` WHERE `agent_role = 'SOURCE'`

### 2. Judge Stage
- **Task:** Evaluate if article violates TJA style guide guidelines
- **Output:** Binary prediction (violates/doesn't violate) with reasoning
- **Table:** `judge_scores`, `stg_flows` WHERE `agent_role = 'JUDGES'`
- **Links to:** Source via `parent_call_id`

### 3. Scorer Stage
- **Task:** Evaluate judge's prediction for quality and correctness
- **Output:** Structured QualScore assessment with error detection
- **Table:** `stg_flows` WHERE `agent_role = 'SCORERS'`
- **Links to:** Judge via `parent_call_id`

## Tracing Across Pipeline Stages

All pipeline stages are linked via `call_id` and `parent_call_id` relationships in the `stg_flows` table.

### Find a judge's source record:
```sql
SELECT judge.*, source.*
FROM stg_flows judge
JOIN stg_flows source ON judge.parent_call_id = source.call_id
WHERE judge.agent_role = 'JUDGES'
  AND judge.call_id = '<judge_call_id>'
```

### Find scorers for a specific judge:
```sql
SELECT scorer.*
FROM stg_flows scorer
WHERE scorer.agent_role = 'SCORERS'
  AND scorer.parent_call_id = '<judge_call_id>'
```

### Full pipeline trace for an article:
```sql
SELECT
  source.call_id as article_id,
  source.outputs->>'headline' as headline,
  judge.call_id as judge_id,
  judge.agent_model as judge_model,
  judge.outputs as judge_prediction,
  scorer.call_id as scorer_id,
  scorer.agent_model as scorer_model,
  scorer.outputs as scorer_assessment
FROM stg_flows source
LEFT JOIN stg_flows judge ON judge.parent_call_id = source.call_id
LEFT JOIN stg_flows scorer ON scorer.parent_call_id = judge.call_id
WHERE source.agent_role = 'SOURCE'
  AND judge.agent_role = 'JUDGES'
  AND scorer.agent_role = 'SCORERS'
ORDER BY source.timestamp DESC
```

## QualScore Format (New Structured Scorer Output)

Recent scorers (Nov 2025 onwards) use a structured format in the `outputs` JSON field:

```json
{
  "confidence": "high" | "medium" | "low",
  "critical_errors": {
    "misinterpreted_fact": boolean,
    "hallucinated_fact": boolean,
    "hallucinated_rule": boolean,
    "logical_error": boolean,
    "misapplied_rule": boolean,
    "abuse_of_discretion": boolean,
    "reasons": [
      {
        "error_type": "misinterpreted_fact",
        "explanation": "What the judge got wrong",
        "analyst_reasoning": "Judge's original reasoning",
        "source_excerpt": "Actual text from article",
        "rule_excerpt": "Relevant guideline text"
      }
    ]
  },
  "ground_truth_alignment": [
    {
      "key_point": "Expected finding from ground truth",
      "key_point_type": "required" | "optional",
      "key_point_mentioned": boolean,
      "alignment": "Correct" | "Incorrect" | "Partial"
    }
  ],
  "summary": "Natural language summary of assessment"
}
```

### Error Types:
- **misinterpreted_fact:** Judge misread source material
- **hallucinated_fact:** Judge claimed something not in the article
- **hallucinated_rule:** Judge cited a non-existent guideline
- **logical_error:** Faulty reasoning in judge's analysis
- **misapplied_rule:** Correct rule applied to wrong situation
- **abuse_of_discretion:** Judge's judgment call was unreasonable

## Investigating Issues

### Find scorers flagging specific error types:
```sql
SELECT
  scorer.call_id,
  scorer.agent_model,
  scorer.outputs->'critical_errors'->>'reasons' as error_details
FROM stg_flows scorer
WHERE scorer.agent_role = 'SCORERS'
  AND scorer.outputs->'critical_errors'->>'misinterpreted_fact' = 'true'
ORDER BY scorer.timestamp DESC
```

### Compare judge predictions to ground truth:
```sql
SELECT
  judge.call_id,
  judge.agent_model,
  scorer.outputs->'ground_truth_alignment' as alignment
FROM stg_flows judge
JOIN stg_flows scorer ON scorer.parent_call_id = judge.call_id
WHERE judge.agent_role = 'JUDGES'
  AND scorer.agent_role = 'SCORERS'
```

### Find judges with low scorer confidence:
```sql
SELECT
  judge.call_id,
  judge.agent_model,
  scorer.outputs->>'confidence' as scorer_confidence,
  scorer.outputs->>'summary' as assessment
FROM stg_flows judge
JOIN stg_flows scorer ON scorer.parent_call_id = judge.call_id
WHERE scorer.outputs->>'confidence' = 'low'
```

## Data Access Rules

**For exploration and analysis, use DuckDB cache:**
```python
import duckdb
db = duckdb.connect("/home/nic/src/automod/tja/data/local_cache.duckdb", read_only=True)
df = db.sql("SELECT * FROM stg_flows WHERE agent_role = 'SCORERS'").df()
```

**Refresh cache before analysis:**
```bash
cd /home/nic/src/automod/tja/tjadbt && ./refresh
```

**Never query BigQuery directly** - always use dbt models and the local DuckDB cache.

## Key Tables

- **`stg_flows`**: All pipeline stages (source, judges, scorers) with `agent_role` field
- **`judge_scores`**: Denormalized judge evaluations with ground truth comparison
- **`scorer_binary_assessments`**: Aggregated scorer performance metrics
- **`bmdev.tja_records`**: Original articles with ground truth labels

## References

See `references/schema.md` for complete database schema and additional query examples.