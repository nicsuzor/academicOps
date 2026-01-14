---
id: tdd-cycle
category: development
---

# Test-Driven Development Cycle

## Overview

The classic TDD red-green-refactor cycle. Write failing tests first, implement minimal code to pass, then refactor. Repeat until all acceptance criteria are met.

## When to Use

- Implementing new features
- Fixing bugs (write test that reproduces bug first)
- Any code change where correctness can be tested
- Refactoring existing code

## Steps

### 1. Red - Write failing test

Write a test for the next piece of functionality:

```python
def test_feature_does_something():
    """Test that feature does X when Y happens."""
    # Arrange
    setup = create_test_fixture()

    # Act
    result = feature.do_something(setup)

    # Assert
    assert result == expected_value
```

The test should:
- Test ONE thing (single responsibility)
- Have a clear name describing what it tests
- Follow Arrange-Act-Assert pattern
- Be independent of other tests

### 2. Verify test fails

Run the test suite to confirm it fails:

```bash
uv run pytest -v test_feature.py::test_feature_does_something
```

**Expected output:**
```
FAILED test_feature.py::test_feature_does_something
```

**Why this matters:**
- Confirms the test is actually testing something
- Prevents false positives from tests that always pass
- Validates test setup is correct

### 3. Green - Minimal implementation

Write just enough code to make the test pass:

```python
def do_something(setup):
    """Implement just enough to pass the test."""
    # Minimal implementation
    return expected_value
```

**Resist the urge to:**
- Implement more than needed for this test
- Add features not covered by tests
- Optimize prematurely

**Focus on:**
- Making this specific test pass
- Simplest possible solution
- Getting to green quickly

### 4. Verify test passes

Run the test suite again:

```bash
uv run pytest -v test_feature.py::test_feature_does_something
```

**Expected output:**
```
PASSED test_feature.py::test_feature_does_something
```

If the test still fails:
- Debug the implementation
- Check test assumptions
- Verify test setup is correct

### 5. Refactor - Clean up code (optional)

Now that tests are passing, improve code quality:

**Code improvements:**
- Extract duplicated logic
- Improve naming
- Simplify complex expressions
- Remove dead code

**Refactoring rules:**
- Keep tests passing (run after each change)
- Don't change behavior
- Don't add new features
- Commit before risky refactoring

**Skip refactoring if:**
- Code is already clean
- No obvious improvements
- Time constraints

### 6. Commit changes

Commit the red-green-refactor cycle:

```bash
git add test_feature.py feature.py
git commit -m "feat: add feature.do_something() - TDD cycle

Red: Test for X functionality
Green: Minimal implementation
Refactor: [describe refactoring or 'none']

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### 7. Check if more tests needed

Determine next steps:

**Implementation complete if:**
- All acceptance criteria have tests
- All edge cases covered
- All tests passing
- Code coverage acceptable

**Need another cycle if:**
- More acceptance criteria remain
- Edge cases not tested
- Additional functionality needed
- Integration tests needed

If more tests are needed, return to step 1 with the next test case.

## TDD Best Practices

### Test First, Always

- Never write production code without a failing test first
- Tests drive the design of the code
- Tests document the intended behavior

### Minimal Steps

- Take the smallest possible step from red to green
- Resist implementing more than the test requires
- Let tests guide you incrementally

### Keep Tests Fast

- Fast tests enable rapid iteration
- Mock external dependencies
- Use in-memory databases for testing
- Avoid network calls in tests

### One Assert Per Test (Generally)

- Tests should verify one thing
- Makes failures easier to diagnose
- Exceptions for related assertions (e.g., multiple fields of same object)

### Test Behavior, Not Implementation

- Test what the code does, not how it does it
- Tests should survive refactoring
- Focus on inputs and outputs

## TDD Anti-Patterns to Avoid

### Writing Tests After Implementation

- Defeats the purpose of TDD
- Tests may be biased toward existing code
- Missing the design feedback from test-first

### Testing Implementation Details

- Tests become brittle
- Refactoring breaks tests unnecessarily
- Test the public interface, not internals

### Large Tests

- Slow test suites discourage running tests
- Failures are hard to diagnose
- Tests become hard to maintain

### Test Dependencies

- Tests that depend on each other
- Tests that require specific execution order
- Shared mutable state between tests

## Success Metrics

- [ ] All tests pass (100% pass rate)
- [ ] Each test tests one thing
- [ ] Test names clearly describe what they test
- [ ] Tests are fast (< 1s for unit tests)
- [ ] Code coverage meets project standards
- [ ] No production code without tests
