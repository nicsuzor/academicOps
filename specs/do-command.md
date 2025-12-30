---
title: /do Command
type: spec
status: implementing
permalink: do-command-spec
tags:
  - framework
  - workflow
  - command
  - intent-routing
created: 2025-12-29
---

# /do Command

**Status**: Implementing

## Problem Statement

Current prompt handling is fragmented across multiple components:

| Component | Purpose | Problem |
|-----------|---------|---------|
| UserPromptSubmit hook | Inject context per prompt | Currently noop, no routing |
| `prompt-writer` agent | Thorough investigation | Separate flow from routing |
| `/q` command | Queue capture | Creates separate queue files |
| `/pull` command | Queue retrieval | Disconnected from tasks |
| `supervisor` skill | Workflow execution | Not integrated with routing |

This creates cognitive overhead and multiple entry points that don't compose well.

## Solution: Single Funnel

One command that does everything: routing + enrichment + workflow selection + todo creation + handoff.

```
/do [user's fragment]
    |
    v
Intent-Router-Agent (Sonnet):
  - Parallel: memory search + codebase search + file reads
  - Hydrates fragment with found context
  - Identifies: task type, workflow, guardrails
  - Creates todo list with steps
    |
    v
Returns: enriched prompt + structured output
    |
    v
Main agent executes with full context (or delegates to supervisor)
```

## Architecture

### Entry Point: `/do` command

Simple command that:
1. Spawns intent-router-agent with user's fragment
2. Receives structured output (enriched prompt, todo items, workflow)
3. Creates TodoWrite from returned steps
4. Proceeds with execution (directly or via supervisor)

### Intent-Router-Agent

The workhorse. Runs parallel searches, enriches the prompt, returns structured guidance.

**Inputs:**
- User's raw fragment

**Parallel Operations:**
1. `mcp__memory__retrieve_memory` - semantic search for related context
2. `Grep/Glob` - codebase search for mentioned files/concepts
3. `Read` - load relevant files identified

**Classification:**
- Task type (framework, debug, feature, question, persist, analysis)
- Workflow (tdd, batch-review, generic)
- Guardrails (Plan Mode, acceptance testing, critic review)

**Outputs (structured):**
```yaml
task_type: framework
workflow: tdd
guardrails:
  plan_mode: true
  acceptance_testing: true
  critic_review: true
enriched_context: |
  [Relevant context from memory and codebase]
todo_items:
  - "Research existing implementation"
  - "Write failing test"
  - "Implement feature"
  - "Run tests"
  - "Commit and push"
original_fragment: "[user's exact words]"
```

### Execution Flow

After intent-router returns:

1. **Create TodoWrite** from `todo_items`
2. **Apply guardrails**:
   - `plan_mode: true` → Enter Plan Mode before implementation
   - `acceptance_testing: true` → Ensure todo includes verification step
   - `critic_review: true` → Invoke critic before presenting plan
3. **Execute** - either directly or delegate to supervisor for complex workflows

## Task Classification Table

| Pattern | Type | Workflow | Guardrails |
|---------|------|----------|------------|
| skills/, hooks/, AXIOMS, HEURISTICS, framework | Framework | generic | plan_mode, critic_review |
| create hook, PreToolUse, PostToolUse | CC Hook | generic | plan_mode |
| error, bug, broken, debug | Debug | generic | verify_first |
| implement, build, create, refactor | Feature | tdd | acceptance_testing |
| how, what, where, explain, "?" | Question | none | answer_only |
| pytest, TDD, Python, test | Python | tdd | acceptance_testing |
| save, remember, persist | Persist | none | skill_remember |
| dbt, Streamlit, data, statistics | Analysis | generic | skill_analyst |

## Components to Delete

| Component | Replaced By |
|-----------|-------------|
| UserPromptSubmit routing approach | `/do` command (explicit invocation) |
| `agents/prompt-writer.md` | `intent-router` agent |
| `commands/q.md` | `/do` (captures directly) |
| `commands/pull.md` | TodoWrite (native tracking) |
| `$ACA_DATA/queue/` directory | Not needed |

## Acceptance Criteria

- [ ] `/do [fragment]` enriches and executes in single flow
- [ ] Intent-router runs parallel context searches
- [ ] TodoWrite created automatically with appropriate steps
- [ ] Guardrails applied based on task classification
- [ ] No separate queue files needed
- [ ] Works for all task types in classification table

## Non-Goals

- Real-time streaming of enrichment progress
- Complex priority routing (simple FIFO via todo list)
- Backward compatibility with queue files
