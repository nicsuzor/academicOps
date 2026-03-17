---
id: external-batch-submission
name: external-batch-submission-workflow
category: operations
bases: [base-task-tracking, base-verification]
description: Manage the submission and monitoring of external batch prediction jobs
permalink: workflows/external-batch-submission
tags: [workflow, operations, batch, submission, monitoring, API]
version: 1.1.0
---

# External Batch Submission Workflow

**Purpose**: Provide a structured approach for submitting, monitoring, and retrieving results from external batch prediction APIs.

**When to invoke**: User says "run this batch job", "submit these inputs to LiteLLM", "process these through Sagemaker", or similar.

## Core Workflow Steps

1. **Review Inputs**: Verify the data is ready for submission and matches target API requirements.
2. **Select Tool**: Choose the appropriate submission tool (LiteLLM, Boto3, Custom Script).
3. **Submit Job**: Execute the submission and capture the Job ID.
4. **Record Status**: Log the Job ID and current status in the task system.
5. **Monitor Progress**: Periodically check the job's state until it completes or fails.
6. **Retrieve Results**: Download the output data after job completion.
7. **Final Verification**: Confirm the results are complete and correctly formatted.

## Detailed Procedures and Selection

For specific tool configurations and batch management steps, see **[[batch-submission-details]]**:

- **Tool Selection Criteria** - Choosing between LiteLLM, Boto3, or custom scripts
- **Batch Management** - Data preparation, status polling, and output retrieval
- **Error Handling** - Managing common API failures and data schema mismatches

## Critical Rules

- **Confidentiality**: Ensure no sensitive data is submitted to unauthorized external APIs.
- **Cost Management**: Verify the cost estimate before submitting large batch jobs.
- **Auditing**: Always record the Job ID and source data hash in the task body.
- **Fail-Fast**: Stop and report immediately if data validation fails.
