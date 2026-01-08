---
name: learn
category: instruction
description: Make minimal, graduated framework tweaks with experiment tracking
allowed-tools: Task
permalink: commands/learn
---

# /learn - Graduated Framework Improvement

**Run in background** - spawn asynchronously so the user can continue working:

```
Task(subagent_type="general-purpose", model="sonnet",
     description="Framework learning: [brief summary]",
     prompt="Invoke Skill(skill='framework') first, then follow the /learn workflow below to make a minimal intervention for: [USER'S FEEDBACK]\n\n[Include full /learn workflow instructions from this file]",
     run_in_background=true)
```

Report to user: "Processing framework learning in background. Continue working."

## Core Principle: Generalisable, not specific

**Don't hyperfocus**:

❌ **WRONG**: User says 'color' should be spelt 'colour' → Create 'AXIOM: HOW TO SPELL COLOR'
✅ **RIGHT**: User says 'color' should be spelt 'colour' → Consider root cause, track in issue about 'localization', consider escalation only if necessary, note that large issues likely need SPEC updates.

**Don't overreact**:
❌ **WRONG**: User mentions spelling → Create SPELLING AXIOM + spell-check hook + prominent warning
✅ **RIGHT**: User mentions spelling → Add brief note in relevant location, track in Issue, escalate only if necessary

**Start small. If we need a heavier intervention, update the Specs.**

## Workflow

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

### 2. Check for Prior Occurrences

Search GitHub Issues for related observations:

```bash
gh issue list --repo nicsuzor/academicOps --label learning --search "[keywords]"
```

**If found**: This is a recurrence. Consider escalating intervention level.

**If new**: Use `/log` first to document the observation.

### 3. Choose Intervention Level (Start at Bottom, Escalate with Evidence)

**Enforcement Ladder** (always start at lowest effective level):

| Level | Mechanism                     | When to Use                                    |
| ----- | ----------------------------- | ---------------------------------------------- |
| 1a    | Prompt text (mention)         | Nice-to-have suggestion                        |
| 1b    | Prompt text (explicit rule)   | Stated rule, no emphasis                       |
| 1c    | Prompt text (emphatic+reason) | Rule with WHY it matters for THIS task         |
| 2     | Intent router                 | Adaptive guidance based on task classification |
| 3a    | Tool restriction (soft deny)  | Tool available only via specific workflow      |
| 3b    | Skill abstraction             | Hide complexity, force workflow                |
| 4     | Pre-tool-use hooks            | Block before damage occurs                     |
| 5     | Post-tool-use validation      | Catch violations, demand correction            |
| 6     | Deny rules (settings.json)    | Hard block, no exceptions                      |
| 7     | Pre-commit hooks              | Last line of defense                           |

**Match root cause to intervention**:

| Root Cause        | Start At                                      |
| ----------------- | --------------------------------------------- |
| Clarity Failure   | Level 1c (emphatic+reasoned instruction text) |
| Context Failure   | Level 2 (intent router classification)        |
| Blocking Failure  | Level 4 (PreToolUse hook)                     |
| Detection Failure | Level 5 (PostToolUse hook)                    |
| Gap               | Lowest level that addresses the gap           |

**Escalation rule**: Only move up when you have evidence that lower levels failed. See [[docs/ENFORCEMENT.md]] for mechanism details, [[RULES]] for current enforcement state.

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions).

If you need a bigger change, **ABORT** and update/create a Spec instead.

### 5. Document in GitHub Issue

Invoke the logging infrastructure to track the intervention:

```
Skill(skill="learning-log", args="[intervention summary]")
```

Include in the summary:

- Root cause category and responsible component
- What was changed (with file path)
- What enforcement level (see [[docs/ENFORCEMENT.md]])
- What would trigger escalation

### 6. Report

Tell the user:

1. Root cause category and responsible component
2. What you changed (with file path)
3. What enforcement level
4. Link to GitHub Issue tracking this
5. What would trigger escalation
