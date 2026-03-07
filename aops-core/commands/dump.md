---
name: dump
type: command
category: instruction
description: Comprehensive work handover and session closure - commit changes, push, file a Pull Request, update tasks, file follow-ups, output Framework Reflection, halt
triggers:
  - "emergency handoff"
  - "save work"
  - "interrupted"
  - "session end"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
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

1. **Commit, push, and file a Pull Request** (MANDATORY per P#24)
2. **Update task with progress** (or create historical task if none claimed)
3. **File follow-up tasks** for outstanding work — use [[decompose]] principles and ensure all have a **parent** set to the current task or epic
4. **Persist discoveries to memory** (optional)
   4.5. **Codify learnings** — framework improvement → `gh issue create` in aops repo; project-scoped → update `./.agent/workflows/`; see [[references/handover-details]]
5. **Output Framework Reflection** (include `**Proposed changes**` field referencing what was filed/updated)
6. **Output Summary to user** — LAST step, after everything else (see format below)

> **CRITICAL**: Do not proceed past Step 1 until ALL changes are committed, pushed, and a Pull Request is filed. The only acceptable reason to skip is if you made NO file changes.

## Framework Reflection Format

Use `## Framework Reflection` as an **H2 heading** with `**Field**: value` lines. Minimum 3 fields:

```markdown
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
```

Do NOT use `**Framework Reflection:**` (bold text) — the parser requires a heading.

## Summary to User Format

After the Framework Reflection, output this as the **very last thing** before stopping. Nothing should follow it — it must be readable in the terminal without scrolling.

```
---
## Session Complete

**What was done**: [1–3 sentences]
**Task(s) worked**: [task-id-1], [task-id-2]
**Follow-up items**:
- [Description] → [task-id]  (or "None")

Next: `/pull <task-id>` to resume, or `/pull` to pick from queue.
---
```
