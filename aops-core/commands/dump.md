---
name: dump
category: instruction
description: Session handover - commit changes, update task, file follow-ups, output Framework Reflection, halt
allowed-tools: Bash, mcp__pkb__create_memory, mcp__pkb__update_task, mcp__pkb__create_task, TodoWrite, AskUserQuestion, Read
permalink: commands/dump
---

# /dump - Session Handover & Context Dump

Force graceful handover when work must stop or session must end. This unified command ensures clean session closure and context preservation.

## Usage

```
/dump
```

To invoke programmatically mid-session: `Skill(skill="aops-core:dump")` — note the `skill=` parameter, not `name=`.

> When `/dump` is triggered as a slash command, the skill content is already injected into context — execute the steps directly without calling `Skill` again.

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
3. **File follow-up tasks** for outstanding work — use [[decompose]] principles and ensure all have a **parent** set to the current task or epic
4. **Persist discoveries to memory** (optional)
5. **Output Framework Reflection** (format below)
6. **Confirm handover complete** and halt

> **CRITICAL**: Do not proceed past Step 1 until ALL changes are committed and pushed. The only acceptable reason to skip is if you made NO file changes.

## Framework Reflection Format

Use `## Framework Reflection` as an **H2 heading** with `**Field**: value` lines. Minimum 3 fields:

```markdown
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
```

Do NOT use `**Framework Reflection:**` (bold text) — the parser requires a heading.
