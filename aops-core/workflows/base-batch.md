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

## Chunking Strategies

| Strategy | Use When |
|----------|----------|
| Temporal | Time-series data (emails by month, logs by day) |
| Categorical | Grouped data (by sender, by type) |
| Size-based | Fixed chunks of 20-50 items |

## Receipt Persistence

**Critical**: Write receipts to task body, not scratchpad.

- Scratchpad = ephemeral (for intermediate state)
- Task body = persistent (for audit trail)
- Workers append receipts during execution, not after

## When to Skip

- Single item (no batching needed)
- Items have dependencies (process sequentially)
- Shared state between items (conflicts likely)
