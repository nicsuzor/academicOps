---
id: tdd-cycle
category: development
bases: [base-task-tracking, base-tdd, base-verification, base-commit]

# Workflow-specific gate constraints
# These extend the base gates defined in lib/gates/definitions.py
constraints:
  # Red Phase (Test First)
  red_phase:
    - id: test-before-implement
      before: implement
      requires: test_exists
      message: "A test must exist before implementation begins"

    - id: test-must-fail-first
      before: implement
      requires: test_fails
      message: "The test must fail before implementation (proves test is meaningful)"

    - id: single-behavior-per-test
      check: test_targets_one_behavior
      verdict: warn
      message: "Each test should target ONE behavior, not multiple"

  # Green Phase (Minimal Implementation)
  green_phase:
    - id: run-test-after-implement
      after: implement
      action: run_tests
      message: "After implementation, always run the test"

    - id: minimal-implementation
      check: implementation_is_minimal
      verdict: warn
      message: "Implementation should be minimal—just enough to pass"

  # Refactor Phase
  refactor_phase:
    - id: tests-pass-after-refactor
      after: refactor
      requires: all_tests_pass
      message: "Tests must still pass after refactoring"

    - id: only-refactor-when-green
      before: refactor
      requires: tests_green
      message: "Can only refactor when tests are green"

  # Commit Gates
  commit_gates:
    - id: no-commit-failing-tests
      before: commit
      requires: all_tests_pass
      verdict: deny
      message: "Cannot commit while tests fail"

    - id: no-incomplete-cycle-commit
      before: commit
      requires: cycle_complete
      verdict: deny
      message: "Cannot commit a failing test without implementation (incomplete cycle)"

  # Cycle Iteration
  cycle_iteration:
    - id: repeat-if-criteria-remain
      when: acceptance_criteria_remain
      action: start_new_cycle
      message: "If acceptance criteria remain, repeat the cycle"

  # Invariants - always true during this workflow
  invariants:
    - id: one-behavior-per-cycle
      check: one_behavior_per_cycle
      message: "One behavior per cycle"

    - id: test-before-code
      check: test_written_before_code
      message: "Test before code"

  # Prohibitions - never do these
  never:
    - id: no-implement-before-test
      action: implement
      when: test_not_written
      verdict: deny
      message: "Never implement before writing a test"

    - id: no-commit-failing
      action: commit
      when: tests_failing
      verdict: deny
      message: "Never commit with a failing test"

    - id: no-skip-failure-verify
      action: proceed_to_green
      when: failure_not_verified
      verdict: deny
      message: "Never skip verifying that the test fails first"

    - id: no-over-implement
      action: implement
      when: implementation_exceeds_test
      verdict: warn
      message: "Never implement beyond the minimal needed to pass"

# State machine for TDD cycle
state_machine:
  states: [red, green, refactor, commit_or_repeat, done]
  initial: red
  transitions:
    - from: red
      event: test_written
      to: verify_failure

    - from: verify_failure
      event: test_fails_as_expected
      to: green

    - from: verify_failure
      event: test_passes_unexpectedly
      to: halt
      message: "HALT: test may not be testing what you think"

    - from: green
      event: test_passes
      to: refactor

    - from: green
      event: test_still_fails
      to: green
      action: continue_implementing

    - from: refactor
      event: tests_pass
      to: commit_or_repeat

    - from: refactor
      event: tests_fail
      to: refactor
      action: undo_refactor

    - from: commit_or_repeat
      event: criteria_remain
      to: red

    - from: commit_or_repeat
      event: acceptance_complete
      to: done

# Predicate definitions for constraint checks
predicates:
  test_exists:
    check: "file contains 'def test_' or 'test(' for target behavior"

  test_fails:
    check: "pytest/test runner exit code is not 0 for the specific test"

  test_passes:
    check: "pytest/test runner exit code is 0 for the specific test"

  all_tests_pass:
    check: "pytest/test runner exit code is 0 for all tests in scope"

  tests_green:
    check: "all tests pass and no new failures introduced"

  test_targets_one_behavior:
    check: "test function has a single assertion focus (heuristic)"

  implementation_is_minimal:
    check: "implementation addresses only what the test requires (requires judgment)"

  cycle_complete:
    check: "test exists AND implementation exists AND tests pass"

  acceptance_criteria_remain:
    check: "uncompleted acceptance criteria items exist"

  acceptance_complete:
    check: "all acceptance criteria are satisfied"

  one_behavior_per_cycle:
    check: "current cycle addresses exactly one behavior"

  test_written_before_code:
    check: "test file modified before implementation file in current cycle"
---

# TDD Cycle Workflow

Red-green-refactor cycle for any testable code change.

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
- Acceptance criteria remain: uncompleted acceptance criteria items exist
- Acceptance complete: all acceptance criteria are satisfied
- Refactor complete: cleanup changes committed or explicitly skipped
