---
title: External Batch Submission
type: template
category: process
description: Submit, monitor, and retrieve batch prediction or inference jobs from external cloud APIs (e.g. Anthropic Batch API, OpenAI Batch, AWS Batch). Select when executing large-scale asynchronous inference. Not for local subprocess batches (use `batch`).
tags: [batch-api, cloud, external-service, async, operations, process]
---

# Process: External Batch Submission

Asynchronous lifecycle for submitting and retrieving external batch API workloads.

## 1. Payload Formatting and Validation

- Format input requests into standard JSONL/schema required by `<api-provider>`.
- Validate each line for schema conformance, token budgets, and parameter limits.
- Save input payload to persistent file and compute content hash.

## 2. Job Submission and Registration

- Submit batch payload using provider SDK or CLI tools.
- Record returned external job ID, creation timestamp, and expected turnaround window.
- Store job metadata in task tracking notes.

## 3. Asynchronous Status Monitoring

- Poll job status at scheduled intervals (`<poll-interval>`) without blocking interactive session.
- Check status transitions: `submitted` -> `validating` -> `in_progress` -> `completed` / `failed`.

## 4. Result Retrieval and Parsing

- Download raw output payload upon job completion.
- Parse responses, separating successful outputs from API-level item errors.
- Save structured outputs to target dataset or workspace paths.

## 5. Completeness Audit and Verification

- Verify retrieved item count equals submitted request count.
- Emit summary report with cost, latency, and error breakdown.
