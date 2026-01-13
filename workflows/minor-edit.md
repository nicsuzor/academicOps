---
id: minor-edit
title: Minor Edit Workflow
type: workflow
category: development
dependencies: []
steps:
  - id: claim-issue
    name: Fetch or create bd issue, mark as in-progress
    workflow: null
    description: Track the work item
  - id: write-test
    name: Invoke ttd to create a failing test
    workflow: null
    description: Test-first approach for the change
  - id: implement
    name: Invoke python-dev to make the change
    workflow: null
    description: Implement the minimal change
  - id: checkpoint
    name: CHECKPOINT - Verify change works
    workflow: null
    description: Run tests to confirm fix
  - id: commit-push
    name: Commit and push
    workflow: null
    description: Land the change
---

# Minor Edit Workflow

## Overview

Streamlined workflow for small, targeted changes. Includes test-first development but skips heavyweight processes like critic review and QA verification.

## When to Use

- Typo fixes
- Small bug fixes
- Minor refactoring
- Documentation updates
- Configuration changes
- Simple one-file changes

## When NOT to Use

Use feature-dev workflow instead if:
- Change affects multiple files
- Architectural decisions required
- Complex logic changes
- New features (not bug fixes)
- User-facing behavior changes

## Steps

### 1. Fetch or create bd issue, mark as in-progress

Track the work:

```bash
bd ready                    # Find available work
bd update <id> --status=in_progress
```

Or create a new issue:

```bash
bd create --title="Fix: [brief description]" --type=bug --priority=3
```

### 2. Invoke ttd to create a failing test

Write a test that demonstrates the bug or validates the change:

```python
def test_fix_for_issue():
    """Test that [issue] is fixed."""
    # Arrange
    setup = create_test_case()

    # Act
    result = function_being_fixed(setup)

    # Assert
    assert result == expected_behavior
```

Run to confirm it fails:

```bash
uv run pytest -v test_file.py::test_fix_for_issue
```

### 3. Invoke python-dev to make the change

Make the minimal change needed:

```python
def function_being_fixed(input):
    """Fix implementation."""
    # Make the change
    return corrected_behavior
```

Keep changes focused:
- Fix only what's needed
- Don't refactor surrounding code
- Don't add extra features

### 4. CHECKPOINT: Verify change works

Run tests to confirm:

```bash
uv run pytest -v              # All tests should pass
./scripts/format.sh           # Format code
uv run ruff check .           # Check linting
```

If tests fail:
- Fix the implementation
- Update tests if assumptions were wrong
- Don't proceed until green

### 5. Commit and push

Land the change:

```bash
./scripts/format.sh          # Format
git add -A                    # Stage changes
git commit -m "fix: [description]

Fixes: [describe what was wrong]
Change: [describe what changed]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git pull --rebase            # Get latest
bd sync                       # Sync bd
git push                      # Push to remote

bd close <id>                 # Close issue
```

## Differences from Feature Dev

**Minor Edit skips:**
- Critic review (too lightweight)
- QA verification (test coverage sufficient)
- Detailed planning (change is obvious)

**Minor Edit keeps:**
- Test-first development (TDD)
- bd issue tracking
- Checkpoint before commit
- Format and lint checks

## When to Upgrade to Feature Dev

If during implementation you discover:
- Change is more complex than expected
- Multiple files need changes
- Architectural decisions needed
- Edge cases are non-trivial

Then stop and switch to feature-dev workflow:

```bash
bd update <id> --status=open    # Release the issue
```

Then follow feature-dev workflow instead.

## Success Metrics

- [ ] Change is minimal and focused
- [ ] Tests pass (including new test)
- [ ] Code formatted and linted
- [ ] Committed and pushed
- [ ] bd issue closed
