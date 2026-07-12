---
id: constraint-check
category: verification
bases: []
---

# Constraint Check

Verify that a proposed execution plan satisfies the selected workflow's constraints.

**Note**: This is constraint-CHECKING, not constraint-SOLVING. You verify compliance, not synthesize valid sequences.

## When to Check

Check constraints when:

- Workflow has a `## Constraints` section
- Workflow has `## Triggers` or `## How to Check` sections
- Plan involves multiple steps with ordering requirements

Skip constraint checking for:

- `simple-question` workflow (no constraints)
- `direct-skill` workflow (skill handles its own constraints)
- Plans with single atomic action

## Constraint Types

| Section               | Contains                   | Verification Method              |
| --------------------- | -------------------------- | -------------------------------- |
| **Sequencing**        | `X must complete before Y` | Check execution step order       |
| **After Each Step**   | `After X: do Y`            | Check post-action steps exist    |
| **Always True**       | Invariants that must hold  | Check no steps violate           |
| **Never Do**          | Prohibited actions         | Check no steps match             |
| **Conditional Rules** | `If X then Y`              | Check conditions trigger actions |
| **Triggers**          | State transitions          | Check triggers map to steps      |
| **How to Check**      | Predicate definitions      | Use to verify completion         |

## Verification Process

1. **BEFORE rules**: Verify X appears before Y in the plan.
2. **AFTER rules**: Verify Y appears after X.
3. **ALWAYS/NEVER rules**: Verify no step violates invariants or prohibited patterns.
4. **IF-THEN/ON-INVOKE rules**: Verify action is in plan if condition triggers.

## Violation Reporting

If any constraint is violated, output:

```markdown
### Constraint Violations

[N] workflow constraint(s) violated:

1. **[Type]**: [Constraint]
   - **Violation**: [Description]
   - **Remediation**: [Fix]
```

Plan must then be revised or flagged for human review.

## Predicate Evaluation

| Predicate       | How to Verify                                  |
| --------------- | ---------------------------------------------- |
| "Tests exist"   | Plan includes "Write test" step                |
| "Tests pass"    | Plan includes "Run tests" step                 |
| "Plan approved" | Plan includes approval gate                    |
| "Task claimed"  | Plan includes task update with status="active" |

**Static predicates** (check at planning time): "test file exists"
**Runtime predicates** (check during execution): "tests pass", "validation succeeds"

For runtime predicates, verify the plan includes the CHECK step, not that the predicate is satisfied.
