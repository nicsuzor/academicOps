---
id: qa-demo
category: quality-assurance
bases: []
---

# QA Verification

Independent verification before completion. "Does it run without error?"

## Routing Signals

- Feature complete, tests pass, before final commit
- User-facing functionality changes
- Complex changes with multiple acceptance criteria

## NOT This Workflow

- Trivial changes (typo fixes)
- Already reviewed by user
- Integration validation → [[prove-feature]]

## Invocation

```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA]. Check functionality, quality, completeness.")
```

## Verdicts

- **VERIFIED**: Proceed to completion
- **ISSUES**: Fix critical/major issues, re-verify
