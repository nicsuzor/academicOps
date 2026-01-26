---
title: Framework Feedback Loops
type: spec
category: architecture
status: active
created: 2026-01-24
related: [[framework-observability]], [[enforcement]], [[workflow-system-spec]]
---

# Framework Feedback Loops

## Overview

The framework improves through structured feedback loops that connect observations to changes. This document describes how observations flow through analysis and become framework improvements.

## The Improvement Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              OBSERVE                                     │
│                                                                         │
│  Session execution generates observables:                               │
│  - Framework Reflections (agent self-report)                            │
│  - Token metrics (resource consumption)                                 │
│  - Skill compliance (suggested vs invoked)                              │
│  - Learning observations (mistakes, corrections)                        │
│                                                                         │
│  See: [[framework-observability]]                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              ANALYZE                                     │
│                                                                         │
│  Human reviews insights JSON and identifies patterns:                   │
│                                                                         │
│  1. Single-session issues                                               │
│     └── May be noise, agent variance, or one-off context               │
│                                                                         │
│  2. Recurring patterns                                                  │
│     └── Same issue across multiple sessions → systemic problem          │
│                                                                         │
│  3. Escalation triggers                                                 │
│     └── Compliance rate < threshold, repeated friction points           │
│                                                                         │
│  Tools: grep insights files, aggregate metrics, skill compliance rates  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              DIAGNOSE                                    │
│                                                                         │
│  Root cause analysis via /learn workflow:                               │
│                                                                         │
│  1. Identify ROOT CAUSE (not proximate cause)                           │
│     - Proximate: "Agent ignored instruction" (can't fix agent)         │
│     - Root: "Instruction unclear for this task type" (can fix)          │
│                                                                         │
│  2. Map to framework component:                                         │
│     ┌─────────────────────┬────────────────────────────────┐            │
│     │ Root Cause Category │ Fix Location                   │            │
│     ├─────────────────────┼────────────────────────────────┤            │
│     │ Clarity Failure     │ AXIOMS, skill text, guardrail  │            │
│     │ Context Failure     │ Hydrator, intent router        │            │
│     │ Blocking Failure    │ PreToolUse hook, deny rule     │            │
│     │ Detection Failure   │ PostToolUse hook               │            │
│     │ Gap                 │ Create new enforcement         │            │
│     └─────────────────────┴────────────────────────────────┘            │
│                                                                         │
│  See: [[commands/learn]]                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              INTERVENE                                   │
│                                                                         │
│  Choose intervention level (start at bottom, escalate with evidence):   │
│                                                                         │
│  Level 1: Prompt-based (soft)                                           │
│    1a. Corollary to existing axiom                                      │
│    1b. New heuristic                                                    │
│    1c. Skill/workflow instruction update                                │
│    1d. Hydrator routing adjustment                                      │
│                                                                         │
│  Level 2: Hook-based (medium)                                           │
│    2a. PostToolUse advisory                                             │
│    2b. PreToolUse warning                                               │
│                                                                         │
│  Level 3: Enforcement (hard)                                            │
│    3a. PreToolUse deny rule                                             │
│    3b. settings.json deny path                                          │
│                                                                         │
│  Level 4: Structural                                                    │
│    4a. New spec                                                         │
│    4b. New workflow                                                     │
│    4c. New skill                                                        │
│                                                                         │
│  See: [[enforcement]]                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              DOCUMENT                                    │
│                                                                         │
│  All changes require documentation:                                     │
│                                                                         │
│  1. Create/update task with:                                            │
│     - Observation (what went wrong)                                     │
│     - Root cause category                                               │
│     - Proposed fix                                                      │
│     - Success metric                                                    │
│                                                                         │
│  2. Emit structured justification:                                      │
│     - Scope (which files changed)                                       │
│     - Rules loaded (P#, H# references)                                  │
│     - Prior art (related tasks)                                         │
│     - Intervention level + change                                       │
│     - Minimality (why not lower level)                                  │
│                                                                         │
│  3. Update enforcement-map.md:                                          │
│     - Map new rule to enforcement mechanism                             │
│     - Document enforcement point (SessionStart, PreToolUse, etc.)       │
│                                                                         │
│  See: [[indices/enforcement-map]]                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              VERIFY                                      │
│                                                                         │
│  Changes are experiments, not permanent solutions:                      │
│                                                                         │
│  1. Observe subsequent sessions for:                                    │
│     - Issue recurrence                                                  │
│     - Unintended side effects                                           │
│     - False positive blocks                                             │
│                                                                         │
│  2. If issue persists:                                                  │
│     - Escalate to higher intervention level                             │
│     - Re-analyze root cause                                             │
│                                                                         │
│  3. If side effects:                                                    │
│     - Narrow scope                                                      │
│     - Add exceptions                                                    │
│     - Revert if necessary                                               │
│                                                                         │
│  4. If resolved:                                                        │
│     - Close task                                                        │
│     - Generalize pattern for future cases                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    └────────────────┐
                                                     │
                                                     ▼
                                              (back to OBSERVE)
```

## Key Workflows

### /learn - Graduated Framework Improvement

The primary feedback workflow. Invoked when:
- User reports an issue
- Agent self-reports a mistake
- Pattern detected across sessions

**Flow:**

```
/learn [observation]
    │
    ├── 0. Load governance context (AXIOMS, HEURISTICS, enforcement-map)
    │
    ├── 0.5. Create/update task FIRST (non-negotiable documentation)
    │
    ├── 1. Identify root cause (framework component, not agent behavior)
    │
    ├── 2. Check for prior occurrences (search existing tasks)
    │
    ├── 3. Choose intervention level (start at bottom)
    │
    ├── 4. Emit structured justification (MANDATORY format)
    │
    ├── 5. Make the fix (as an experiment)
    │
    ├── 6. Generalize the pattern (prevent future instances)
    │
    ├── 7. Create regression test (when testable)
    │
    └── 8. Report (Framework Reflection format)
```

### /log - Learning Observation Capture

Lightweight logging without immediate fix:

```
/log [observation]
    │
    ├── Search for existing related task
    │
    ├── Create or update learn-type task
    │
    └── Report task ID for later /qa analysis
```

Use when:
- Observing a pattern but not ready to fix
- Accumulating evidence before escalation
- Deferring root cause analysis

### /audit - Governance Verification

Periodic health check:

```
/audit
    │
    ├── Check orphan files (specs without links)
    │
    ├── Check enforcement-map completeness
    │
    ├── Verify indices are current
    │
    └── Report gaps and violations
```

## Escalation Rules

### When to Escalate

| Signal | Current Level | Escalate To |
|--------|---------------|-------------|
| Same issue 3x across sessions | 1a (corollary) | 1b (heuristic) |
| Heuristic ignored repeatedly | 1b (heuristic) | 2a (PostToolUse hook) |
| PostToolUse warning ineffective | 2a (advisory) | 3a (PreToolUse deny) |
| Deny rule has false positives | 3a (deny) | Refine or revert |

### Escalation Approval

| Intervention Level | Approval Required |
|-------------------|-------------------|
| 1a: Corollary | Auto (proceed immediately) |
| 1b-1d: Soft prompt | Critic review |
| 2a-2b: Hooks | Critic review |
| 3a-3b: Deny rules | Human approval (AskUserQuestion) |
| 4+: Structural | Human approval + spec |

## Guardrails

### Preventing Runaway Self-Modification

1. **Human in the loop** - Insights are for human review, not automated consumption
2. **Task documentation** - Every change is tracked in a task
3. **Structured justification** - Must explain why this level, why not lower
4. **Escalation gates** - Higher levels require more approval
5. **Experiment framing** - Changes are hypotheses to verify, not permanent solutions

### Preventing Over-Engineering

1. **Start small** - Begin with lowest intervention level
2. **Generalize, don't hyperfocus** - Fix the class of error, not just this instance
3. **No new files** - Edit existing files inline, don't create new context files
4. **Brief interventions** - 1-3 sentences for soft fixes
5. **Spec for big changes** - If more is needed, create a spec first

## Metrics for Self-Improvement

Track these to measure framework health:

| Metric | Source | Target |
|--------|--------|--------|
| Skill compliance rate | insights.skill_compliance | > 0.9 |
| Session success rate | insights.outcome | > 0.8 |
| Custodiet false positive rate | insights.custodiet_blocks | < 0.1 |
| Learning observation frequency | count of learn-type tasks | Stable or decreasing |
| Time to root cause | task creation → fix | < 24 hours for recurring issues |

## Related Documents

- [[framework-observability]] - What we observe and how
- [[enforcement]] - Enforcement mechanism details
- [[workflow-system-spec]] - Workflow selection and composition
- [[commands/learn]] - The /learn command reference
- [[indices/enforcement-map]] - Current enforcement rules
