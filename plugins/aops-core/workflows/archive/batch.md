---
id: batch
type: template
kind: fragment
category: fragment
description: Process multiple independent items in parallel — internal fan-out and external costly submission regimes
requires: []
pairs-with: [task-tracking]
conflicts: [burst]
version: 1.1.0
permalink: workflows-process-batch
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---

> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process fragment: Batch

**Composable fragment.** Used when processing multiple independent items in
one session, split into two regimes with very different risk profiles:
(a) **internal fan-out** — parallel subagent workers over a dataset, cheap to redo if wrong; and
(b) **external costly submission** — API calls to paid inference/prediction services, irreversible once sent.
For work spanning multiple sessions, use [[burst]] instead — these two are mutually exclusive for the same body of work.

## Procedure — internal fan-out

1. **Validate independence** — no shared mutable state between items.
2. **Chunk** — temporal, categorical, or size-based (20–50 items/chunk for
   large sets).
3. **Parallelize** — spawn one worker per chunk in the background; don't
   process sequentially in the main agent.
4. **Persist receipts** — write to the task body, not scratchpad, for the
   audit trail; each worker appends as it completes.
5. **User checkpoints** — after each chunk: present a summary (counts by
   category), show sample items, and confirm before proceeding to the next
   chunk or executing bulk actions.
6. **Aggregate and report** — poll for completion via task status rather than
   blocking; never block waiting on a single worker's notification.

### Key Principle

**Smart subagent, dumb supervisor.** One smart prompt per chunk; workers
discover, process, and report. Don't micromanage.

## Procedure — external costly submission

Every request costs money and cannot be undone. This requires strict
verification before commit:

1. **Document the exact command before executing anything** — model, dataset
   size, request count, estimated cost — written to the task body as the audit
   trail.
2. **Get explicit user approval on the concrete plan (mandatory, P#50).** A
   general "run the batch" is not sufficient approval for the actual
   submission; if parameters change, get fresh approval.
3. **Verify configuration takes effect with a single-request test before the
   full batch.** Check the _actual_ state (read back the submitted job's real
   metadata), not the command's claimed success — config overrides fail
   silently.
4. **HALT if verification fails.** Do not proceed to full submission on a failed
   single-request check.
5. **Submit the full batch only after step 3 passes**, and record the job/batch
   ID immediately, verified live via the API — not trusted from the submission
   response alone.
6. **Post-submission verification**: job ID is real and queryable, request count
   matches expected, parameters match intent, status is RUNNING/QUEUED not
   FAILED.
7. **Multi-model submissions are sequential with verification between each** —
   never submit model B while model A's verification is pending.
8. **On any post-submission verification failure: cancel immediately, then
   diagnose** — don't investigate while a misconfigured job burns money.

## Output contract

- Internal fan-out: chunk count, per-chunk summary counts, and the task-body
  receipt trail.
- External submission: documented command, user approval (quoted or linked),
  single-request verification result, job ID with live-queried status, and any
  cancellation record/root cause.

## When to Skip

- Single item — no batching needed.
- Items have dependencies — process sequentially instead.
- Shared state between items — conflicts likely, use [[burst]] or serial work.
