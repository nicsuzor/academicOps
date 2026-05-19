# PR State Index Spec

This document defines the schema and producer requirements for the PR state index used by academicOps to close the loop on task completion.

## Overview

The PR state index is a JSON artefact generated periodically (typically by `repo-sync-cron.sh`) that provides a snapshot of open, recently merged, and recently closed Pull Requests across all tracked repositories.

- **Path**: `$AOPS_SESSIONS/state/pr-state.json`
- **Producer**: `repo-sync-cron.sh` (via `scripts/dump_pr_state.py`)
- **Consumers**: `/daily` task sweep, Dashboard, etc.

## Schema

```json
{
  "generated_at": "ISO-8601 timestamp",
  "generator": "repo-sync-cron",
  "repos": {
    "<repo-slug>": {
      "fetched_at": "ISO-8601 timestamp",
      "open_prs": [
        {
          "number": 123,
          "title": "PR Title",
          "url": "https://github.com/...",
          "state": "OPEN",
          "isDraft": false,
          "author": { "login": "username", "is_bot": false },
          "createdAt": "...",
          "updatedAt": "...",
          "headRefName": "branch-name",
          "baseRefName": "main",
          "body": "PR description (truncated to ~2KB)",
          "mergeable": "MERGEABLE",
          "reviewDecision": "REVIEW_REQUIRED",
          "statusCheckRollup": [
            { "name": "Lint", "conclusion": "SUCCESS", "status": "COMPLETED" }
          ]
        }
      ],
      "recent_merged": [
        {
          "number": 122,
          "title": "...",
          "url": "...",
          "state": "MERGED",
          "author": { "login": "...", "is_bot": false },
          "createdAt": "...",
          "updatedAt": "...",
          "mergedAt": "...",
          "closedAt": "...",
          "headRefName": "...",
          "baseRefName": "main",
          "body": "..."
        }
      ],
      "recent_closed": [/* same shape as recent_merged */],
      "error": "Error message if fetch failed for this repo (optional)"
    }
  }
}
```

## Producer Requirements

1. **Raw Data Only**: The producer must NOT attempt task-id matching, bucketing, or any other heuristic interpretation of the PR data.
2. **Atomicity**: The file must be written to a temporary location (e.g., `pr-state.json.tmp`) and then moved into place to ensure readers never see a partial write.
3. **Resilience**: A failure to fetch PRs for one repository must not prevent the generation of the artefact for others.
4. **Efficiency**: The `body` field must be truncated to approximately 2KB per PR to keep the artefact size manageable. Per-PR projection further drops fields no consumer reads: `author` is reduced to `{login, is_bot}`; each `statusCheckRollup` entry is reduced to `{name, conclusion, status}`; `recent_merged`/`recent_closed` entries omit `statusCheckRollup`, `mergeable`, `reviewDecision`, `isDraft`, and `labels` entirely (only open PRs need bucketing signals).
5. **Freshness**: `recent_merged` should include PRs merged in the last ~14 days (limit 50). `recent_closed` should include PRs closed in the last ~14 days (limit 20).

## Consumers

Consumers are responsible for:

- Matching PR titles/bodies to Task IDs (e.g., via `task-XXXXXXXX` regex).
- Determining if a task can be transitioned to `done` based on its linked PR being merged.
- Computing "needs decision" or "review ready" buckets.
