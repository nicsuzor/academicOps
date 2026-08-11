---
id: external-batch-submission
category: operations
bases: [base-task-tracking, base-verification]
---

# External Batch Submission

Submitting prediction/inference jobs to external APIs (Vertex AI, Anthropic, OpenAI, etc.) where each request costs money and cannot be undone.

## Routing Signals

- "Submit batch job", "run predictions", "run inference"
- Any API call that sends N requests to an external service
- Batch submissions with configurable parameters (model, dataset, prompts)

## NOT This Workflow

- Internal batch processing (parallel task workers) → [[batch-processing]]
- Single API call → no workflow needed
- Read-only API queries (listing jobs, checking status) → no workflow needed

## Unique Steps

### 1. Document the command

Before executing anything, write the EXACT command to the task body or session notes:

```
Command: uv run bm submit --config pipeline_judge.yaml model=gemini-flash
Dataset: 36 records × 3 criteria = 108 requests
Model: gemini-flash
Estimated cost: ~$X
```

This serves as the audit trail. If the command is wrong, it's visible before execution.

### 1.5. Get explicit user approval (MANDATORY — P#50)

Present the concrete submission plan and get explicit approval before proceeding:

```
AskUserQuestion: "Ready to submit batch: [model], [N] requests, [dataset]. Approve?"
```

The user must see and confirm the specific parameters. A general task description ("run the batch") is not sufficient approval for the actual submission. If parameters change (different model, retry after failure), get fresh approval.

### 2. Verify configuration takes effect (MANDATORY)

Run a **single-request test** or dry-run to confirm parameters are applied:

```
# Submit 1 request, not 108
# Then verify the actual parameter values in the API response
```

**Check the ACTUAL state, not the command output.** Config overrides can fail silently (P#8, P#26):

- Read back the submitted job's metadata from the API
- Confirm the model, dataset, and parameters match what you intended
- If the API doesn't expose metadata, check logs for the actual values used

**HALT if verification fails.** Do not proceed to full submission. Report the discrepancy.

### 3. Submit full batch

Only after Step 2 confirms parameters are correct:

- Submit the full batch
- Record the batch/job ID immediately in the task body
- Verify the job ID exists via the API (don't trust the submission response alone)

### 4. Post-submission verification

After submission, confirm:

- [ ] Job ID is real (queryable via API)
- [ ] Request count matches expected (e.g., 108 requests, not 0 or 1)
- [ ] Model/parameters match intended values
- [ ] Job status is RUNNING or QUEUED (not FAILED)

Record all verification results in the task body.

## Key Principles

1. **External API calls are irreversible costs.** Unlike local operations, you cannot undo a batch submission. You can only cancel if caught in time.
2. **Silent failures are the worst kind.** Config overrides, parameter passing, and API wrappers can all fail without raising errors. Always verify the actual state.
3. **1 request is cheap; N requests are not.** The cost of a single verification request is negligible compared to discovering a full batch was misconfigured.
4. **The command IS the documentation.** Writing the command before executing it forces you to think about what you're actually doing.

## Multi-model submissions

When submitting the same dataset to multiple models:

1. Submit model A → verify (Steps 1-4)
2. Submit model B → verify (Steps 1-4)
3. Never submit model B while model A verification is pending

Sequential submission with verification between each model prevents the "3 duplicate batches" failure mode.

## Cancellation protocol

If any verification step fails after submission:

1. Cancel the batch IMMEDIATELY (don't investigate first)
2. Then diagnose the issue
3. Re-submit only after the root cause is fixed and verified

## References

- P#50: Explicit Approval For Costly Operations — user must approve before spend
- P#8: Fail-Fast — no silent failures
- P#26: Verify First — check actual state, never assume
- P#45: Feedback Loops — single-request test is a feedback loop
- Fails: `$ACA_DATA/aops/fails/20260212-batch-model-override-ignored.md`
