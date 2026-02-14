---
title: Session Insights Pipeline Metrics Schema
type: spec
category: observability
status: active
created: 2026-02-04
related: [[framework-observability]], [[session-insights-prompt]]
---

# Session Insights Pipeline Metrics Schema

## Giving Effect

- [[skills/session-insights/SKILL.md]] - Skill that generates insights conforming to this schema
- [[specs/session-insights-prompt.md]] - Prompt template that references this schema
- [[specs/framework-observability.md]] - Observability architecture consuming these metrics

## Overview

This document defines the metrics schema for monitoring the session insights pipeline. These metrics enable observability of pipeline health, performance, and quality.

## Design Principles

1. **Minimal overhead**: Metrics collection should not significantly impact pipeline performance
2. **Additive accumulation**: Metrics should be easy to aggregate across time periods
3. **Human-readable**: Status should be understandable at a glance
4. **Machine-parseable**: Enable automated alerting and dashboards

## Metrics Categories

### 1. Pipeline Execution Metrics

Track each pipeline run:

| Metric            | Type     | Description                               |
| ----------------- | -------- | ----------------------------------------- |
| `run_timestamp`   | ISO 8601 | When the pipeline ran                     |
| `run_duration_ms` | int      | Execution time in milliseconds            |
| `run_status`      | enum     | "success", "partial", "failure"           |
| `run_error`       | string   | Error message if failure (null otherwise) |
| `run_trigger`     | enum     | "manual", "skill", "hook", "batch"        |

### 2. Processing Metrics

Track what was processed:

| Metric               | Type | Description                                    |
| -------------------- | ---- | ---------------------------------------------- |
| `sessions_scanned`   | int  | Total sessions scanned for pending             |
| `sessions_pending`   | int  | Sessions needing insights generation           |
| `sessions_processed` | int  | Sessions successfully processed                |
| `sessions_failed`    | int  | Sessions that failed processing                |
| `sessions_skipped`   | int  | Sessions skipped (already done, invalid, etc.) |

### 3. Quality Metrics

Track output quality:

| Metric              | Type | Description                        |
| ------------------- | ---- | ---------------------------------- |
| `validation_errors` | int  | Schema validation failures         |
| `malformed_json`    | int  | JSON parse failures from LLM       |
| `empty_responses`   | int  | Responses with no content          |
| `coercions_applied` | int  | Fields that required type coercion |

### 4. Task Sync Metrics

Track task integration:

| Metric                     | Type  | Description                         |
| -------------------------- | ----- | ----------------------------------- |
| `sessions_with_task_match` | int   | Sessions matched to tasks           |
| `sessions_no_task_match`   | int   | Sessions with no task match         |
| `task_match_rate`          | float | Ratio (0.0-1.0) of matched sessions |
| `accomplishments_synced`   | int   | Accomplishments synced to tasks     |

### 5. Operational Health Metrics

Track pipeline health over time:

| Metric                 | Type     | Description                        |
| ---------------------- | -------- | ---------------------------------- |
| `last_successful_run`  | ISO 8601 | Timestamp of last success          |
| `consecutive_failures` | int      | Count of back-to-back failures     |
| `uptime_24h`           | float    | Success rate in last 24h (0.0-1.0) |

## Schema Definition

### Pipeline Metrics File

Location: `~/writing/sessions/summaries/.metrics/pipeline-metrics.json`

```json
{
  "$schema": "session-insights-metrics-schema/v1",
  "last_updated": "2026-02-04T10:30:00+10:00",

  "current_run": {
    "run_timestamp": "2026-02-04T10:30:00+10:00",
    "run_duration_ms": 2340,
    "run_status": "success",
    "run_error": null,
    "run_trigger": "skill",

    "sessions_scanned": 15,
    "sessions_pending": 3,
    "sessions_processed": 3,
    "sessions_failed": 0,
    "sessions_skipped": 0,

    "validation_errors": 0,
    "malformed_json": 0,
    "empty_responses": 0,
    "coercions_applied": 1,

    "sessions_with_task_match": 2,
    "sessions_no_task_match": 1,
    "accomplishments_synced": 5
  },

  "cumulative": {
    "total_runs": 150,
    "total_success": 142,
    "total_failures": 8,
    "total_sessions_processed": 450,
    "total_sessions_failed": 12,
    "total_validation_errors": 3,
    "total_malformed_json": 2,
    "avg_task_match_rate": 0.78,
    "avg_run_duration_ms": 1850
  },

  "health": {
    "last_successful_run": "2026-02-04T10:30:00+10:00",
    "consecutive_failures": 0,
    "uptime_24h": 0.95,
    "status": "healthy"
  }
}
```

### Per-Run Log Entry

Location: `~/writing/sessions/summaries/.metrics/runs.jsonl`

Each line is a complete run record (JSONL format for easy appending):

```json
{
  "run_timestamp": "2026-02-04T10:30:00+10:00",
  "run_duration_ms": 2340,
  "run_status": "success",
  "run_trigger": "skill",
  "sessions_processed": 3,
  "sessions_failed": 0,
  "validation_errors": 0,
  "task_match_rate": 0.67
}
```

## Derived Metrics

These are computed from raw metrics for reporting:

| Metric            | Formula                                                       | Purpose                  |
| ----------------- | ------------------------------------------------------------- | ------------------------ |
| `success_rate`    | sessions_processed / (sessions_processed + sessions_failed)   | Pipeline reliability     |
| `task_match_rate` | sessions_with_task_match / sessions_processed                 | Task integration quality |
| `processing_rate` | sessions_processed / run_duration_ms * 1000                   | Sessions per second      |
| `quality_score`   | 1 - (validation_errors + malformed_json) / sessions_processed | Output quality           |

## Alert Thresholds

See [alert-thresholds task](../tasks/aops-b31047ec) for threshold definitions.

Preliminary thresholds:

| Condition                     | Threshold | Severity |
| ----------------------------- | --------- | -------- |
| `consecutive_failures`        | >= 3      | warning  |
| `consecutive_failures`        | >= 5      | critical |
| `uptime_24h`                  | < 0.8     | warning  |
| `uptime_24h`                  | < 0.5     | critical |
| `task_match_rate`             | < 0.5     | warning  |
| `validation_errors` (per run) | > 0       | info     |
| `malformed_json` (per run)    | > 0       | warning  |
| `hours_since_success`         | > 24      | warning  |
| `hours_since_success`         | > 48      | critical |

## Collection Points

Where metrics are collected:

1. **find_pending.py**: `sessions_scanned`, `sessions_pending`
2. **process_response.py**: `validation_errors`, `malformed_json`, `coercions_applied`
3. **merge_insights.py**: `sessions_processed`, `sessions_failed`
4. **task_sync.py**: `sessions_with_task_match`, `accomplishments_synced`
5. **Skill orchestration**: `run_duration_ms`, `run_status`, `run_trigger`

## Implementation Notes

### Thread Safety

The metrics file uses atomic writes (temp file + rename) to prevent corruption from concurrent access.

### Rotation

The runs.jsonl file should be rotated monthly or at 10MB, whichever comes first. Old files archived as `runs-YYYYMM.jsonl.gz`.

### Initialization

If metrics files don't exist, create with zero values and current timestamp.

## Related Documents

- [[framework-observability]] - Overall observability architecture
- [[session-insights-prompt]] - Insights schema definition
- [[enforcement]] - How metrics enable enforcement
