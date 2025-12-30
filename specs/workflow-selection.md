---
title: Workflow Selection
type: spec
status: draft
permalink: workflow-selection
tags: [framework, workflows, orchestration, routing]
---

# Workflow Selection

**Status**: Draft (decisions pending)

## Decision Tree (Proposed)

```mermaid
graph TD
    A[Task Received] --> B{Slash Command?}
    B -->|Yes| C[Claude Code Handles]
    B -->|No| D{Question Only?}
    D -->|Yes| E[Answer then STOP]
    D -->|No| F{Framework Files?}
    F -->|Yes| G[/meta]
    F -->|No| H{Structured Dev?}
    H -->|Yes| I[/supervise tdd]
    H -->|No| J{Batch Operation?}
    J -->|Yes| K[/supervise batch-review]
    J -->|No| L{Simple Single Action?}
    L -->|Yes| M[Just Do It]
    L -->|No| N[/meta - Default]
```

## Problem Statement

Agents don't know which workflow to use for different task types. This causes:
- Confusion: "No framework workflow exists. I'll use the generic supervisor process."
- Wrong tool: Using `/supervise` when `/meta` is appropriate (or vice versa)
- Skipped orchestration: Doing complex work without proper structure
- Missed workflows: Framework workflows (`01-design`, `02-debug`) not surfaced

## What Exists (Consolidated)

### Orchestration Commands

| Command | Role | Tools Available | Documented Purpose |
|---------|------|-----------------|-------------------|
| `/meta` | Strategic brain + executor | Full (Read, Edit, Bash, etc.) | "Handle framework problems end-to-end. Design AND build." |
| `/supervise {workflow}` | Strict delegator | Only Task, Skill, TodoWrite, AskUserQuestion | "Structured work with quality gates, delegates to subagents" |

### Workflow Templates

**Supervisor Workflows** (`skills/supervisor/workflows/`):

| Workflow | Purpose | Scope |
|----------|---------|-------|
| `tdd` | Test-first development with pytest | Python code with defined acceptance criteria |
| `batch-review` | Parallel batch processing | Multiple files needing same operation |
| `skill-audit` | Review skills for content separation | Skill quality review |

**Framework Workflows** (`skills/framework/workflows/`):

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `01-design-new-component` | Adding new capability | New hook, skill, script, command |
| `02-debug-framework-issue` | Diagnosing failures | Framework component not working |
| `03-experiment-design` | Experiment patterns | Testing hypothesis about behavior |
| `04-monitor-prevent-bloat` | Anti-bloat | Periodic framework cleanup |
| `06-develop-specification` | Collaborative spec development | New feature planning |

### Intent Router Classification

The [[intent-router-spec|intent-router-spec]] router (`hooks/prompts/intent-router.md`) classifies prompts and provides guidance:

| Pattern | Current Guidance |
|---------|-----------------|
| Framework files | `Skill("framework")`, Plan Mode, TodoWrite, critic |
| Debug/error | VERIFY STATE FIRST, TodoWrite checklist |
| Question | Answer then STOP |
| Multi-step | TodoWrite, commit after logical units |
| Python | `Skill("python-dev")`, tests first |
| Simple | Just do it |

**Gap**: Router suggests skills but doesn't route to `/meta` vs `/supervise`.

---

## Unresolved: When to Use Each Workflow

### OPTION A: Task-Type Based Selection

| Task Type | Workflow | Rationale |
|-----------|----------|-----------|
| Framework file edits (skills, hooks, specs, commands) | `/meta` | Needs strategic context + implementation power |
| Python development with defined acceptance criteria | `/supervise tdd` | Needs delegation + quality gates |
| Batch operations on multiple files | `/supervise batch-review` | Parallel processing with quality gates |
| Simple single-action tasks | Just do it | Overhead exceeds benefit |
| Questions | Answer then stop | No workflow needed |

**Problem**: Doesn't distinguish "edit a spec" from "build a new feature". Both touch framework files but have different complexity.

### OPTION B: Complexity-Based Selection

