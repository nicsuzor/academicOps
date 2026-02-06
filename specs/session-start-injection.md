---
title: Context Loading Specification
type: spec
category: spec
status: Active
permalink: context-loading-spec
tags: [framework, hooks, architecture, session]
created: 2025-12-30
updated: 2026-01-22
---

# Context Loading Specification

## User Story

As a **framework user**, I want agents to receive minimal context at session start with additional context loaded just-in-time, so that sessions start quickly while still having access to relevant information when needed.

## Purpose

Define what information agents receive and when. This spec governs the **three-tier loading architecture** that balances minimal startup cost with just-in-time context availability.

## Design Principle

**Minimal baseline, maximal JIT.** Agents start with only what they need to understand the framework and project. Everything else loads on-demand when relevant to the task.

## Three-Tier Architecture

```
Tier 1: Framework Core (ALL agents)
    |
Tier 2: Project Context (project-scoped agents)
    |
Tier 3: JIT Injection (prompt-hydrator or on-demand)
```

### Tier 1: Framework Core

**File**: `$AOPS/CORE.md`

**Who reads**: ALL agents, at session start.

**Contains** (ESSENTIAL only):
- Framework tool inventory (what MCP servers exist, what they do)
- Task system usage (create, update, complete, search)
- Memory system usage (store, retrieve, remember skill)
- Git/submodule handling rules

**Does NOT contain**:
- Detailed workflows (-> Tier 3)
- Heuristics/axioms (-> Tier 3)
- Skill-specific instructions (-> Tier 3)
- Project-specific context (-> Tier 2)

**Contract**:
- Must fit in ~2KB (token budget: ~500 tokens)
- Every line must answer: "Does an agent need this to START working?"
- If no, move to Tier 3

### Tier 2: Project Context

**File**: `$cwd/.agent/CORE.md`

**Who reads**: Agents working in a project directory.

**Contains**:
- Project-specific conventions
- Local tool configuration
- Domain knowledge essential for the project
- Links to project documentation

**Contract**:
- Optional - projects without this file use Tier 1 only
- Must be project-specific (no framework content)
- Replaces per-project CLAUDE.md for framework-aware projects

### Tier 3: JIT Injection

**Mechanism**: `prompt-hydrator` agent or skill-specific loading.

**Who uses**:
- Agents WITH prompt hooks: Hydrator loads context based on task
- Agents WITHOUT prompt hooks: MUST read `$AOPS/aops-core/agents/prompt-hydrator.md` and self-hydrate

**Contains** (loaded on-demand):
- Workflow instructions
- Skill/command documentation
- Heuristics relevant to task
- Reference material
- Historical context from memory

**Contract**:
- Never front-load speculatively
- Load only what the current task requires
- Hydrator decides relevance, not session-start hooks

## File Inventory

| Tier | File | Purpose | Size Target |
|------|------|---------|-------------|
| 1 | `$AOPS/CORE.md` | Framework tools | ~2KB |
| 2 | `$cwd/.agent/CORE.md` | Project context | ~1KB |
| 3 | `$AOPS/aops-core/agents/prompt-hydrator.md` | Fallback for non-hooked agents | ~1KB |
| 3 | Various | JIT-loaded by hydrator | As needed |

## What Was Removed (from v1 spec)

The previous spec mandated 4 files at session start:
- FRAMEWORK-PATHS.md -> Merged into CORE.md (essential paths only)
- AXIOMS.md -> Tier 3 (JIT when relevant)
- HEURISTICS.md -> Tier 3 (JIT when relevant)
- CORE.md -> Retained (Tier 1), but stripped to essentials

**Rationale**: Front-loading principles/heuristics costs ~3KB+ tokens per session. Most sessions don't need most heuristics. JIT loading saves tokens and reduces cognitive load.

## Implementation

### SessionStart Hook

```bash
# Inject Tier 1 only
cat $AOPS/CORE.md
```

### Project Detection

```bash
# If project has .agent/CORE.md, inject Tier 2
if [ -f "$cwd/.agent/CORE.md" ]; then
  cat "$cwd/.agent/CORE.md"
fi
```

### Prompt Hook (UserPromptSubmit)

```bash
# Spawn hydrator for Tier 3 context
# Hydrator reads task, loads relevant context
```

### Non-Hooked Agents

Agents spawned without hooks (e.g., subagents via Task tool) must:
1. Read `$AOPS/aops-core/agents/prompt-hydrator.md`
2. Self-assess what context they need
3. Load relevant files before executing

## Verification

### Test: Tier 1 loads correctly
```bash
# Session starts with CORE.md content visible
claude --print-context | grep "Framework tool inventory"
```

### Test: Tier 2 loads when present
```bash
mkdir -p .agent
echo "# Project Context" > .agent/CORE.md
# New session should show project context
```

### Test: Non-hooked agent self-hydrates
```bash
# Spawn subagent, verify it reads prompt-hydrator.md
```

## Related Documents

- [[CORE.md]] - Tier 1 framework core
- [[prompt-hydrator.md]] - Tier 3 hydration agent
- [[enforcement-map.md]] - Loading rule enforcement

## Acceptance Criteria

- [ ] $AOPS/CORE.md contains ONLY essential framework tool info (~2KB)
- [ ] $cwd/.agent/CORE.md convention documented and templated
- [ ] SessionStart hook injects Tier 1 only
- [ ] Prompt hook triggers hydrator for Tier 3
- [ ] Non-hooked agents have clear self-hydration path
- [ ] Token savings measured vs. v1 spec
