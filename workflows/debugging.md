---
id: debugging
category: development
---

# Debugging Workflow

## Overview

Systematic debugging process focused on understanding the problem before fixing it. Emphasizes creating durable tests that verify the fix and prevent regression.

## When to Use

- Investigating bugs or unexpected behavior
- Understanding why something doesn't work
- Reproducing reported issues
- Root cause analysis

## When NOT to Use

If you already know the cause and fix:
- Use minor-edit for simple fixes
- Use feature-dev for complex fixes

## Steps

### 1. Fetch or create bd issue, mark as in-progress

Track the debugging work:

```bash
bd ready                    # Find bugs to investigate
bd update <id> --status=in_progress
```

Or create a new issue:

```bash
bd create --title="Debug: [symptom description]" --type=bug --priority=2
```

### 2. Articulate clear acceptance criteria

Define what "fixed" means:

**What is broken?**
- What is the expected behavior?
- What is the actual behavior?
- How do you know it's broken?

**Success criteria:**
- [ ] Understand root cause
- [ ] Create test that reproduces issue
- [ ] Test fails before fix, passes after
- [ ] Document findings

### 3. Use python-dev skill to design a durable test for success

Create a test that:
1. Reproduces the bug reliably
2. Will pass once bug is fixed
3. Prevents regression in future

```python
def test_bug_reproduction():
    """
    Reproduces bug: [description]

    Expected: [what should happen]
    Actual: [what actually happens]
    """
    # Arrange - Set up conditions that trigger bug
    setup = create_bug_conditions()

    # Act - Perform action that exhibits bug
    result = buggy_function(setup)

    # Assert - This should fail with current code
    assert result == expected_behavior, "Bug: [description]"
```

Run to confirm it reproduces the bug:

```bash
uv run pytest -v test_file.py::test_bug_reproduction
# Should FAIL (confirming bug exists)
```

### 4. Investigate root cause

Systematic investigation:

**Narrow the scope:**
- What minimal code triggers the bug?
- What inputs cause vs. don't cause the issue?
- What changed recently that might have caused this?

**Investigation techniques:**
- Add logging/print statements
- Use debugger (pdb/ipdb)
- Check git history: `git log -p -- file.py`
- Review related code
- Check dependencies/environment

**Questions to answer:**
- Where does the bug originate?
- Why does it happen?
- What assumptions were violated?
- Are there related bugs?

### 5. Report findings and save to bd issue

Document the investigation:

```markdown
## Debugging Findings

**Bug**: [description]

**Root cause**: [explanation of why it happens]

**Affected code**: [file paths and functions]

**Trigger conditions**: [what causes the bug]

**Test created**: test_file.py::test_bug_reproduction
- Reproduces: ✓
- Will verify fix: ✓

**Proposed fix**: [brief description or "needs design"]

**Related issues**: [any related bugs or concerns]
```

Save to bd issue:

```bash
bd update <id> --description="[paste findings]"
```

### 6. Commit and push

Commit the test and findings:

```bash
git add test_file.py
git commit -m "test: add reproduction test for [bug]

Root cause: [brief explanation]
Test reproduces bug reliably
Will verify fix when implemented

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git pull --rebase
bd sync
git push
```

## After Debugging

Once you understand the bug:

**For simple fixes:**
- Switch to minor-edit workflow
- Implement fix
- Verify test now passes

**For complex fixes:**
- Switch to feature-dev workflow
- Plan the fix
- Get critic review if needed

**If unsure:**
- Ask user for direction
- Create follow-up issue for fix
- Mark debugging issue complete

## Common Debugging Patterns

### Intermittent Bugs

- Run test multiple times
- Check for race conditions
- Look for shared mutable state
- Check for timing dependencies

### Environment-Specific Bugs

- Check environment variables
- Verify dependencies (versions)
- Compare working vs. broken environments
- Check file system differences

### Regression Bugs

- Use git bisect to find when bug was introduced
- Review changes in that commit
- Check if tests should have caught it

### Performance Issues

- Profile the code
- Check for N+1 queries
- Look for unnecessary iterations
- Check memory usage

## Success Metrics

- [ ] Root cause understood and documented
- [ ] Test reliably reproduces bug
- [ ] Test will verify fix (clear assertion)
- [ ] Findings saved to bd issue
- [ ] Test committed to prevent regression
- [ ] Next steps clear (fix or design fix)
