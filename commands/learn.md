---
name: learn
description: Make minimal, graduated framework tweaks with experiment tracking
allowed-tools: Read,Edit,Write,Glob,Grep,Skill
permalink: commands/learn
---

# /learn - Graduated Framework Improvement

The user is telling you something needs to change. Your job: **minimal intervention** that we can **track and verify**.

## MANDATORY: Invoke Framework Skill First

```
Skill(skill="framework")
```

This ensures changes are categorical (generalizable rules), not ad-hoc fixes.

## Core Principle: Don't Overreact

❌ **WRONG**: User mentions spelling → Create SPELLING AXIOM + spell-check hook + prominent warning
✅ **RIGHT**: User mentions spelling → Add brief note in relevant location, create experiment to track

**Start small. Escalate only if it recurs.**

## Workflow

### 1. Understand the Issue

What happened? Categorize:
- **Missing fact** - Agent lacked information
- **Ignored instruction** - Instruction exists but wasn't followed
- **Poor behavior** - Agent did something wrong (spelling, verbosity, etc.)
- **Missing capability** - No skill/hook handles this

### 2. Check for Prior Occurrences

Search `$ACA_DATA/projects/aops/experiments/` for related experiments:
```bash
grep -r "[keywords]" $ACA_DATA/projects/aops/experiments/
```

Search HEURISTICS.md for related heuristics.

**If found**: This is a recurrence. Consider escalating the intervention level.

### 3. Choose Intervention

The framework skill (via `@skills/framework/ENFORCEMENT.md`) defines available enforcement mechanisms. Consult it to choose the **minimal sufficient** intervention:

- **First occurrence** → Softest mechanism that addresses the issue
- **Recurrence** → Consider next-stronger mechanism
- **Persistent problem** → Escalate further

**Principle**: Start soft, escalate only with evidence.

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions). For heuristics, follow HEURISTICS.md format.

### 5. Create/Update Experiment

**Always** create or update an experiment in `$ACA_DATA/projects/aops/experiments/`:

```markdown
---
title: [Issue] Intervention Tracking
type: experiment_log
permalink: experiment-[slug]
tags: [learn, intervention, relevant-tags]
---

# [Issue] Intervention Tracking

**Date**: YYYY-MM-DD
**Hypothesis**: [Minimal intervention] will reduce [problem behavior]
**Success Criteria**: No user corrections for this issue in next 5 sessions

## Intervention History

| Date | Level | Change Made | File Modified |
|------|-------|-------------|---------------|
| YYYY-MM-DD | 1 | [brief description] | [path] |

## Observations

(Add dated observations when issue recurs or is resolved)

## Decision

- [ ] Resolved (no recurrence after N sessions)
- [ ] Escalate (recurred, increase intervention level)
- [ ] Revert (intervention caused other problems)
```

### 6. Report

Tell the user:
1. What you changed (with file path)
2. What intervention level (1-4)
3. What experiment tracks this
4. What would trigger escalation

## Example

**First mention of spelling issues**:
- Consult ENFORCEMENT.md for minimal mechanism
- Add brief note to relevant skill or CLAUDE.md
- Create experiment to track
- Report: "Added note to [location]. Will escalate if it recurs."

**Recurring issue**:
- Check existing heuristics/experiments
- Add evidence or escalate mechanism
- Update experiment with observation

## NOT for Bug Reports

If reporting a specific bug (script crashed, hook failed), use `/log` instead. `/learn` is for improving agent behavior through instruction/constraint changes.
