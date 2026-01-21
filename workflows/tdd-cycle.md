---
id: tdd-cycle
category: development
---

# Test-Driven Development Cycle

Red-green-refactor cycle: write failing tests first, implement minimal code to pass, then refactor.

## When to Use

- Implementing new features
- Fixing bugs (reproduce bug with test first)
- Any testable code change
- Refactoring existing code

## When NOT to Use

- Non-code changes (documentation, config)
- Exploratory work where tests aren't yet meaningful
- Changes to test infrastructure itself

## Core Cycle

1. **Red**: Write failing test for ONE thing
2. **Verify failure**: Confirm test fails (proves test works)
3. **Green**: Minimal implementation to pass
4. **Verify pass**: Confirm test passes
5. **Refactor**: Clean up (optional, keep tests green)
6. **Commit**: Red-green-refactor cycle complete
7. **Repeat**: If more acceptance criteria remain

## Quality Gates

- All tests pass
- Each test tests one thing
- Test names describe what they test
- No production code without tests
- Tests are fast (< 1s for unit tests)

## Anti-Patterns

- Writing tests after implementation
- Testing implementation details (test behavior, not internals)
- Large tests (slow, hard to diagnose)
- Test dependencies (shared mutable state)
