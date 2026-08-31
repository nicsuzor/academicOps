---
alias:
- wf-constraint-check-wf-constraint-check
- wf-constraint-check
created: 2026-07-20T07:23:18.877334132+00:00
id: wf-constraint-check
last_modified: 2026-07-28T03:01:21.918067800+00:00
modified: 2026-07-28T03:01:21.918065987+00:00
permalink: wf-constraint-check
tags:
- wf-template
- v0.4
- module-f
title: wf-constraint-check
type: template
---

## What this step does

Verify a proposed execution plan complies with the templates it claims to compose; you do not synthesize a valid plan for it. Used at the Decompose/Brief stages of the pipeline — after templates are selected, before the plan is dispatched.

## When to check

Check when the composed template(s) declare a `## Constraints`, `## Critical Rules`, or ordering requirement. Skip for `simple-question`-shaped work or single-step plans.

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

For runtime predicates ("tests pass", "criteria met"), verify the plan _includes the check step_ — not that the predicate already holds; that's verification's job once the plan executes.

## Violation Reporting

```markdown
### Constraint Violations

N violated:

1. **[Type]**: [constraint] — **Violation**: [what's missing/wrong] — **Remediation**: [fix]
```

A violated plan is revised or escalated to human review — it does not proceed to dispatch as-is.

## Declared stakes

Cheap and two-way — re-running this check costs nothing. Its value is entirely upstream: it stops a downstream one-way-door gate (e.g. [[wf-human-approval]]) from being reached by a plan that was never going to satisfy it.
