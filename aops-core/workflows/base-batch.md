---
id: base-batch
category: base
---

# Base: Batch Processing

**Composable base pattern.** Used when processing multiple independent items in parallel.

## Pattern

1. **Validate independence**: No shared mutable state between items
2. **Chunk**: Split into reviewable groups (temporal, categorical, or size-based)
3. **Parallelize**: Spawn workers per chunk (not sequential in main agent)
4. **Aggregate**: Collect results, summarize counts
5. **Persist receipts**: Write to task body (not scratchpad) for audit trail

## Key Principle

**Smart subagent, dumb supervisor.** Supervisor writes ONE smart prompt; workers discover, process, and report. Don't micromanage workers.

## Receipt Persistence

1. **Write to TASK BODY, not scratchpad** - receipts must be persistent, not ephemeral
2. **Concurrent writes** - update task body DURING execution, not after
3. **Each worker appends** - pass task ID to workers, workers call `update_task(body=...)` to append receipts
4. **Failure = partial receipt** - if operation fails mid-batch, task body contains audit trail up to failure point

## When to Skip

- Single item (no batching needed)
- Items have dependencies (process sequentially)
- Shared state between items (conflicts likely)

## Batch Structuring

For large datasets (100+ items), structure into reviewable chunks:

- **Temporal**: By month/week for time-series data (email, logs, events)
- **Categorical**: By sender/type for grouped data
- **Size-based**: Fixed chunks of 20-50 items

**Each chunk = one worker.** Don't process chunks sequentially in main agent. Spawn parallel subagents:

```
Task(subagent_type="general-purpose", prompt="Process Nov 2025 emails: [criteria]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process Dec 2025 emails: [criteria]", run_in_background=true)
```

## Intermediate State

Store partial results in scratchpad for resilience, review, and audit:

```
$SCRATCHPAD/batch-[task-id]/
  chunk-01-summary.json   # {processed: 50, categories: {task: 3, fyi: 40, skip: 7}}
  chunk-01-details.md     # Per-item classifications with rationale
```

## User Checkpoints

After each chunk:

1. Present summary (counts by category)
2. Show sample items per category
3. **AskUserQuestion** before:
   - Proceeding to next chunk
   - Executing bulk actions (archive, create tasks)

### Fire-and-Forget Pattern

> ⚠️ Background agent notifications are unreliable (P#86). Never use `TaskOutput(block=true)` - it can deadlock.

1. Spawn all workers with `run_in_background=true`
2. **Continue other work** - don't wait for notifications
3. Periodically poll task completion via MCP: `list_tasks(status="done")`
4. Workers update task status to `done` when they complete
