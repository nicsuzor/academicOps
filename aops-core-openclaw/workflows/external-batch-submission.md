---
id: external-batch-submission
type: template
kind: process
category: operations
description: Submit, monitor, and retrieve results from external batch prediction/inference APIs (LiteLLM, Boto3, custom)
requires: [task-tracking, wf-verification]
pairs-with: []
conflicts: []
version: 1.1.0
permalink: workflows-process-external-batch-submission
---

# Process: External Batch Submission

**When to invoke**: "run this batch job", "submit these inputs to LiteLLM",
"process these through Sagemaker".

## Steps

1. **Review inputs** — data is ready, matches the target API's requirements.
2. **Select tool** — LiteLLM, Boto3, or a custom script.
3. **Submit** — execute, capture the Job ID.
4. **Record status** — record the Job ID and current status under `## Pointers`.
5. **Monitor** — poll periodically until complete or failed.
6. **Retrieve results** — download output after completion.
7. **Final verification** — compose [[wf-verification]]: results are complete and
   correctly formatted.

## Critical Rules

- Confidentiality: no sensitive data to unauthorized external APIs.
- Cost: verify the cost estimate before submitting large jobs.
- Auditing: always record the Job ID and source-data hash under `## Pointers` in the task.
- Fail-fast: stop and report immediately on data validation failure.
