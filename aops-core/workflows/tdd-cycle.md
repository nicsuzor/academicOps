# TDD Cycle Workflow

Red-green-refactor cycle for any testable code change.

## When to Use

Use this workflow when:
- Implementing new features
- Fixing bugs (reproduce with test first)
- Refactoring existing code

Do NOT use for:
- Non-code changes (docs, config)
- Exploratory work where tests aren't yet meaningful
- Test infrastructure itself

## Constraints

### Red Phase (Test First)

- A test must exist before implementation begins
- The test must fail before implementation (this proves the test is meaningful)
- Each test should target ONE behavior, not multiple

### Green Phase (Minimal Implementation)

- After implementation, always run the test
- Implementation should be minimal—just enough to pass

### Refactor Phase

- Tests must still pass after refactoring
- Can only refactor when tests are green

### Commit Gates

- Cannot commit while tests fail
- Cannot commit a failing test without implementation (that's an incomplete cycle)

### Cycle Iteration

- If acceptance criteria remain, repeat the cycle

### Always True

- One behavior per cycle
- Test before code

### Never Do

- Never implement before writing a test
- Never commit with a failing test
- Never skip verifying that the test fails first
- Never implement beyond the minimal needed to pass

## Triggers

Cycle state transitions:
- When test is written → verify it fails
- When test fails (as expected) → proceed to implement
- When test passes → proceed to refactor or commit
- When refactor is complete → verify tests still pass
- When tests pass and acceptance criteria remain → start new cycle
- When tests pass and acceptance is complete → proceed to commit

Error handling:
- If test passes unexpectedly → HALT with message "test may not be testing what you think"
- If tests fail after refactor → undo the refactor

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
- Acceptance criteria remain: TodoWrite has uncompleted acceptance criteria items
- Acceptance complete: all acceptance criteria are marked completed
- Refactor complete: cleanup changes committed or explicitly skipped
