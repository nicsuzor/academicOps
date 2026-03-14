---
id: base-tdd
category: base
---

# Base: Test-Driven Development

Red-green-refactor cycle for any testable code change.

**Composable base pattern.** Used by development workflows.

## Pattern

1. **Red**: Write failing test for ONE behavior
2. **Verify failure**: Confirm test fails (proves test works)
3. **Green**: Minimal implementation to pass
4. **Verify pass**: Confirm test passes
5. **Refactor**: Optional cleanup (keep tests green)
6. **Repeat**: If more acceptance criteria remain

## Constraints

### Red Phase (Test First)

- A test must exist before implementation begins
- The test must fail before implementation (this proves the test is meaningful)
- Each test should target ONE behavior, not multiple
- **Valid red = `AssertionError` on behavior.** `TypeError` (wrong API shape) is a
  test bug — add a minimal stub first so the test reaches the assertion.
- **Every test result must be explained.** If a test passes before implementation:
  backward-compat behavior → label `[GREEN]` (regression guard, valid). Unclear →
  the test is wrong; fix or remove it. Never call it "accidental" and move on.

### Green Phase (Minimal Implementation)

- After implementation, always run the test
- Implementation should be minimal—just enough to pass

### Refactor Phase

- Tests must still pass after refactoring
- Can only refactor when tests are green

### Commit Gates

- Cannot commit while tests fail or without implementation (incomplete cycle)

### Always True

- One behavior per cycle; test before code.

### Never Do

- Never implement before writing a test; never commit with a failing test.

## Triggers

Cycle state transitions:

- Written → verify failure; Failure (expected) → implement; Pass → refactor or commit.
- Refactor complete → verify pass; Criteria remain → start new cycle.
- Unexpected pass → HALT; Fail after refactor → undo refactor.

## State Machine

The TDD cycle follows this flow:

```
[RED] Write failing test
   ↓
Verify failure → (passes unexpectedly) → HALT
   ↓ (fails as expected)
[GREEN] Minimal implementation
   ↓
Verify pass → (still fails) → continue implementing
   ↓ (passes)
[REFACTOR] Optional cleanup
   ↓
Verify still pass → (fails) → undo refactor
   ↓ (passes)
[COMMIT or REPEAT]
   ├── (criteria remain) → back to RED
   └── (complete) → DONE
```

## How to Check

- Test exists: file contains "def test_" or "test(" for target behavior
- Test fails: pytest/test runner exit code is not 0 for the specific test
- Test passes: pytest/test runner exit code is 0 for the specific test
- Tests pass (all): pytest/test runner exit code is 0 for all tests in scope
- Tests still pass: all tests pass and no new failures were introduced
- Test targets one behavior: test function has a single assertion focus (heuristic)
- Implementation minimal: implementation addresses only what the test requires (requires judgment)
- Acceptance criteria remain: uncompleted acceptance criteria items exist
- Acceptance complete: all acceptance criteria are satisfied
- Refactor complete: cleanup changes committed or explicitly skipped
