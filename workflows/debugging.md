---
id: debugging
category: development
bases: [base-task-tracking, base-verification]
---

# Debugging

Understand the problem before fixing it.

## Routing Signals

- "Why doesn't this work?"
- Investigating unexpected behavior
- Bug where cause is unknown

## NOT This Workflow

- Cause already known → [[minor-edit]] or [[design]]

## Unique Steps

1. Define success criteria (what "fixed" means)
2. Create reproducing test (fails now, passes after fix)
3. Investigate root cause
4. Document findings in task

## Exit Routing

After debugging:
- Simple fix → [[minor-edit]]
- Complex fix → [[design]]
- Unsure → ask user
