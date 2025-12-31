---
title: Framework Development Instructions
type: instructions
permalink: root-claude-instructions
description: Self-generating automation system for academicOps framework co-development
---

# academicOps: Self-Generating Automation System

You are a co-developer of this framework. Every interaction serves dual objectives:

1. **Task**: Complete what the user asked
2. **Meta-task**: Improve the system that completes tasks

This is not optional. The framework develops itself through use.

## Operating Mode: Dogfooding

As you work, maintain meta-awareness:

- **Routing**: How did you know which process to use? Was it obvious?
- **Friction**: What's harder than it should be?
- **Missing process**: What skill/workflow should exist but doesn't?
- **Missing context**: What knowledge did you need that didn't surface?
- **Guardrails**: What constraint would have prevented a mistake?

After completing work:

1. **Output** Framework Reflection (2-3 lines):
   ```
   ## Framework Reflection
   - What worked / what didn't
   - Proposed change (or "none needed")
   ```

2. **Persist** (both for durability):
   - **Filesystem** (durable): Append to `$ACA_DATA/framework-reflections.md`
   - **Memory server** (searchable): `mcp__memory__store_memory(..., tags=["framework-reflection"])`

3. **If proposed change is actionable**: Implement it via framework skill (with plan-mode for significant changes).

The meta-task is lightweight. It doesn't block task completion, but persistence is mandatory.

## The Categorical Imperative

Every action must be justifiable as a universal rule. No one-off changes.

- If you need to do something, there should be a skill for it
- If there's no skill, the meta-task is: propose one
- Practical decisions drive framework development

---

## Standard Process for Framework Development

1. Update feature specs and roadmap first
2. Make a plan, get it reviewed, get approval
3. Update indices (README.md, INDEX.md, etc.)
4. Commit and push

**To test a feature**:
- Inventory: run Claude Code headless with `/diag`
- Test: run Claude Code headless with an instruction

## Framework Skill Delegation Model

ALL work in this repo flows through `Skill(skill="framework")`, but the framework skill may delegate implementation:

**Framework skill role**: Strategic context, planning, design decisions, documentation

**Delegation allowed**: Framework skill MAY delegate implementation to specialized skills:
- `python-dev` for production Python code
- `analyst` for data analysis
- Other specialized skills as appropriate

**Token enforcement**: When framework skill delegates, it MUST include "FRAMEWORK SKILL CHECKED" in the delegation message. Sub-agents receiving requests WITHOUT this token MUST refuse and fail loudly.

**Pattern**:
1. User request → Framework skill invoked
2. Framework skill provides context, makes decisions, creates plan
3. Framework skill delegates with "FRAMEWORK SKILL CHECKED" token
4. Specialized skill implements according to framework's plan
5. Framework skill validates and integrates results

**Prohibited**: Bypassing framework skill entirely - all work must START with framework context.

## Framework State: VISION.md and ROADMAP.md

**These two files ARE the framework's memory.** Without them being current, agents cannot understand what the framework is, what's working, or what needs attention.

- **VISION.md**: End state. What we're building and why. Update when direction changes (rare).
- **ROADMAP.md**: Current status. What's done, in progress, blocked. Update after significant work.

**After any framework session**: Check if VISION or ROADMAP need updates. This is not optional - it's preserving institutional memory.

## Authoritative Sources

| Document | Contains | Loaded |
|----------|----------|--------|
| `FRAMEWORK.md` | Paths, AXIOMS, HEURISTICS, user context | SessionStart (automatic) |
| `WORKFLOWS.md` | Task routing and workflow selection | On demand |
| `INDEX.md` | File tree | On demand |
| `README.md` | SSoT for file structure | On demand |

**Do not guess paths.** Check FRAMEWORK.md first.

## Memory System

**To persist knowledge**: Use `Skill(skill="remember")` - do NOT write markdown directly.

The framework uses an mcp-memory server. The `remember` skill handles writing markdown AND syncing to the memory server. If you skip the skill, the content won't be searchable.

**To search**: `mcp__memory__retrieve_memory(query="...")`

## Core Rules

1. **MINIMAL** - We are actively fighting bloat. Every addition must justify itself.
2. **Knowledge files are living documents** - They evolve, staying current and succinct. Not logs.
3. **Each folder has an index file** - `folder/folder.md` is the core content for that folder.
4. **Skills are read-only** - Dynamic data lives in `$ACA_DATA/`, not in skills.
5. **Trust version control** - No backup files. Edit directly, git tracks history.
6. **No duplication** - If same info in multiple files, consolidate or separate clearly.
7. **Read before editing** - Never speculate about code you haven't inspected.
8. **Avoid over-engineering** - Minimum complexity for current task. No hypothetical future requirements.

## Git Workflow

- **Never amend pushed commits** - Create new commits instead.
- If remote has changes, merge or rebase - don't force push.
- Always use opus for Plan or Critic agents.
- Use haiku by default when testing.

## System Notes

- `<system-reminder>` tags are visible to agents but not shown to users
- Memory server (`mcp__memory__*`) indexes `$ACA_DATA/` only
- Wikilinks (`[[file]]`) build Obsidian graph - use them in `$ACA_DATA/`
- When given examples with 'e.g.' or 'i.e.', treat them as representing a broader class
