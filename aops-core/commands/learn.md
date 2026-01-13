---
name: learn
category: instruction
description: Make minimal, graduated framework tweaks with experiment tracking
allowed-tools: Task
permalink: commands/learn
---

# /learn - Graduated Framework Improvement

## Core Principle: Generalisable, not specific

**Don't hyperfocus**:

❌ **WRONG**: User says 'color' should be spelt 'colour' → Create 'AXIOM: HOW TO SPELL COLOR'
✅ **RIGHT**: User says 'color' should be spelt 'colour' → Consider root cause, track in issue about 'localization', consider escalation only if necessary, note that large issues likely need SPEC updates.

**Don't overreact**:
❌ **WRONG**: User mentions spelling → Create SPELLING AXIOM + spell-check hook + prominent warning
✅ **RIGHT**: User mentions spelling → Add brief note in relevant location, track in Issue, escalate only if necessary

**Start small. If we need a heavier intervention, update the Specs.**

## Workflow

### 0. Agents Are Stateless - You MUST Edit a File or create a task/issue

**This is the most important rule of /learn.**

❌ **WRONG**: "I understand now, I'll do better next time" (no file change)
✅ **RIGHT**: Edit a framework file so future agents get the corrected instruction

Agents are stateless. "Understanding" means nothing without a persistent change. If you complete /learn without using Edit or Write on a framework file, you have failed.

**Common failure mode**: Agent explains what it learned, promises to do better, but makes no file change. This is worthless - the next agent starts fresh with the same flawed instructions.

### 1. Identify Root Cause (Not Proximate Cause)

**We don't control agents** - they're probabilistic. Find the **framework component failure**, not the agent mistake.

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

| Root Cause Category | Definition                     | Fix Location                  |
| ------------------- | ------------------------------ | ----------------------------- |
| Clarity Failure     | Instruction ambiguous/weak     | AXIOMS, skill text, guardrail |
| Context Failure     | Didn't provide relevant info   | Intent router, hydration      |
| Blocking Failure    | Should have blocked but didn't | PreToolUse hook, deny rule    |
| Detection Failure   | Should have caught but didn't  | PostToolUse hook              |
| Gap                 | No component exists for this   | Create new enforcement        |

**Wrong**: "Agent ignored instruction" (proximate cause - we can't fix the agent)
**Right**: "Guardrail instruction too generic for this task type" (root cause - we can fix the guardrail)

**CRITICAL**: "No framework change needed" is NEVER a valid conclusion. If an agent made an error, something in the framework failed to provide the right instruction at the right time. Find that component.

**When you're tempted to say "I just failed to follow instructions"**: That's the proximate cause. Ask: WHY did you fail? What instruction was missing, unclear, or not salient enough? That's the root cause. Fix THAT.

### 2. Check for Prior Occurrences and Document in GitHub Issue

Invoke the logging workflow to identify prior occurrences and track the intervention:

`Skill(skill='framework')` then follow workflow 07-learning-log.md with "[root cause summary]"

The learning-log workflow will search bd issues for related observations and return information about what interventions have been tried to date.

### 3. Choose Intervention Level (Start at Bottom, Escalate with Evidence)

See @docs/ENFORCEMENT.md for mechanism details.

- **Enforcement Ladder** (always start at lowest effective level). 
- **Match root cause to intervention**
- **Escalation rule**: Only move up when you have evidence that lower levels failed. 

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions).

If you need a bigger change, **ABORT** and update/create a Spec instead.

Include in the summary:

- Root cause category and responsible component
- What was changed (with file path)
- What enforcement level (see [[docs/ENFORCEMENT.md]])
- What would trigger escalation

### 5. Update GitHub issue and relevant framework documentation

- Make sure existing documentation is still up-to-date after changes
- Log work done in comment on GitHub issue and reference commits.

### 6. Report

Tell the user:

1. Root cause category and responsible component
2. What you changed (with file path)
3. What enforcement level
4. Link to GitHub Issue tracking this
5. What would trigger escalation
