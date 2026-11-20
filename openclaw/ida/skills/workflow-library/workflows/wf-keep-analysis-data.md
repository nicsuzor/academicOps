---
description: Persist intermediate datasets from slow, costly, or hard-to-reproduce analyses so follow-up queries and revised assumptions reuse saved data without re-collection.
id: wf-keep-analysis-data
tags:
  - wf-template
  - analysis
title: Intermediate Analysis Data Workflow
type: template
---

## What this step does

Preserves intermediate collected data from non-trivial analyses in a queryable store so follow-up questions or changed assumptions can reuse it instead of repeating expensive collection.

## Procedure

1. **Assess collection cost**: Skip this step if collection is fast, cheap, and trivial to re-run; proceed when collection is slow, costly, rate-limited, or hard to reproduce.
2. **Persist intermediate data**: Save the intermediate dataset in a queryable location while keeping raw source data immutable.
3. **Record location**: Document the storage path, format, and scope in the task result so downstream analyses can query it directly.

## Output contract

- When collection is non-trivial: intermediate dataset saved in a queryable store with its location and scope recorded in the task result.
- When collection is trivial: no additional artifact.

## When to include

Long-running, rate-limited, or resource-intensive empirical analyses.
