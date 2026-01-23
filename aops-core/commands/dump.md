---
name: dump
category: instruction
description: Emergency work handover - update task, file follow-ups, persist to memory, output reflection, halt
allowed-tools: Bash, mcp__memory__store_memory, TodoWrite, AskUserQuestion
permalink: commands/dump
---

# /dump - Emergency Work Handover

Force graceful handover when work must stop immediately.

## Usage

```
/dump
```

## When to Use

- Session must end unexpectedly
- Context window approaching limit
- User needs to interrupt for higher-priority work
- Agent is stuck and needs to hand off

## Execution

Execute the [[emergency-handover-workflow]]:

1. Identify current task (or create historical task if work was done without one)
2. Update task with progress checkpoint
3. File follow-up tasks for incomplete work
4. Persist discoveries to memory (if any)
5. Output Framework Reflection
6. Halt

See `aops-core/skills/dump/workflows/emergency-handover.md` for step-by-step procedure.

## Example

```
/dump
```

1. Finds `aops-xyz` active
2. Updates: `update_task(id="aops-xyz", body="DUMP: Completed auth refactor, tests remain")`
3. Creates: `aops-abc` "Add auth tests (follow-up from dump)"
4. Persists: Key pattern discovered about token refresh
5. Outputs Framework Reflection with `Outcome: partial`
6. Halts with resume instructions
