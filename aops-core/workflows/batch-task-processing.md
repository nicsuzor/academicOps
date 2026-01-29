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
2. mcp__plugin_aops-tools_task_manager__update_task(id="...", status="in_progress", assignee="bot")
3. Execute the claimed task
4. mcp__plugin_aops-tools_task_manager__complete_task(id="...")
```

**Why**: Skills require interactive prompts which are auto-denied in background mode.

### 3. Monitor via Notifications

**DO NOT** poll TaskOutput with full content - it bloats context with JSONL transcripts.

Instead:
- Wait for system notifications: "Agent X (status: completed)"
- Only read output files if you need specific failure details
- Use `block=false, timeout=1000` for quick status checks if absolutely needed

### 4. Replace Completed Workers

When a worker completes, spawn a replacement to maintain pool size.

## Known Limitations

| Issue | Cause | Workaround |
|-------|-------|------------|
| Skill tool denied | Background agents can't prompt | Use MCP tools directly |
| Bash denied (some) | Same permission issue | Workers can use Glob/Grep/Read |
| Can't kill agents | KillShell only for bash tasks | Wait for natural completion |
| Race conditions | Multiple workers claiming same task | Check status/assignee before claiming |

## Efficiency Guidelines

1. **Don't read full outputs** - completion notifications tell you status
2. **Batch spawn workers** - single message with multiple Task calls
3. **Clear instructions** - explicit MCP tool names prevent confusion
4. **Let workers fail fast** - they'll report blockers in their output

## Example Supervisor Loop

```
1. Spawn 8 workers with MCP-direct instructions
2. Continue other work
3. When notified of completion, check if task succeeded
4. Spawn replacement worker
5. Repeat until queue empty
```
