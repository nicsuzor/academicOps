---
name: learn
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

### 1. Understand the Issue

What happened? Categorize:
- **Missing fact** - Agent lacked information
- **Ignored instruction** - Instruction exists but wasn't followed
- **Poor behavior** - Agent did something wrong
- **Missing capability** - No skill/hook handles this
- **Guardrail failure** - Known failure pattern not prevented

### 2. Check for Prior Occurrences

Search GitHub Issues for related observations:
```bash
gh issue list --repo nicsuzor/academicOps --label learning --search "[keywords]"
```

**If found**: This is a recurrence. Consider escalating intervention level.

**If new**: Use `/log` first to document the observation.

### 3. Choose Intervention

Consult [[RULES]] for available enforcement mechanisms. Choose **minimal sufficient** intervention:

- **First occurrence** → Softest mechanism
- **Recurrence** → Consider next-stronger mechanism
- **Persistent problem** → Escalate further

**Principle**: Start soft, escalate only with evidence.

### 4. Make the Minimal Change

Keep changes brief (1-3 sentences for soft interventions).

If you need a bigger change, **ABORT** and update/create a Spec instead.

### 5. Document in GitHub Issue

Track the intervention in the relevant Issue:
- What was changed (with file path)
- What intervention level (1-4)
- What would trigger escalation

Per [[specs/reflexivity]], interventions are tracked as Issue comments, not separate experiment files.

### 6. Report

Tell the user:
1. What you changed (with file path)
2. What intervention level
3. Link to GitHub Issue tracking this
4. What would trigger escalation
