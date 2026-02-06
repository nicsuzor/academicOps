# Batch Task Processing Workflow

Orchestrate multiple worker agents to process tasks from the queue in parallel.

## Prerequisites

- Tasks in queue with `status: inbox` or ready state
- `aops-core:worker` agent type available

## Procedure

### 1. Spawn Workers

```
Use Task tool with:
- subagent_type: "aops-core:worker"
- run_in_background: true
- Spawn up to 8 workers in parallel
```

### 2. Worker Instructions (Critical)

Workers MUST use MCP tools directly, NOT Skills:

```
Pull and complete a task. Use MCP task tools directly:
1. mcp__plugin_aops-tools_task_manager__list_tasks(status="active")
2. mcp__plugin_aops-tools_task_manager__update_task(id="...", status="in_progress", assignee="polecat")
3. Execute the claimed task
4. mcp__plugin_aops-tools_task_manager__complete_task(id="...")
```

**Why**: Skills require interactive prompts which are auto-denied in background mode.

### 3. Monitor Completion (Fire-and-Forget Pattern)

> ⚠️ **WARNING**: Background agent notifications are unreliable (P#86). Empirical testing showed ~20% didn't arrive, others delayed 2-5 minutes. Never use `TaskOutput(block=true)` - it can deadlock.

**Recommended pattern - Fire and Forget**:

1. Spawn all workers with `run_in_background=true`
2. **Continue other work** - don't wait for notifications
3. Periodically check task completion via MCP:
   ```
   mcp__plugin_aops-tools_task_manager__list_tasks(status="done", limit=20)
   ```
4. Workers update task status to `done` when they complete

**Why this works**: Workers call `complete_task()` directly, updating task status in the MCP database. You don't need notifications - just poll the task database.

**Avoid these anti-patterns**:
- ❌ `TaskOutput(block=true)` - deadlock risk
- ❌ Waiting for `<agent-notification>` or `<task-notification>` - unreliable
- ❌ Reading `.output` files for status - files are cleaned up after completion

### 4. Replace Completed Workers (Optional)

If maintaining a worker pool:

1. Poll task status via MCP to detect completions
2. Spawn replacement workers for tasks still in queue
3. Continue until queue is empty

## Known Limitations

| Issue | Cause | Workaround |
|-------|-------|------------|
| Skill tool denied | Background agents can't prompt | Use MCP tools directly |
| Bash denied (some) | Same permission issue | Workers can use Glob/Grep/Read |
| Can't kill agents | KillShell only for bash tasks | Wait for natural completion |
| Race conditions | Multiple workers claiming same task | Check status/assignee before claiming |
| **Notifications unreliable** | Empirical observation (P#86) | Use fire-and-forget + MCP polling |

## Efficiency Guidelines

1. **Fire-and-forget** - spawn workers and continue other work
2. **Poll MCP for status** - task database is the source of truth, not notifications
3. **Batch spawn workers** - single message with multiple Task calls
4. **Clear instructions** - explicit MCP tool names prevent confusion
5. **Let workers fail fast** - they'll update task status to blocked/review

## Example Supervisor Loop

```
1. Spawn 8 workers with MCP-direct instructions (run_in_background=true)
2. Continue other work (don't wait for notifications)
3. Periodically: list_tasks(status="done") to check completions
4. Periodically: list_tasks(status="active") to see remaining queue
5. When queue is empty and all workers done, summarize results
```

## References

- P#86: Background Agent Notifications Are Unreliable
- P#77: CLI-MCP Interface Parity (workers use MCP, not CLI)
