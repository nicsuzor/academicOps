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

**Start small. If we need a heavier intervention, we need to update the Specs.**

## Workflow

### 1. Understand the Issue

What happened? Categorize:
- **Missing fact** - Agent lacked information
- **Ignored instruction** - Instruction exists but wasn't followed
- **Poor behavior** - Agent did something wrong (spelling, verbosity, etc.)
- **Missing capability** - No skill/hook handles this
- **Guardrail failure** - Known failure pattern not prevented (see [[hooks/guardrails.md]])

### 2. Check for Prior Occurrences

Search `$AOPS/experiments/` for related experiments:
```bash
grep -r "[keywords]" $AOPS/experiments/
```

Search HEURISTICS.md for related heuristics.

**If found**: This is a recurrence. Consider escalating the intervention level.

**If this is a new issue**: Invoke the `/log` command to track it.

### 3. Choose Intervention

The framework skill (via `@RULES.md`) defines available enforcement mechanisms. Consult it to choose the **minimal sufficient** intervention:

- **First occurrence** → Softest mechanism that addresses the issue
- **Recurrence** → Consider next-stronger mechanism
- **Persistent problem** → Escalate further

**Principle**: Start soft, escalate only with evidence.

#### Guardrail-Specific Interventions

For guardrail failures, consult [[hooks/guardrails.md]] and choose:

| Issue | Intervention | File to Edit |
|-------|--------------|--------------|
| Guardrail not applied to task type | Add to Task Type → Guardrail Mapping | `hooks/guardrails.md` |
| Guardrail instruction unclear | Strengthen the Instruction text | `hooks/guardrails.md` |
| New failure pattern needs guardrail | Add to Guardrail Registry | `hooks/guardrails.md` |
| Guardrail triggers incorrectly | Adjust "When to apply" conditions | `hooks/guardrails.md` |
| Need new heuristic first | Create heuristic via `/log` | `HEURISTICS.md` |

**Guardrail escalation path:**
1. Adjust instruction text (clearer wording)
2. Add to more task types (broader application)
3. Propose PreToolUse enforcement (hook blocks until condition met)
4. Propose PostToolUse verification (hook checks after action)

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions).

If you need to make a bigger change, **ABORT** and update/create a Spec instead.

### 5. Create/Update Experiment

**Always** create or update an experiment in `$AOPS/experiments/`:

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
- Consult RULES.md for minimal mechanism
- Add brief note to relevant skill or CLAUDE.md
- Create experiment to track
- Report: "Added note to [location]. Will escalate if it recurs."

**Recurring issue**:
- Check existing heuristics/experiments
- Add evidence or escalate mechanism
- Update experiment with observation
