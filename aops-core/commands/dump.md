---
name: dump
category: instruction
description: Session handover - commit changes, update task, file follow-ups, output Framework Reflection, halt
allowed-tools: Bash, mcp__memory__store_memory, mcp__plugin_aops-core_task_manager__update_task, mcp__plugin_aops-core_task_manager__create_task, TodoWrite, AskUserQuestion, Read
permalink: commands/dump
---

# /dump - Session Handover & Context Dump

Force graceful handover when work must stop or session must end. This unified command ensures clean session closure and context preservation.

## Usage

```
/dump
```

This command is **mandatory** before session end. The framework stop gate blocks exit until `/dump` is invoked and completed.

## When to Use

- Session ending normally
- Session must end unexpectedly (Emergency)
- Context window approaching limit
- User needs to interrupt for higher-priority work
- Agent is stuck and needs to hand off

## Execution

Execute the [[base-handover]] workflow. The steps are:

1. **Commit and push all work** (MANDATORY per P#24)
2. **Update task with progress** (or create historical task if none claimed)
3. **File follow-up tasks** for outstanding work — use [[decompose]] principles for appropriate granularity
4. **Persist discoveries to memory** (optional)
5. **Output Framework Reflection**
6. **Confirm handover complete** and halt

> **CRITICAL**: Do not proceed past Step 1 until ALL changes are committed and pushed. The only acceptable reason to skip is if you made NO file changes.
