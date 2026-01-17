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

**Run `bd` from your working directory** - never `cd` to academicOps. bd uses CWD to determine project prefix.

Check beads (`bd`): `bd ready`, `bd list`, `bd update <id> --status=in_progress`, `bd close <id>`, `bd sync`

**On interruption** (e.g., user triggers /learn mid-task): Mark current issue `--status=blocked`, create child issue for interrupt work with `--parent=<current-id>`.

## Session Completion

**Work is NOT complete until `git push` succeeds.**

1. File issues for remaining work
2. Run quality gates (tests, linters)
3. Update issue status
4. Format: `./scripts/format.sh && git add -A && git commit -m "..."`
5. **Push**: `git pull --rebase && bd sync && git push && git status`
6. Hand off with Framework Reflection

NEVER stop before pushing.

## Framework Reflection (Session End)

**CRITICAL**: Use this EXACT format - session insights scripts parse this structure. Field names and syntax must match precisely.

```
## Framework Reflection

**Request**: [Original request in brief]
**Guidance received**: [Hydrator/custodiet advice, or "N/A"]
**Followed**: [Yes/No/Partial - explain]
**Outcome**: [success/partial/failure]
**Accomplishments**: [What was accomplished - list key items]
**Friction points**: [What was harder than expected, or "none"]
**Root cause** (if not success): [Which component failed]
**Proposed changes**: [Framework improvements identified, or "none"]
**Next step**: [Context for next session - MUST be filed as bd issue if actionable]
```

**Next step rule**: If Next step contains actionable work, file it as a bd issue before ending the session. Don't just document it - track it.

Field alignment with session-insights JSON schema:
- `**Outcome**`: Must be lowercase: `success`, `partial`, or `failure`
- `**Accomplishments**`: Maps to `accomplishments` array
- `**Friction points**`: Maps to `friction_points` array
- `**Proposed changes**`: Maps to `proposed_changes` array

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
