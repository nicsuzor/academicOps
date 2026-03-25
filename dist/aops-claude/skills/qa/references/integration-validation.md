# Integration Validation Mode

Framework integration testing. "Does it connect properly?"

## When to Use

- Validating new framework capabilities
- Verifying structural changes (relationships, computed fields)
- After framework modifications

## Unique Steps

1. **Baseline**: Capture state before running feature
2. **Execute**: Run feature as user would
3. **Verify**: Check structural changes
4. **Report**: Evidence table (expected vs actual)

## Evidence Format

| Field | Expected | Actual  | Correct? |
| ----- | -------- | ------- | -------- |
| [key] | [value]  | [value] | Yes/No   |

## Invocation

```
Task(subagent_type="qa",
     prompt="Validate framework integration: [FEATURE]. Capture baseline, execute, verify structural changes, report evidence.")
```
