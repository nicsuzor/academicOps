---
id: prove-feature
category: quality-assurance
---

# Prove Feature Workflow

Validate framework features integrate correctly by establishing baseline, executing operation, and verifying structural changes.

**Key distinction**: qa-demo checks "does it run without error?" This workflow checks "does it integrate correctly?"

## When to Use

- Validating new framework capabilities
- Testing operations produce expected data structures
- Verifying components connect properly (not orphaned)
- Features where "correct" means "properly integrated"

## When NOT to Use

- General functionality testing (use qa-demo)
- Unit testing (use tdd-cycle)
- Bug investigation (use debugging)

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| "Does it integrate correctly?" | Prove feature |
| "Does it run without error?" | QA demo |
| Structural verification needed | Prove feature |

## Key Steps

1. **Baseline**: Capture existing state before running feature
2. **Execute**: Run feature as user would
3. **Verify**: Check structural changes (relationships, computed fields)
4. **Report**: Present evidence table (expected vs actual)

## Evidence Format

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key] | [value] | [value] | ✅/❌ |

## Quality Gates

- Baseline captured before execution
- Feature executed normally (no test modifications)
- Structural integration verified
- Evidence table produced
