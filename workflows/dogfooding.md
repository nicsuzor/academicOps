---
id: dogfooding
category: meta
---

# Dogfooding Workflow

## Overview

Operational workflow for framework self-improvement. Apply during any task likely to surface framework friction. Every agent interaction serves dual objectives: complete the task AND improve the system.

**Reference**: [[archived/specs/reflexivity]] (architectural spec)

## When to Use

Apply this workflow during:

- Feature development on the framework itself
- Tasks where instructions feel unclear or missing
- Work that reveals gaps in context, routing, or guardrails
- Any session where you notice friction

**Key signal**: "This is harder than it should be" or "I had to work around something."

## Core Principle

**We don't control agents** - they're probabilistic. Framework improvement targets the system, not agent behavior.

| Wrong (Proximate) | Right (Root Cause) |
|-------------------|---------------------|
| "Agent skipped skill" | "Router didn't explain WHY skill needed" |
| "Agent didn't verify" | "Guardrail instruction too generic" |
| "I forgot to check X" | "Instruction for X not salient at decision point" |

## Decision Tree

When you notice something during work:

```
Is this a one-time observation? (friction, missing context, unexpected behavior)
  └─ YES → /log [observation]
           Creates bd issue, runs in background, continue working

Is this a recurring pattern? (3+ observations with same root cause)
  └─ YES → Check if heuristic exists in HEURISTICS.md
           └─ If exists but wasn't followed → Note in bd issue
           └─ If doesn't exist → /learn to propose new heuristic

Is this blocking your current task?
  └─ YES → Fix minimally, document in bd issue, continue
           Use /learn for tracked intervention

At session end:
  └─ Follow Framework Reflection format in AGENTS.md
     Log remaining observations before closing
```

## During-Task Checklist

While working, notice:

1. **Routing friction** - Did you know which workflow/skill to use? If unclear, that's a signal.
2. **Missing context** - What information didn't surface that should have? (Memory search returned nothing? Hydrator missed relevant files?)
3. **Instruction gaps** - What guidance was absent at a decision point?
4. **Guardrail failures** - What constraint would have prevented a mistake?
5. **Tool issues** - Did a tool behave unexpectedly? Return unhelpful errors?

**Don't stop to fix everything.** Log observations with `/log`, continue working.

## Integration Points

| Component | Role | When to Use |
|-----------|------|-------------|
| `/log [obs]` | Route observations to bd issues | During work - friction noticed |
| `/learn [issue]` | Make tracked interventions | Pattern confirmed, fix needed |
| Framework Reflection | Session-end summary | Every session end |
| `session-insights` | Post-hoc analysis | Batch processing of sessions |
| HEURISTICS.md | Synthesis destination | 3+ issues → new heuristic |

## Examples

### Example 1: Missing Context

**Observation**: "Hydrator didn't inject relevant bd issues into context"

```
/log Hydrator missed related bd issues when routing this task - search query may be too narrow
```

**Result**: bd issue created, framework agent categorizes root cause, work continues.

### Example 2: Unclear Instruction

**Observation**: "AGENTS.md says to use TodoWrite but doesn't say when to skip it"

```
/log TodoWrite guidance in AGENTS.md doesn't cover when NOT to use it - led to unnecessary overhead on simple task
```

### Example 3: Pattern Emerges

After 3+ observations about hydrator search quality:

```
/learn aops-1abc
```

This triggers the graduated intervention workflow - review pattern, propose fix, create regression test.

### Example 4: Session-End Reflection

At session end, include in response:

```markdown
## Framework Reflection

**Request**: [what was asked]
**Guidance received**: Hydrator suggested feature-dev workflow
**Followed**: Yes
**Outcome**: success
**Accomplishments**: [list]
**Friction points**: Hydrator search missed related issues
**Root cause**: N/A (success)
**Proposed changes**: Expand hydrator search to include bd issues by keyword
**Next step**: Filed as aops-2xyz
```

## What NOT to Do

- **Don't stop work to fix every friction** - Log it, continue
- **Don't create new files for observations** - Use bd issues
- **Don't fix agents** - Fix the framework that guides them
- **Don't skip session reflection** - It's how patterns surface

## Quality Gates

- [ ] Observations logged to bd (not local notes)
- [ ] Root causes identified (not proximate causes)
- [ ] Session ends with Framework Reflection
- [ ] Recurring patterns escalated via /learn
- [ ] Heuristics reference bd issue evidence (P#nn format)

## See Also

- [[archived/specs/reflexivity]] - Architectural specification
- [[bd-workflow]] - Issue tracking workflow
- [[feature-dev]] - Development workflow (applies dogfooding)
- HEURISTICS.md - Synthesis destination for patterns
