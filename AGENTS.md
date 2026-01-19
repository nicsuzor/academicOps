---
title: Framework Development Instructions
type: instruction
category: instruction
permalink: root-claude-instructions
description: Essential agent rules for academicOps framework co-development
---

@CORE.md

# academicOps: Core Agent Rules

You are a co-developer of this framework. Complete the user's task AND improve the system that completes tasks.

## Self-Reflexivity

This framework is itself a hypothesis. When you encounter friction-something that doesn't fit, a question the schema can't answer, a pattern that needs a name-do this:

1. **Log it.**
2. **Propose.** If you see an amendment, suggest it.
3. **Don't force it.** If something doesn't fit, that's data. Don't mangle it to fit the current model.

The system learns, and the framework evolves through use.

## HALT on Underspecified Tasks

Before starting, verify: **What** (exact task), **Where** (files/systems), **Why** (context).

If unclear: HALT, use AskUserQuestion, NEVER assume.

## Fail Fast

- If something doesn't work: FAIL FAST, ESCALATE, HALT
- WORKING TOOLS NOT WORKAROUNDS

## Agent Instructions Are Expensive

Skill, command, and agent instruction files (SKILL.md, commands/*.md, agents/*.md) are loaded into agent context and cost tokens.

**Three rules:**

1. **Actionable content only** - Every line should tell the agent WHAT TO DO
2. **No spec references** - Specifications are for humans, not agent execution
3. **No meta-commentary** - "This skill does X because Y" belongs in specs, not instructions

## Task Tracking

Use the **tasks MCP server** for work tracking:

- `mcp__plugin_aops-core_tasks__get_ready_tasks()` - Find available work
- `mcp__plugin_aops-core_tasks__create_task(title, type, project, parent, depends_on, priority, body)` - Create tasks
- `mcp__plugin_aops-core_tasks__update_task(id, status, ...)` - Update task status
- `mcp__plugin_aops-core_tasks__complete_task(id)` - Mark task done
- `mcp__plugin_aops-core_tasks__list_tasks(project, status, type)` - List/filter tasks
- `mcp__plugin_aops-core_tasks__search_tasks(query)` - Search tasks

**On interruption** (e.g., user triggers /learn mid-task): Update current task `status="blocked"`, create child task for interrupt work with `parent=<current-id>`.

## Session Completion

**Work is NOT complete until `git push` succeeds AND Framework Reflection is output.**

1. File issues for remaining work
2. Run quality gates (tests, linters)
3. Update issue status
4. Format: `./scripts/format.sh && git add -A && git commit -m "..."`
5. **Push**: `git pull --rebase && git push && git status`
6. **Output Framework Reflection** (MANDATORY - see format below)

NEVER stop before pushing. NEVER skip the Framework Reflection.

## Framework Reflection (Session End)

**MANDATORY**: You MUST output a Framework Reflection at the end of EVERY session. This is not optional.

The reflection is extracted by `transcript.py` and stored in `$ACA_SESSIONS/{date}-{session_id}.json`. Without this output, session insights are lost.

Use this EXACT format - field names and syntax must match precisely:

```
## Framework Reflection

**Prompts**: [Verbatim user prompts from session, chronologically. Include ALL prompts, not just the final one.]
**Guidance received**: [Hydrator/custodiet advice, or "N/A"]
**Followed**: [Yes/No/Partial - explain]
**Outcome**: [success/partial/failure]
**Accomplishments**: [What was accomplished - list key items]
**Friction points**: [What was harder than expected, or "none"]
**Root cause** (if not success): [Which component failed]
**Proposed changes**: [Framework improvements identified, or "none"]
**Next step**: [Context for next session - MUST be filed as task if actionable]
**Workflow improvements**: [Changes to make this type of task easier in future, or "none"]
**JIT context needed**: [Info that would have saved time if provided earlier, or "none"]
**Context distractions**: [Irrelevant info that added noise, or "none"]
**User tone**: [Float -1.0 to 1.0: 1.0=effusive, 0.0=neutral, -0.5=disappointed, -1.0=furious]
```

**Next step rule**: If Next step contains actionable work, file it as a task before ending the session. Don't just document it - track it.

**Task creation rule**: If you forgot to create a task for your work this session, create one now and mark it complete. This is how we track work. Set parent/child/dependencies as appropriate.

Field alignment with session-insights JSON schema:
- `**Prompts**`: Maps to `prompts` array - verbatim user prompts in order
- `**Outcome**`: Must be lowercase: `success`, `partial`, or `failure`
- `**Accomplishments**`: Maps to `accomplishments` array
- `**Friction points**`: Maps to `friction_points` array
- `**Proposed changes**`: Maps to `proposed_changes` array
- `**Workflow improvements**`: Maps to `workflow_improvements` array
- `**JIT context needed**`: Maps to `jit_context_needed` array
- `**Context distractions**`: Maps to `context_distractions` array
- `**User tone**`: Maps to `user_mood` float (-1.0 to 1.0, default 0.0)

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Persist key insights** (if learned something) - Use `Skill(skill="remember")` for discoveries worth preserving. Git commits aren't searchable; memory is.
5. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
6. **Clean up** - Clear stashes, prune remote branches
7. **Verify** - All changes committed AND pushed
8. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER ask "should I commit?" or "ready to push when you are" - YOU must commit and push
- If push fails, resolve and retry until it succeeds
