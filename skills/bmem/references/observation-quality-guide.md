# Observation Quality Guide

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

### ❌ BAD (duplicates frontmatter)

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

### ✅ GOOD (adds new information)

```markdown
---
due: 2025-11-07
type: task
status: inbox
---

## Context

Review Rhyle Simcock's PhD thesis lodgement. Do NOT name examiners in comments.

## Observations

- [fact] Rhyle Simcock is PhD candidate in platform governance #student-rhyle-simcock
- [requirement] Cannot name examiners in comments as student will see them #compliance
- [insight] This is thesis examination stage requiring supervisor approval #phd-process
- [decision] Will focus review on methodology and structure #review-strategy
```
