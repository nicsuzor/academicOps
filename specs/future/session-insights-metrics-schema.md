---
title: Session Insights Pipeline Metrics Schema
type: spec
category: observability
status: draft
tier: observability
tags: [spec, observability, metrics, schema]
created: 2026-02-04
---

# Session Insights Pipeline Metrics Schema

**Unbuilt.** Nothing collects or emits these metrics. No `session-insights` skill
or command exists in this repository, and the pipeline this schema measures is
itself a design, not a running system — see
[session-insights-prompt.md](session-insights-prompt.md), which is the extraction
contract, and [sleep-cycle.md](sleep-cycle.md), whose first phase is the
consuming design. Those two specs point here for the metrics definition; this
file exists to be that definition and nothing more.

Because the extraction design is a Claude subagent emitting JSON directly, with
no Python glue, there is no settled set of collection points. Whatever
eventually runs the pipeline owns emitting these fields.

## Metrics

### Pipeline execution — one record per run

| Metric            | Type     | Description                               |
| ----------------- | -------- | ----------------------------------------- |
| `run_timestamp`   | ISO 8601 | When the pipeline ran                     |
| `run_duration_ms` | int      | Execution time in milliseconds            |
| `run_status`      | enum     | "success", "partial", "failure"           |
| `run_error`       | string   | Error message if failure (null otherwise) |
| `run_trigger`     | enum     | "manual", "skill", "hook", "batch"        |

### Processing — what the run handled

| Metric               | Type | Description                                    |
| -------------------- | ---- | ---------------------------------------------- |
| `sessions_scanned`   | int  | Total sessions scanned for pending             |
| `sessions_pending`   | int  | Sessions needing insights generation           |
| `sessions_processed` | int  | Sessions successfully processed                |
| `sessions_failed`    | int  | Sessions that failed processing                |
| `sessions_skipped`   | int  | Sessions skipped (already done, invalid, etc.) |

### Quality — how good the output was

| Metric              | Type | Description                        |
| ------------------- | ---- | ---------------------------------- |
| `validation_errors` | int  | Schema validation failures         |
| `malformed_json`    | int  | JSON parse failures from LLM       |
| `empty_responses`   | int  | Responses with no content          |
| `coercions_applied` | int  | Fields that required type coercion |

### Task sync — how well insights bound to tasks

| Metric                     | Type | Description                     |
| -------------------------- | ---- | ------------------------------- |
| `sessions_with_task_match` | int  | Sessions matched to tasks       |
| `sessions_no_task_match`   | int  | Sessions with no task match     |
| `accomplishments_synced`   | int  | Accomplishments synced to tasks |

### Operational health — trend across runs

| Metric                 | Type     | Description                        |
| ---------------------- | -------- | ---------------------------------- |
| `last_successful_run`  | ISO 8601 | Timestamp of last success          |
| `consecutive_failures` | int      | Count of back-to-back failures     |
| `uptime_24h`           | float    | Success rate in last 24h (0.0-1.0) |

### Derived — computed for reporting, not stored raw

| Metric            | Formula                                                       | Purpose                  |
| ----------------- | ------------------------------------------------------------- | ------------------------ |
| `success_rate`    | sessions_processed / (sessions_processed + sessions_failed)   | Pipeline reliability     |
| `task_match_rate` | sessions_with_task_match / sessions_processed                 | Task integration quality |
| `processing_rate` | sessions_processed / run_duration_ms * 1000                   | Sessions per second      |
| `quality_score`   | 1 - (validation_errors + malformed_json) / sessions_processed | Output quality           |

## File shape

Two files, in a `.metrics/` directory beside the session summaries the pipeline
writes. Neither location is hardcoded here: the summaries root comes from the
environment, and this schema constrains only the file names and their contents.

`pipeline-metrics.json` — current state. `current_run` and `health` carry the
fields defined above; `cumulative` is defined only here:

```json
{
  "$schema": "session-insights-metrics-schema/v1",
  "last_updated": "2026-02-04T10:30:00+10:00",
  "current_run": {
    "run_timestamp": "…",
    "run_status": "success",
    "…": "one value per field above"
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

`runs.jsonl` — append-only history, one complete run record per line, carrying
the execution, processing, and quality fields plus the derived `task_match_rate`.

Write `pipeline-metrics.json` atomically (temp file + rename) so a concurrent
reader never sees a half-written file. Rotate `runs.jsonl` monthly or at 10 MB,
whichever comes first, archiving as `runs-YYYYMM.jsonl.gz`. Where the files do
not yet exist, create them with zero values and the current timestamp.

## Alert thresholds

Preliminary — these are the starting values, not a settled contract.

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
