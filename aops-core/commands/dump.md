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

* Session must end unexpectedly
* Context window approaching limit
* User needs to interrupt for higher-priority work
* Agent is stuck and needs to hand off

## Execution

Execute the [[handover-workflow]]:

1. Identify current task (or create historical task if work was done without one)
2. Update task with progress checkpoint
3. File follow-up tasks for incomplete work
4. Persist discoveries to memory (if any)
5. Commit changes
6. Output Framework Reflection
7. Halt

See `$AOPS/workflows/handover.md` for step-by-step procedure.
