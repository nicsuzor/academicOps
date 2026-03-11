# Quick Verification Mode

**Default mode.** Pre-completion sanity check. "Does it run without error?"

## When to Use

- Feature complete, tests pass
- Before final commit
- User-facing changes

## Invocation

```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA]. Check functionality, quality, completeness.")
```

## Verdicts

- **VERIFIED**: Proceed to completion
- **ISSUES**: Fix critical/major issues, re-verify
