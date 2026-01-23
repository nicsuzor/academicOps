---
id: design
category: planning
bases: [base-task-tracking]
---

# Design

Specification and planning for known work.

## Routing Signals

- "Add feature X" with unclear requirements
- Complex modifications needing architecture decisions
- "How should we build this?"

## NOT This Workflow

- Obvious scope → [[minor-edit]]
- Uncertain path → [[decompose]] first
- Simple bug → [[debugging]]

## Unique Steps
<!-- NS: spec requirement is for framework only. maybe merge this entire file into framework-change.md? -->
1. Verify spec exists (user stories, acceptance criteria)
   - If no spec → create SPEC task first (blocks implementation)
2. Articulate clear acceptance criteria
3. Create implementation plan
4. Get critic review (PROCEED / REVISE / HALT)

## Exit Routing

Once design approved:
- General code → [[base-tdd]]
- Python → python-dev skill
- Framework → framework skill
