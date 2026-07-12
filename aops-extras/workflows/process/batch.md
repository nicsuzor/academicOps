---
id: batch
kind: process
category: fragment
description: Process multiple independent items in parallel — chunk, spawn workers, aggregate, persist receipts
requires: []
pairs-with: [task-tracking]
conflicts: [burst]
version: 1.0.0
permalink: workflows-process-batch
---

# Process fragment: Batch

**Composable fragment.** Used when processing multiple independent items in
one session. For work spanning multiple sessions, use [[burst]] instead —
these two are mutually exclusive for the same body of work.

## Pattern

1. **Validate independence** — no shared mutable state between items.
2. **Chunk** — temporal, categorical, or size-based (20–50 items/chunk for
   large sets).
3. **Parallelize** — spawn one worker per chunk; don't process sequentially in
   the main agent.
4. **Aggregate** — collect results, summarize counts.
5. **Persist receipts** — write to the task body, not scratchpad, for the
   audit trail; each worker appends as it completes.

## Key Principle

**Smart subagent, dumb supervisor.** One smart prompt per chunk; workers
discover, process, and report. Don't micromanage.

## User Checkpoints

After each chunk: present a summary (counts by category), show sample items,
and confirm before proceeding to the next chunk or executing bulk actions.

## Fire-and-forget

Spawn workers in the background, continue other work, poll for completion —
never block waiting on a single worker's notification.

## When to Skip

- Single item — no batching needed.
- Items have dependencies — process sequentially instead.
- Shared state between items — conflicts likely, use [[burst]] or serial work.
