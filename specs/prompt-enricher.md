---
title: Prompt Enricher Specification
type: spec
status: Draft
permalink: prompt-enricher-spec
tags: [framework, hooks, architecture, routing]
created: 2025-12-30
---

# Prompt Enricher Specification

## Purpose

Define the **Prompt Enricher** - a fast subagent that runs on every user prompt to intelligently enrich it with relevant context before the main agent processes it.

## Architectural Position

```
SessionStart (baseline injected)
    ↓
User submits prompt
    ↓
UserPromptSubmit hook fires
    ↓
**Prompt Enricher runs** (THIS SPEC)
    ↓
Main agent receives: original prompt + baseline + enriched context
    ↓
Agent processes request
```

The Prompt Enricher sits between the raw user prompt and the main agent, adding intelligence to every interaction.

## What It Does

### Input

The Prompt Enricher receives:
1. **User prompt** - The raw text the user typed
2. **Conversation history** - Prior turns in the session
3. **Instructions** - Defined in a separate instructions file (see below)

### Output

The Prompt Enricher returns `additionalContext` containing:
1. **Relevant context** - Information the main agent needs for this specific prompt
2. **Guardrails** - Which rules/heuristics are particularly relevant
3. **Suggested approach** - Recommendations for how to handle the request

### What It Does NOT Do

- Does NOT execute the user's request
- Does NOT make tool calls
- Does NOT replace the main agent's judgment
- Does NOT add latency beyond acceptable threshold (see Performance)

## Instructions Location

The Prompt Enricher applies instructions from a defined location:

```
$AOPS/hooks/prompts/prompt-enricher-instructions.md
```

This file is the **single source of truth** for what the enricher does. It contains:
- Classification rules (what type of request is this?)
- Context gathering rules (what information is relevant?)
- Guardrail selection rules (which heuristics apply?)
- Output format specification

**Separation of concerns**: The enricher mechanism (this spec) is separate from the enricher behavior (the instructions file). Changing behavior = edit instructions file. Changing mechanism = edit this spec.

## Design Principles

### 1. Fast

The enricher must complete quickly. Users shouldn't notice latency.

- **Model**: Use fast model (Haiku or equivalent)
- **Scope**: Minimal work - classify and gather, don't deliberate
- **Timeout**: Hard limit (e.g., 2 seconds) - return partial results if exceeded

### 2. Reliable

The enricher must not fail silently.

