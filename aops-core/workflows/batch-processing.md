---
id: batch-processing
category: operations
bases: [base-task-tracking, base-batch]
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

## Receipt Persistence (CRITICAL)

When user requests receipts/logging of destructive batch operations:

1. **Write to TASK BODY, not scratchpad** - receipts must be persistent, not ephemeral
2. **Concurrent writes** - update task body DURING execution, not after
3. **Each worker appends** - pass task ID to workers, workers call `update_task(body=...)` to append receipts
4. **Failure = partial receipt** - if operation fails mid-batch, task body contains audit trail up to failure point

```
# Worker prompt must include:
"After EACH item processed, append receipt to task [task-id]:
mcp__plugin_aops-core_task_manager__update_task(id='[task-id]', body='- Archived: DATE | FROM | SUBJECT')"
```

**Scratchpad is for intermediate state and summaries. Task body is for user-requested receipts.**

## Key Principle

**Smart subagent, dumb supervisor.** Supervisor writes ONE smart prompt; worker discovers, processes, reports.

## Task Queue Specialization

When batch processing tasks from the queue (swarm pattern):

### Worker Spawning

```
Task(subagent_type="aops-core:worker", run_in_background=true,
     prompt="Pull and complete a task. Use MCP task tools directly...")
```

Spawn up to 8 workers in parallel. Workers MUST use MCP tools directly, NOT Skills (Skills require interactive prompts which are auto-denied in background mode).

### Worker Instructions

Workers use MCP tools directly:

1. `mcp__plugin_aops-core_task_manager__list_tasks(status="active")`
2. `mcp__plugin_aops-core_task_manager__update_task(id="...", status="in_progress", assignee="polecat")`
3. Execute the claimed task
4. `mcp__plugin_aops-core_task_manager__complete_task(id="...")`

### Fire-and-Forget Pattern

> ⚠️ Background agent notifications are unreliable (P#86). Never use `TaskOutput(block=true)` - it can deadlock.

1. Spawn all workers with `run_in_background=true`
2. **Continue other work** - don't wait for notifications
3. Periodically poll task completion via MCP: `list_tasks(status="done")`
4. Workers update task status to `done` when they complete

### Known Limitations

| Issue                    | Workaround                            |
| ------------------------ | ------------------------------------- |
| Skill tool denied        | Use MCP tools directly                |
| Can't kill agents        | Wait for natural completion           |
| Race conditions          | Check status/assignee before claiming |
| Notifications unreliable | Use fire-and-forget + MCP polling     |

### References

- P#86: Background Agent Notifications Are Unreliable
- P#77: CLI-MCP Interface Parity (workers use MCP, not CLI)
