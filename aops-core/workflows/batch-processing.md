---
id: batch-processing
category: operations
bases: [base-task-tracking]
---

# Batch Processing

Multiple similar items processed in parallel.

## Routing Signals

- "Process all X", "batch update"
- Multiple independent tasks
- Items don't share mutable state

## NOT This Workflow

- Items have dependencies → process sequentially
- Shared state → conflicts likely
- Single item → [[design]]

## Unique Steps

1. Validate task independence (no file conflicts)
2. Spawn workers: hypervisor (5+) or direct (2-4)
3. Workers commit locally, supervisor pushes

## Batch Structuring

For large datasets (100+ items), structure into reviewable chunks:

### Splitting Strategies

- **Temporal**: By month/week for time-series data (email, logs, events)
- **Categorical**: By sender/type for grouped data
- **Size-based**: Fixed chunks of 20-50 items

**Each chunk = one worker.** Don't process chunks sequentially in main agent. Spawn parallel subagents:

```
Task(subagent_type="general-purpose", prompt="Process Nov 2025 emails: [criteria]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process Dec 2025 emails: [criteria]", run_in_background=true)
```

### Intermediate State

Store partial results in scratchpad for resilience, review, and audit:

```
$SCRATCHPAD/batch-[task-id]/
  chunk-01-summary.json   # {processed: 50, categories: {task: 3, fyi: 40, skip: 7}}
  chunk-01-details.md     # Per-item classifications with rationale
```

### User Checkpoints

After each chunk:
1. Present summary (counts by category)
2. Show sample items per category
3. **AskUserQuestion** before:
   - Proceeding to next chunk
   - Executing bulk actions (archive, create tasks)

## Key Principle

**Smart subagent, dumb supervisor.** Supervisor writes ONE smart prompt; worker discovers, processes, reports.
