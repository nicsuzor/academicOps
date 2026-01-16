---
name: framework
title: Framework Paths and Configuration
type: instruction
category: instruction
description: Session-resolved paths and environment configuration. Injected at session start.
permalink: framework-paths
tags: [framework, paths, configuration]
---

# Framework Paths and Configuration

**Before using Read, Glob, Grep, or Write tools**: Check this path table FIRST.
**If you get "Error reading file"**: You guessed wrong. Return here, use correct path.
**DO NOT fabricate paths** like `~/.config/aops/` - they don't exist.

## Resolved Paths (Use These Directly)

These are the **concrete absolute paths** for this session. Use them directly with Read/Write/Edit tools:

| Path           | Value                 |
| -------------- | --------------------- |
| Framework root | `$AOPS`               |
| User data      | `$ACA_DATA`           |
| Commands       | `$AOPS/commands/`     |
| Skills         | `$AOPS/skills/`       |
| Hooks          | `$AOPS/hooks/`        |
| Agents         | `$AOPS/agents/`       |
| Tests          | `$AOPS/tests/`        |
| Projects       | `$ACA_DATA/projects/` |
| Library        | `$AOPS/lib/`          |
| Sessions       | `$ACA_DATA/sessions/` |

**CRITICAL - Session Log Location**: Session JSONL files are in `$ACA_DATA/sessions/`, NOT `$AOPS/data/sessions/` or `~/.claude/sessions/`. When working with session logs, always invoke `Skill(skill='transcript')` first to convert JSONL to markdown (90% token savings).

**Common files you may need:**

- User accommodations: [[ACCOMMODATIONS.md]] (in $ACA_DATA/)
- User context: [[CORE.md]] (in $ACA_DATA/)
- Project state: [[STATE.md]] (in $ACA_DATA/projects/aops/)
- Vision: [[VISION.md]] (in $AOPS/)

## Path Reference

| Variable     | Purpose                                                  |
| ------------ | -------------------------------------------------------- |
| `$AOPS`      | Framework source (SSoT for all framework files)          |
| `$ACA_DATA`  | User data (sessions, knowledge base)                     |
| `~/.claude/` | Runtime directory (symlinks → `$AOPS`, DO NOT edit here) |

**To edit framework files**: Always edit in `$AOPS/`, never in `~/.claude/` symlinks.

## Memory System

User memories are strictly organised with a clear distinction between:

- **Episodic Memory** (Observations): Time-stamped events, what happened when. "I tried X and it failed." "Meeting decided Y."
- **Semantic Memory** (Current State): Timeless truths, always up-to-date. "X doesn't work because Y." "Our approach is Z."

### Three Storage Systems

| System | Purpose | When to Use |
|--------|---------|-------------|
| **bd issues** | Operational tracking | Tasks, bugs, observations, experiments, decisions-in-progress |
| **$ACA_DATA markdown** | Knowledge SSoT | Synthesized truths, project context, goals, general knowledge |
| **Memory server** | Semantic search index | Derivative of markdown - enables `mcp__memory__retrieve_memory` |

### Decision Tree

```
Is this a task or observation? (time-stamped, "agent did X")
  → YES: bd create or bd update (NOT remember skill)

Is this synthesized knowledge? (timeless truth, "X is Y")
  → YES: Skill(skill="remember") → writes markdown + memory server

Need to search existing knowledge?
  → USE: mcp__memory__retrieve_memory(query="...")
```

### Key Rules

1. **Markdown is SSoT** - Memory server is derived, not authoritative
2. **Remember skill dual-writes** - Always use it for new knowledge (ensures sync)
3. **bd for observations** - Don't create markdown files for time-stamped events
4. **Synthesis flow**: bd observations → patterns emerge → remember skill → semantic docs → close bd issue

### Insight Capture

When you discover something worth preserving:
- **Operational insight** (bug found, approach tried): `bd create` or comment on existing issue
- **Knowledge insight** (pattern, principle, fact): `Skill(skill="remember")`
- **Both**: Create bd issue for tracking, use remember skill for the knowledge

**To persist knowledge**: Use `Skill(skill="remember")` (blocking) or spawn background Task with `run_in_background=true` (seamless).

**To search**: Use `mcp__memory__retrieve_memory(query="...")`.

**To repair sync**: Run remember skill's sync workflow (reconciles markdown → memory server).

### Search Strategy: Indices Over Exploration

**Prefer curated indices over raw filesystem searches.**

| Query Type | Use | NOT |
|------------|-----|-----|
| Semantic/exploratory ("find related to X") | `mcp__memory__retrieve_memory`, zotero MCP, bd search | Broad grep across directories |
| Known pattern ("find class Foo") | Grep with specific pattern + path | Grep with wildcards across large trees |
| File by name | Glob with specific pattern | Grep for filename strings |

**Grep is for needles, not fishing expeditions.** If you're searching for concepts, relationships, or "anything related to X", use semantic search. Reserve grep for when you know exactly what string you're looking for and roughly where it lives.

## Environment Variable Architecture

**How hooks get environment variables:**

1. **`setup.sh`** creates `~/.claude/settings.local.json` with machine-specific paths (AOPS, ACA_DATA)
2. Claude Code reads `settings.local.json` and passes `env` values to all hooks
3. Hooks receive AOPS/ACA_DATA automatically - no hardcoding needed

**Key rules:**

- **NEVER hardcode paths** in framework files (settings.json, hooks, scripts)
- User-specific paths come from `settings.local.json` (created by setup.sh at install time)
- `~/.env` is for shell environment, NOT for Claude Code hooks
- If hooks don't have ACA_DATA: re-run `setup.sh`
