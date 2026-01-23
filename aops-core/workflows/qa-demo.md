# QA Demo Workflow

Independent verification before completion. "Does it run without error?"

## When to Use

Use this workflow when:
- Feature is complete and tests pass, before final commit
- User-facing functionality has changed
- Complex changes have multiple acceptance criteria

Do NOT use for:
- Trivial changes (typo fixes)
- Work already reviewed by the user
- Integration validation (use prove-feature)

## Constraints

### Preconditions

- Feature must be complete before QA verification
- Tests must pass before QA verification

### QA Gate

- QA must verify the work before completion

### Verdict Handling

- If QA returns VERIFIED → proceed to completion
- If QA finds issues → fix the issues and re-verify

### Never Do

- Never complete without QA verification
- Never ignore QA issues

## Invocation

Invoke the QA agent with:
```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA]. Check functionality, quality, completeness.")
```

## Triggers

- When feature is ready → invoke QA agent
- When QA returns VERIFIED → proceed to complete
- When QA finds issues → fix issues

## How to Check

- Feature complete: all implementation tasks are marked done
- Tests pass: pytest exit code is 0
- QA verified: QA agent returned "VERIFIED"
- QA issues found: QA agent returned "ISSUES" with critical or major items
