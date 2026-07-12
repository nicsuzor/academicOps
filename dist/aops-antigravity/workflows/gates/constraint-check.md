---
id: constraint-check
kind: gate
category: verification
description: Verify a proposed execution plan satisfies the constraints of the process/gate templates it composes — checking, not solving
door-type: two-way
stakes: A decompose/brief pass composes a regime on paper but the resulting plan silently violates one of the composed templates' own rules (missing a mandatory step, wrong ordering, a prohibited action).
skip-when: The routed template declares no constraints (e.g. simple-question), or the plan is a single atomic action.
pairs-with: [verification]
version: 1.0.0
permalink: workflows-gates-constraint-check
---

# Gate: Constraint Check

**This is constraint-CHECKING, not constraint-SOLVING.** You verify a plan
complies with the templates it claims to compose; you do not synthesize a
valid plan for it. Used at the Decompose/Brief stages of the pipeline — after
templates are selected, before the plan is dispatched.

## When to Check

Check when the composed template(s) declare a `## Constraints`,
`## Critical Rules`, or ordering requirement. Skip for `simple-question`-shaped
work or single-step plans.

## Constraint Types

| Kind            | Contains                   | How to verify                         |
| --------------- | -------------------------- | ------------------------------------- |
| Sequencing      | "X must complete before Y" | Step order in the plan                |
| After-each-step | "After X: do Y"            | Post-action step present              |
| Always-true     | Invariants                 | No step violates them                 |
| Never-do        | Prohibited actions         | No step matches                       |
| Conditional     | "If X then Y"              | Condition triggers the action in-plan |

## Process

1. Verify BEFORE-rules: X appears before Y.
2. Verify AFTER-rules: Y appears after X.
3. Verify ALWAYS/NEVER-rules: no step violates.
4. Verify IF-THEN-rules: the triggered action is present.

For runtime predicates ("tests pass", "criteria met"), verify the plan
_includes the check step_ — not that the predicate already holds; that's
[[verification]]'s job once the plan executes.

## Violation Reporting

```markdown
### Constraint Violations

N violated:

1. **[Type]**: [constraint] — **Violation**: [what's missing/wrong] —
   **Remediation**: [fix]
```

A violated plan is revised or escalated to human review — it does not proceed
to dispatch as-is.

## Declared stakes

Cheap and two-way — re-running this check costs nothing. Its value is entirely
upstream: it stops a downstream one-way-door gate (e.g. [[human-approval]])
from being reached by a plan that was never going to satisfy it.
