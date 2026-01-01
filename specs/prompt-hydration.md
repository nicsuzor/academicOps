---
title: Prompt Hydration
type: spec
status: implemented
permalink: prompt-hydration
tags: [framework, routing, context, skills]
---

# Prompt Hydration

Transform a raw user prompt into a structured, context-rich prompt matched to the appropriate skill(s).

## Purpose

Users type terse prompts. Agents need:
- **Context** - What's relevant to this task?
- **Workflow** - What approach fits this work?
- **Skills** - Which skill(s) should be invoked?
- **Guardrails** - What constraints apply?

Prompt Hydration bridges this gap automatically on every prompt.

## When It Runs

**Every UserPromptSubmit** - not just `/do`. This closes the "control gap" where freeform prompts previously got baseline context only.

```
User types prompt
    ↓
UserPromptSubmit hook fires
    ↓
Prompt Hydration runs
    ↓
Main agent receives: original prompt + hydrated context
```

## What It Does

### 1. Context Gathering

Parallel searches to understand what's relevant:

| Source | What | Token Budget |
|--------|------|--------------|
| Memory server | Semantic search for related knowledge | ~200 |
| Codebase | Files relevant to the prompt | ~150 |
| Session | Last 3-5 prompts, active skill, TodoWrite state | ~100 |
| Task inbox | Related existing tasks | ~50 |

**Total budget**: ~500 tokens of context

### 2. Workflow Selection

Select composable workflow dimensions based on gathered context. This is intelligent decision-making, not keyword matching - the agent understands the prompt in context and selects the appropriate workflow.

#### Dimension 1: Gate

Must pass before implementation begins.

| Gate | When to Apply |
|------|---------------|
| plan-mode | Framework changes, infrastructure work, multi-file refactors, anything requiring user approval before starting |
| none | Clear scope, single-file changes, debugging, questions |

#### Dimension 2: Pre-work

What to do before implementing.

| Pre-work | When to Apply |
|----------|---------------|
| verify-first | Error reports, "doesn't work" complaints - reproduce before fixing |
| research-first | Unfamiliar territory, unclear requirements, need to explore codebase |
| none | Clear scope, well-understood domain |

#### Dimension 3: Approach

How to implement.

| Approach | When to Apply |
|----------|---------------|
| tdd | Creating new functionality, refactoring with behavioral changes |
| direct | Bug fixes, configuration changes, documentation, simple edits |
| none | Questions, explanations, research tasks (no implementation needed) |

### 3. Skill Matching

Based on context and workflow, identify skill(s) to invoke:

| Domain Signal | Skill |
|---------------|-------|
| Framework files, AXIOMS, HEURISTICS, skills/, hooks/ | `framework` |
| Claude Code hooks, PreToolUse, PostToolUse | `plugin-dev:hook-development` |
| MCP servers, tool integration | `plugin-dev:mcp-integration` |
| New functionality, feature requests | `feature-dev` |
| Python code, pytest, type hints | `python-dev` |
| "Remember", "save to memory", persist knowledge | `remember` |
| dbt, Streamlit, data analysis | `analyst` |
| No domain skill needed | (direct handling) |

### 4. Guardrail Selection

Based on workflow dimensions, select applicable guardrails from `hooks/guardrails.md`:

| Workflow Dimension | Guardrails Applied |
|--------------------|-------------------|
| gate=plan-mode | plan_mode, critic_review |
| pre-work=verify-first | quote_errors_exactly, fix_within_design |
| approach=tdd | require_acceptance_test |
| approach=none (question) | answer_only |
| skill matched | require_skill:[skill-name] |
| any implementation | verify_before_complete, use_todowrite |

## Output Format

Hydration adds structured context to the agent's prompt:

```markdown
## Prompt Hydration

**Workflow**: gate=[X] pre-work=[X] approach=[X]
**Skill(s)**: [skill name(s) or "none"]
**Guardrails**: [list]

### Relevant Context
- [context item from memory/codebase/session]
- [context item]

### Session State
- Recent: "[last prompt]", "[prior prompt]"
- Active skill: [if any]
- Todos: [N] pending, [M] in_progress

### Guidance
[Workflow-specific instructions based on dimensions and guardrails]
```

## Performance Requirements

| Metric | Target |
|--------|--------|
| Typical | 5-10 seconds |
| Max timeout | 15 seconds |

Quality of context gathering matters more than speed. The hydrator should take the time needed to gather relevant context and make intelligent workflow decisions.

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Memory search fails | Continue with codebase/session context only |
| Classification uncertain | Default to `simple` |
| Timeout | Return partial context, log warning |
| Complete failure | Return empty context, agent proceeds with baseline |

Graceful degradation - never crash or block.

## Implementation

### Option A: Fast Script + Main Agent Decision

Hook runs Python script that:
1. Gathers context (memory search, session state, codebase signals)
2. Returns structured context to main agent
3. Main agent makes intelligent workflow selection based on context

**Pros**: Fast context gathering, intelligent decisions by capable model
**Cons**: Uses main agent tokens for decision

### Option B: Background Subagent

Hook spawns Haiku subagent asynchronously:
1. Subagent gathers context AND makes workflow selection
2. Returns structured output before main agent responds

**Pros**: Offloads decision to cheaper model
**Cons**: More latency, may need main agent override for complex cases

**Recommendation**: Start with Option A. The main agent already understands context - just surface relevant information and let it decide.

## Relationship to /do

| Prompt Hydration | /do Command |
|------------------|-------------|
| Automatic, every prompt | Explicit invocation |
| Context + classification only | Full orchestration pipeline |
| Fast, lightweight | Comprehensive, heavier |
| Suggests skills | Enforces skills + checkpoints |

With Prompt Hydration working, `/do` becomes the "extra guardrails" option for complex work, not the only way to get intelligent routing.

## Relationship to WORKFLOWS.md

`WORKFLOWS.md` is the **generated index** that reflects this spec's routing table. The `/audit` skill regenerates it from:
- This spec's workflow dimension definitions
- `hooks/guardrails.md` definitions
- Skill descriptions

## Acceptance Criteria

1. Hydration runs on every UserPromptSubmit
2. Context surfaces relevant information for workflow decisions
3. Latency meets performance requirements
4. Skills are correctly suggested based on domain signals
5. Guardrails match `hooks/guardrails.md` definitions
6. Graceful degradation on errors
7. Agent behavior measurably improves (fewer skill bypasses)

## Files

| File | Purpose |
|------|---------|
| `hooks/user_prompt_submit.py` | Entry point - runs hydration |
| `hooks/prompt_hydration.py` | Core logic (new) |
| `hooks/guardrails.md` | Guardrail definitions (existing) |
| `WORKFLOWS.md` | Generated routing table (existing) |
