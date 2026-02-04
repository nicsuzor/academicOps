---
id: base-tdd
category: base
---

# Base: Test-Driven Development

**Composable base pattern.** Used by development workflows.

## Pattern

1. **Red**: Write failing test for ONE behavior
2. **Verify failure**: Confirm test fails (proves test works)
3. **Green**: Minimal implementation to pass
4. **Verify pass**: Confirm test passes
5. **Refactor**: Optional cleanup (keep tests green)
6. **Repeat**: If more acceptance criteria remain

## When to Skip

- Non-code changes (docs, config)
- Exploratory work where tests aren't yet meaningful
