---
name: learn
category: instruction
description: Make minimal, graduated framework tweaks with experiment tracking
allowed-tools: Read,Edit,Write,Glob,Grep,Skill
permalink: commands/learn
---

# /learn - Graduated Framework Improvement

The user is telling you something needs to change. Your job: **minimal intervention** that we can **track and verify**.

See [[specs/reflexivity]] for the complete data architecture.

## MANDATORY: Invoke Framework Skill First

```
Skill(skill="framework")
```

This ensures changes are categorical (generalizable rules), not ad-hoc fixes.

## Core Principle: Don't Overreact

❌ **WRONG**: User mentions spelling → Create SPELLING AXIOM + spell-check hook + prominent warning
✅ **RIGHT**: User mentions spelling → Add brief note in relevant location, track in Issue

**Start small. If we need a heavier intervention, update the Specs.**

## Workflow

### 1. Identify Root Cause (Not Proximate Cause)

**We don't control agents** - they're probabilistic. Find the **framework component failure**, not the agent mistake.

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

| Root Cause Category | Definition | Fix Location |
|---------------------|------------|--------------|
| Clarity Failure | Instruction ambiguous/weak | AXIOMS, skill text, guardrail |
| Context Failure | Didn't provide relevant info | Intent router, hydration |
| Blocking Failure | Should have blocked but didn't | PreToolUse hook, deny rule |
| Detection Failure | Should have caught but didn't | PostToolUse hook |
| Gap | No component exists for this | Create new enforcement |

**Wrong**: "Agent ignored instruction" (proximate cause - we can't fix the agent)
**Right**: "Guardrail instruction too generic for this task type" (root cause - we can fix the guardrail)

### 2. Check for Prior Occurrences

Search GitHub Issues for related observations:
```bash
gh issue list --repo nicsuzor/academicOps --label learning --search "[keywords]"
```

**If found**: This is a recurrence. Consider escalating intervention level.

**If new**: Use `/log` first to document the observation.

### 3. Choose Intervention Based on Root Cause Category

Match intervention to root cause category:

| Root Cause | Intervention |
|------------|--------------|
| Clarity Failure | Strengthen instruction text, add task-specific reasoning |
| Context Failure | Improve router classification, add context source |
| Blocking Failure | Fix hook pattern, add deny rule |
| Detection Failure | Improve hook detection logic |
| Gap | Create new enforcement at appropriate level |

Consult [[RULES]] for enforcement level ladder. **Start soft, escalate only with evidence.**

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions).

If you need a bigger change, **ABORT** and update/create a Spec instead.

### 5. Document in GitHub Issue

Track the intervention in the relevant Issue:
- Root cause category and responsible component
- What was changed (with file path)
- What enforcement level (see [[docs/ENFORCEMENT.md]])
- What would trigger escalation

Per [[specs/reflexivity]], interventions are tracked as Issue comments, not separate experiment files.

### 6. Report

Tell the user:
1. Root cause category and responsible component
2. What you changed (with file path)
3. What enforcement level
4. Link to GitHub Issue tracking this
5. What would trigger escalation
