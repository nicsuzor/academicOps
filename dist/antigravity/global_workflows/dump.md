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
   - For EACH incomplete item, call `create_task()` with details
   - Mentioning follow-up in reflection text is NOT sufficient
   - Tasks must exist in the system before proceeding
4. Persist discoveries to memory (if any)
5. **MANDATORY: Commit changes** - DO NOT proceed to step 6 until all file changes are committed and pushed. If there are uncommitted changes, commit them now.
6. Output Framework Reflection (must confirm commit happened in step 5)
7. Halt

> **CRITICAL**: Steps 5-6 ordering is intentional. The reflection MUST confirm that changes were committed. Never output a reflection with uncommitted work.