| Complexity | Workflow | Criteria |
|------------|----------|----------|
| Trivial | Just do it | Single file, single change, obvious outcome |
| Moderate | `/meta` | Multiple files OR requires context loading OR design decisions |
| Structured | `/supervise {workflow}` | Well-defined phases, acceptance criteria, delegation needed |

**Problem**: "Moderate" is subjective. Agents may misjudge complexity.

### OPTION C: Tool-Need Based Selection

| Need | Workflow | Rationale |
|------|----------|-----------|
| Must directly edit/read files | `/meta` | Has implementation tools |
| Must delegate all work | `/supervise` | Forces subagent orchestration |
| Neither | Just do it or answer question | No orchestration needed |

**Problem**: Doesn't capture WHEN to force delegation vs allow direct work.

### OPTION D: Hybrid (Current Implicit Practice)

```
IF slash command → Claude Code handles
IF question → Answer then STOP
IF framework file edit → /meta (loads context, Plan Mode, critic)
IF structured dev with acceptance criteria → /supervise tdd
IF batch operation → /supervise batch-review
IF simple single action → Just do it
ELSE → /meta (default for complex work)
```

**Problem**: "Framework file edit" includes spec edits, skill edits, hook edits - but some are simple fixes, others are major features.

---

## Unresolved: Framework Workflows Integration

Currently framework workflows (`01-design`, `02-debug`, etc.) are:
- Buried in `skills/framework/workflows/`
- Not visible to intent router
- Only surfaced when `/meta` or `Skill("framework")` is invoked

### OPTION 1: Surface in Intent Router

Add to intent router classification table:
```
| new hook/skill/command | Framework | Skill("framework") + workflow 01-design |
| framework debugging | Framework | Skill("framework") + workflow 02-debug |
```

**Pro**: JIT guidance includes specific workflow
**Con**: Intent router becomes more complex

### OPTION 2: Leave as Internal to Framework Skill

Framework skill already loads these workflows when relevant. Keep routing simple.

**Pro**: Separation of concerns
**Con**: Agents don't know workflows exist until inside framework skill

### OPTION 3: Create Commands for Key Workflows

```
/debug-framework → invokes framework skill + 02-debug workflow
/design-component → invokes framework skill + 01-design workflow
```

**Pro**: Explicit invocation, user can choose
**Con**: More commands to maintain, namespace concerns

---

## Unresolved: What Counts as "Simple"?

Intent router says "Simple → Just do it" but criteria undefined.

### OPTION A: Line Count Heuristic

Simple = single file + <10 lines changed

**Problem**: Some 2-line changes are architectural; some 50-line changes are mechanical

### OPTION B: Decision Count Heuristic

Simple = zero design decisions required

**Problem**: Agents misjudge what requires decisions

### OPTION C: Explicit Enumeration

Simple tasks:
- Typo fixes
- Adding log statements
- Single import additions
- Comment updates

Everything else requires at least TodoWrite.

**Problem**: Enumeration is never complete

### OPTION D: Default to TodoWrite

If in doubt, use TodoWrite. Cost of over-tracking < cost of losing context.

**Problem**: Overhead for truly trivial tasks

---

## Acceptance Criteria (When Resolved)

1. **Clear decision tree**: Given any task description, an agent can determine the appropriate workflow in <3 reasoning steps
2. **Intent router integration**: Router guidance includes workflow selection, not just skill suggestions
3. **No orphan workflows**: All workflows discoverable via README, INDEX, or intent router
4. **Documented in README**: Workflow selection explained in README.md Quick Start or new section

## Implementation (Pending Decisions)

After resolving the options above:

1. Update `hooks/prompts/intent-router.md` with workflow routing
2. Update `$AOPS/README.md` with workflow selection guide
3. Update `$AOPS/INDEX.md` with workflow cross-references
4. Consider new commands if OPTION 3 chosen for framework workflows

---

## Open Questions for User

1. **Which selection model?** (A: task-type, B: complexity, C: tool-need, D: hybrid, or other?)
2. **Framework workflows**: Surface in router (1), keep internal (2), or create commands (3)?
3. **"Simple" criteria**: How do we define tasks that need no orchestration?
4. **Is `/meta` the default?** For anything complex that doesn't match a specific workflow, should agents default to `/meta`?

