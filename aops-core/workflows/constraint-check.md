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

For each constraint type in the selected workflow:

**1. BEFORE rules** - "X must complete before Y"

- Verify X appears before Y in the plan
- If X is missing entirely, flag as violation

**2. AFTER rules** - "After X: do Y"

- Find step X in the plan
- Verify Y appears after X

**3. ALWAYS rules** - Invariants

- Verify no step would violate the invariant

**4. NEVER rules** - Prohibitions

- Check no step matches the prohibited pattern

**5. IF-THEN rules** - Conditionals

- If condition applies to this task, verify action is in plan
- If can't evaluate statically, note as "runtime check needed"

**6. ON-INVOKE rules** - Triggers

- Identify if trigger condition will occur
- Verify corresponding action is invoked

## Violation Reporting

If any constraint is violated, output:

```markdown
### Constraint Violations

[N] workflow constraint(s) violated:

1. **[Constraint type]**: [Quoted constraint from workflow]
   - **Violation**: [What's wrong with the current plan]
   - **Remediation**: [How to fix]
```

After listing violations:

- **Revise the plan** to satisfy all constraints (preferred)
- **Flag for human review** if constraints conflict or are ambiguous

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
