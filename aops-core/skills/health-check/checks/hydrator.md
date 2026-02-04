---
name: hydrator-check
description: Health check evaluation prompt for the Prompt Hydrator component
---

# Hydrator Health Check

Evaluation prompt for assessing the Prompt Hydrator's performance.

## Component Overview

The Prompt Hydrator (`agents/prompt-hydrator.md`) transforms terse user prompts into execution plans. It decides scope, workflow, and what to do now vs later.

## Evaluation Prompt

You are evaluating the **Prompt Hydrator** component's performance across recent session transcripts.

### What to Look For

Search transcripts for:
- `HYDRATION RESULT` blocks (hydrator output)
- `prompt-hydrator` agent invocations
- References to hydration or execution plans

### Assessment Criteria

#### 1. Prompt-to-Plan Transformation Quality

| Rating | Criteria |
|--------|----------|
| **Good** | Plan captures user intent accurately, appropriate scope, clear execution steps |
| **Acceptable** | Minor misinterpretations, slightly over/under-scoped, steps need clarification |
| **Poor** | Misses key intent, wrong scope assessment, unclear or wrong workflow |

**Evidence to cite**: Compare user prompt to hydration output. Did the plan match what the user actually wanted?

#### 2. Context Gathering Completeness

| Rating | Criteria |
|--------|----------|
| **Good** | Relevant files identified, memory queried appropriately, task state considered |
| **Acceptable** | Some context missed but plan still workable |
| **Poor** | Critical context missed, leading to rework or confusion |

**Evidence to cite**: Did the hydrator suggest reading files that turned out to be necessary? Did it miss important context?

#### 3. Workflow Selection Accuracy

| Rating | Criteria |
|--------|----------|
| **Good** | Correct workflow from WORKFLOWS.md decision tree |
| **Acceptable** | Reasonable workflow, minor mismatch |
| **Poor** | Wrong workflow entirely, causing process friction |

**Evidence to cite**: Compare selected workflow to task characteristics. Was it the right choice?

#### 4. Task Routing Appropriateness

| Rating | Criteria |
|--------|----------|
| **Good** | Correctly identified existing task or created appropriate new task |
| **Acceptable** | Task created but could have used existing, or vice versa |
| **Poor** | Duplicate tasks created, orphan work, wrong project assignment |

**Evidence to cite**: Check task system state before/after. Was routing correct?

#### 5. Deferred Work Capture

| Rating | Criteria |
|--------|----------|
| **Good** | Multi-session work properly scoped, deferred items captured |
| **Acceptable** | Some deferred work noted but incomplete |
| **Poor** | Work lost, no capture of items for later |

**Evidence to cite**: For multi-session work, was there a decomposition or follow-up plan?

### Output Format

```markdown
## Hydrator Health Assessment

**Overall Health**: [Healthy | Needs Attention | Critical]

### Instance Analysis

#### Instance 1: [Session ID, Turn N]
**User prompt**: "[quote]"
**Hydration output**: [summary]
**Assessment**:
- Transformation: [Good/Acceptable/Poor] - [reason]
- Context: [Good/Acceptable/Poor] - [reason]
- Workflow: [Good/Acceptable/Poor] - [reason]
- Routing: [Good/Acceptable/Poor] - [reason]

[Repeat for each instance found]

### Aggregate Findings

**Strengths**:
- [Pattern that works well]

**Weaknesses**:
- [Pattern that needs improvement]

### Recommendations

1. [Specific actionable recommendation]
2. [...]

### Evidence Summary

| Session | Turn | Issue | Severity |
|---------|------|-------|----------|
| [id] | [N] | [brief description] | [High/Med/Low] |
```

## Red Flags

Immediate attention needed if:
- Hydrator consistently misses user intent
- Wrong workflows selected >30% of time
- Task routing creates duplicates or orphans
- Multi-session work consistently lost