- **On error**: Return empty context, log error, continue (don't block user)
- **On timeout**: Return partial results if available
- **Never**: Crash the session or require user intervention

### 3. Transparent

The enricher's additions should be visible and understandable.

- **Labeled output**: Enriched context clearly marked (not mixed with user prompt)
- **Traceable**: What the enricher added can be inspected
- **Overridable**: User can bypass with explicit instruction

### 4. Additive Only

The enricher adds context, never removes or modifies the user's prompt.

- **Original preserved**: User's exact words pass through unchanged
- **Context appended**: Enriched context added alongside, not instead of
- **No censoring**: Enricher doesn't filter or block user input (that's policy_enforcer's job)

## Enrichment Categories

The instructions file defines what categories of enrichment to perform:

### Category 1: Task Classification

Classify the user's request into types:
- Question (needs answer, not action)
- Implementation (needs code changes)
- Debug (needs investigation)
- Framework (affects $AOPS/)
- Research (needs information gathering)
- ...

Classification determines which guardrails and approaches are relevant.

### Category 2: Context Gathering

Based on classification, gather relevant context:
- Memory search for related information
- Codebase search for relevant files
- Task list for related work
- Recent session activity

**Constraints**: Limited time budget. Gather what's most likely useful, not exhaustive.

### Category 3: Guardrail Selection

Based on classification, select relevant guardrails from HEURISTICS.md:
- Framework work → H2 (Skill-First), Plan Mode, critic review
- Debug work → H3 (Verify First), H5 (Error Messages)
- Questions → H19 (Questions Require Answers)
- ...

Return specific heuristic numbers so main agent knows which rules are most relevant.

### Category 4: Approach Suggestion

Based on classification and context, suggest approach:
- Which skill(s) might be relevant
- Whether this needs planning vs direct action
- Whether subagent delegation is appropriate
- ...

**Note**: Suggestions only. Main agent makes final decision.

## Output Format

The enricher returns structured `additionalContext`:

```markdown
## Prompt Enrichment

**Classification**: [task type]

**Relevant Context**:
- [context item 1]
- [context item 2]

**Applicable Guardrails**: H[n], H[m], ...

**Suggested Approach**: [brief recommendation]
```

This format allows the main agent to quickly parse and apply the enrichment.

## Implementation Options

### Option A: Async Subagent (Recommended)

Hook spawns a background subagent that runs in parallel:
1. Hook starts enricher subagent asynchronously
2. Hook returns immediately (no blocking)
3. Enricher result arrives as system context before main agent responds
4. If enricher is slow, main agent proceeds with baseline only

**Pros**: No perceived latency, graceful degradation
**Cons**: More complex, result may arrive late

### Option B: Sync Subagent

Hook spawns subagent and waits for result:
1. Hook starts enricher subagent
2. Hook waits for result (with timeout)
3. Hook returns result as additionalContext
4. Main agent receives enriched prompt

**Pros**: Simple, guaranteed enrichment
**Cons**: Adds latency to every prompt

### Option C: Hook-Only (No Subagent)

Hook does enrichment directly via script:
1. Hook runs Python script
2. Script does keyword matching, memory queries
3. Script returns context without LLM

**Pros**: Fastest, simplest
**Cons**: Not intelligent, can't understand intent

**Recommendation**: Start with Option C for reliability, add Option A when proven.

## Relationship to Existing Components

### vs. SessionStart Injection

| SessionStart | Prompt Enricher |
|--------------|-----------------|
| Runs once per session | Runs every prompt |
| Provides baseline context | Provides prompt-specific context |
| Static (same every time) | Dynamic (varies by prompt) |
| Always succeeds or fails hard | Gracefully degrades |

### vs. /do Command

| /do Command | Prompt Enricher |
|-------------|-----------------|
| User explicitly invokes | Automatic on every prompt |
| Full routing + execution | Context only, no execution |
| Main agent flow | Pre-agent enrichment |

The Prompt Enricher could make `/do` less necessary by providing some of its benefits automatically.

### vs. intent-router Agent

The current `intent-router` agent is a **specific implementation** of this spec's concept. This spec generalizes and clarifies what that component should do.

## Performance Requirements

| Metric | Target |
|--------|--------|
| P50 latency | < 500ms |
| P95 latency | < 1500ms |
| Timeout | 2000ms (hard limit) |
| Failure rate | < 1% |

If enricher can't meet latency target, return partial/empty result rather than blocking.

## Verification

### Test: Enrichment appears in context

After submitting prompt, main agent should see enrichment markers in its context.

### Test: Graceful timeout

Simulate slow enricher - main agent should still receive prompt and function.

### Test: Classification accuracy

Sample prompts should be classified correctly per instructions file.

## Open Questions

1. **What's in the instructions file?** - Need to define the actual classification rules, context gathering strategies, etc.
2. **How much context is too much?** - Token budget for enrichment
3. **Should enrichment be optional?** - User setting to disable?

## Related Documents

- [[specs/session-start-injection.md]] - Baseline context (runs before this)
- [[docs/execution-flow.md]] - Where this fits in the flow
- [[agents/intent-router.md]] - Current implementation (to be aligned with this spec)
- [[HEURISTICS.md]] - Source of guardrails to select

## Acceptance Criteria

- [ ] Instructions file location defined and documented
- [ ] Enricher runs on every UserPromptSubmit
- [ ] Output format is consistent and parseable
- [ ] Latency meets performance requirements
- [ ] Graceful degradation on timeout/error
- [ ] Main agent behavior improves with enrichment (measured)
