---
id: design
category: planning
---

# Design Workflow

Specification and planning workflow for features and changes. Ensures clear requirements, acceptance criteria, and reviewed plans before implementation.

**Output**: Task with approved spec, acceptance criteria, and implementation plan.

## When to Use

- Adding new features that need specification
- Complex modifications requiring architectural decisions
- Work where requirements are unclear
- Before invoking implementation workflows (TDD, language-specific builds)

## When NOT to Use

- Minor edits with obvious scope → minor-edit
- Pure research/exploration → decompose
- Simple bug fixes with clear reproduction → debugging

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| "Add feature X", "implement Y" with unclear requirements | Design first |
| "How should we build this?" | Design workflow |
| Known requirements, ready to code | Skip to implementation |

## Phase 0: Spec Verification

Before planning, verify requirements exist with user stories and acceptance criteria.

- **YES**: Proceed to planning
- **NO**: Create SPEC task first (blocks implementation)

## Key Steps

1. Track work (create/claim task)
2. Articulate clear acceptance criteria
3. Create implementation plan
4. Get critic review (PROCEED / REVISE / HALT)

## Complex Features

For multi-system changes:
```
SPEC (blocker) → AUDIT (verify assumptions) → DESIGN (plan) → IMPL phases
```

Decompose when: 3+ files, uncertain requirements, multiple contributors, integration validation needed.

## Exit Criteria

- Spec exists with clear user story
- Acceptance criteria are specific and verifiable
- Implementation plan documented in task
- Critic review returned PROCEED

## Handoff

Once design complete, implementation follows appropriate workflow:
- General TDD: feature-dev
- Python: python-dev skill
- Framework: framework skill
