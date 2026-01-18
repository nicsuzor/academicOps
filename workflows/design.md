---
id: design
category: planning
---

# Design Workflow

## Overview

Specification and planning workflow for features and changes. Ensures clear requirements, acceptance criteria, and reviewed plans before implementation begins.

**Output**: bd issue with approved spec, acceptance criteria, and implementation plan.

## When to Use

- Adding new features that need specification
- Complex modifications requiring architectural decisions
- Work where requirements are unclear or need validation
- Before invoking implementation workflows (TDD, language-specific builds)

## When NOT to Use

- Minor edits with obvious scope → [[minor-edit]]
- Pure research/exploration → [[decompose]]
- Simple bug fixes with clear reproduction → [[debugging]]

## Phase 0: Spec Verification

Before any planning, verify requirements exist:

**Do you have a specification with user stories and acceptance criteria?**

- **YES**: Proceed to Step 1
- **NO**: Create a SPEC task first

```bash
bd create "SPEC: [Feature name]" --type=task --priority=1 \
  --description="Create specification with user stories and acceptance criteria.

DELIVERABLE:
- User story (role/goal/context)
- Acceptance criteria (specific, verifiable)
- Edge cases and error handling requirements

This task BLOCKS implementation work."
```

**Why spec-first?** Without clear requirements, you cannot verify implementation. Agents must not guess feature behavior—extract from existing patterns or ask for clarification.

## Decision Tree

```
Is the feature fully specified with acceptance criteria?
├─ NO → Create SPEC task, HALT until approved
└─ YES → Is it a complex multi-system change?
         ├─ YES → Use "Complex Features" pattern below
         └─ NO → Proceed to Step 1 (single-session design)
```

## Complex Features: Task Decomposition

For features touching multiple systems or requiring architectural decisions:

**Pattern:**
```
SPEC (blocker) ──→ AUDIT (verify assumptions) ──→ DESIGN (plan)
                                                      │
                                                      └──→ IMPL phases (see [[feature-dev]])
```

**Guidelines:**
- SPEC tasks are P1 blockers—nothing starts until requirements are clear
- AUDIT tasks verify existing state matches assumptions before designing
- DESIGN produces the plan that implementation follows
- Use `bd dep add <dependent> <blocker>` to enforce ordering

**When to decompose:**
- Feature affects 3+ files or systems
- Requirements are uncertain or evolving
- Multiple agents or sessions will contribute
- Integration points need separate validation

## Steps

### 1. Track work in bd

Follow [[bd-workflow]] to set up issue tracking:

```bash
bd ready                           # Check for existing issues
bd create "[Feature]" --type=task  # Or claim existing
bd update <id> --status=in_progress
```

### 2. Articulate clear acceptance criteria

Define specific, verifiable conditions for success:

- What functionality must work?
- What edge cases must be handled?
- What quality gates must pass?

Document in the bd issue description.

### 3. Create implementation plan

Design the approach:

- What files need to change?
- What new components are needed?
- What dependencies exist?
- What testing strategy will be used?

Save the plan to the bd issue.

### 4. Get critic review ([[spec-review]])

Invoke critic agent to review:

```javascript
Task(subagent_type="critic", model="opus", prompt=`
Review this implementation plan for errors, hidden assumptions, and missing verification:

**Feature**: [description]

**Acceptance Criteria**:
1. [criterion]
2. [criterion]

**Plan**:
[implementation plan]

Return: PROCEED | REVISE (list changes) | HALT (explain)
`)
```

**If PROCEED**: Design complete, ready for implementation
**If REVISE**: Update plan, re-review
**If HALT**: Address fundamental issues before proceeding

## Exit Criteria

Design is complete when:

- [ ] Spec exists with clear user story
- [ ] Acceptance criteria are specific and verifiable
- [ ] Implementation plan documented in bd issue
- [ ] Critic review returned PROCEED (or REVISE items addressed)

## Handoff to Implementation

Once design is complete, implementation follows language/project-specific workflows:

- **General TDD**: [[feature-dev]] (Steps 5-8)
- **Python**: python-dev skill
- **Framework work**: framework skill

The bd issue ID carries forward—implementation references the same issue.

## Integration with Other Workflows

- **decompose**: For uncertain scope, use decompose first to identify what needs designing
- **spec-review**: Used in Step 4 for critic feedback loop
- **feature-dev**: Consumes design output for TDD implementation
- **bd-workflow**: Tracks work throughout design and implementation
