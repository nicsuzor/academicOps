---
title: Observation Quality Guide
type: reference
permalink: observation-quality-guide
tags:
  - bmem
  - reference
  - quality-standards
---

# Observation Quality Guide

## Tag Placement Rules

**CRITICAL: All tags belong in YAML frontmatter, NEVER inline in observations.**

✅ **CORRECT**:
```markdown
---
tags:
  - energy-management
  - productivity
  - planning
---

## Observations

- [principle] Match task difficulty to available energy levels for optimal productivity
- [pattern] Late day/low energy optimal for reviews and evaluations
```

❌ **WRONG**:
```markdown
## Observations

- [principle] Match task difficulty to available energy levels #energy-management #productivity
- [pattern] Late day/low energy optimal for reviews and evaluations #task-scheduling
```

**Why**: Inline hashtags pollute prose, making observations hard to copy/export. Tags are metadata and belong in the metadata section (frontmatter).

**Keep**: Category brackets `[principle]`, `[pattern]`, etc. - these are semantic structure, not tags.

## What Observations ARE

**Observations ADD new information beyond document body and frontmatter.**

✅ **GOOD observations**:

- Specific, concrete facts
- Atomic (one fact per observation)
- Additive (new information not in frontmatter/body)
- Contextual (enough detail to understand)
- Semantic (enable knowledge graph queries)

❌ **BAD observations**:

- Repeat document body verbatim
- Duplicate frontmatter metadata (due dates, status, type)
- State the obvious ("This is a task")
- Add no new information

## Examples

### ❌ BAD (duplicates frontmatter AND uses inline tags)

```markdown
---
due: 2025-11-07
type: task
status: inbox
---

## Context

Review student thesis by Nov 7.

## Observations

- [task] Review student thesis by Nov 7 #inbox
- [requirement] Due date: 2025-11-07 #deadline
- [fact] Type: task #type-task
```

**Problems**:
1. Inline hashtags (#inbox, #deadline, #type-task) pollute prose - should be in frontmatter
2. Observations duplicate information already in frontmatter (due date, type, status)
3. Observations add no new information beyond what's already stated

### ✅ GOOD (adds new information)

```markdown
---
due: 2025-11-07
type: task
status: inbox
tags:
  - student-rhyle-simcock
  - compliance
  - phd-process
  - review-strategy
---

## Context

Review Rhyle Simcock's PhD thesis lodgement. Do NOT name examiners in comments.

## Observations

- [fact] Rhyle Simcock is PhD candidate in platform governance
- [requirement] Cannot name examiners in comments as student will see them
- [insight] This is thesis examination stage requiring supervisor approval
- [decision] Will focus review on methodology and structure
```
