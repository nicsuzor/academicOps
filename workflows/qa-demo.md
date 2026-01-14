---
id: qa-demo
title: QA Verification Demo
type: workflow
category: quality-assurance
dependencies: []
steps:
  - id: gather-context
    name: Gather work context
    workflow: null
    description: Collect original request, acceptance criteria, and work completed
  - id: invoke-qa
    name: "Task(subagent_type='aops-core:qa-verifier', prompt='Verify work...')"
    workflow: null
    description: Spawn independent QA verification
  - id: analyze-verdict
    name: Analyze QA verdict
    workflow: null
    description: Review verification results
  - id: fix-issues
    name: Fix issues if needed
    workflow: null
    description: Address any problems found by QA
  - id: re-verify
    name: "Task(subagent_type='aops-core:qa-verifier', prompt='Re-verify after fixes...')"
    workflow: null
    description: Run QA again after fixes
---

# QA Verification Demo

## Overview

Independent end-to-end verification before work completion. A QA verifier agent checks that work meets acceptance criteria, functions correctly, and follows quality standards.

## When to Use

- Before completing any feature or bug fix
- After all tests pass but before committing final work
- When work affects user-facing functionality
- For complex changes with multiple acceptance criteria

## Steps

### 1. Gather work context

Collect all information needed for verification:

**Original request:**
- What did the user ask for?
- What problem are we solving?

**Acceptance criteria:**
- What are the specific, verifiable conditions for success?
- What functionality must work?
- What quality gates must pass?

**Work completed:**
- What files were changed?
- What tests were added?
- What functionality was implemented?

### 2. Invoke QA verifier agent

Spawn the QA verifier agent with full context:

```javascript
Task(subagent_type="aops-core:qa", model="opus", prompt=`
Verify the work is complete and correct.

**Original request**: [describe what was asked for]

**Acceptance criteria**:
1. [specific criterion #1]
2. [specific criterion #2]
3. [specific criterion #3]

**Work completed**:
- Changed: [list files modified]
- Added: [list new files/tests]
- Tests: [describe test coverage]

**Verification dimensions**:
1. **Functionality**: Does it do what was requested?
2. **Quality**: Does it meet code standards?
3. **Completeness**: Are all criteria met?

Produce a VERIFIED or ISSUES verdict with specific findings.
`)
```

### 3. Analyze QA verdict

Review the QA agent's findings:

**If VERIFIED:**
- Note any suggestions for future improvements
- Proceed to final commit and push
- Document lessons learned

**If ISSUES found:**
- Categorize issues by severity:
  - **Critical**: Must fix before proceeding
  - **Major**: Should fix before proceeding
  - **Minor**: Can defer or document
- Prioritize fixes
- Create plan to address critical/major issues

### 4. Fix issues if needed

Address problems identified by QA:

**For critical/major issues:**
```bash
# Fix the issue
[make necessary changes]

# Verify fix with tests
uv run pytest -v

# Commit fix
git add .
git commit -m "fix: address QA findings - [description]"
```

**For minor issues:**
- Document in TODO comments
- Create bd issue for follow-up
- Note in commit message if relevant

### 5. Re-verify if fixes made

If you made changes based on QA feedback, run verification again:

```javascript
Task(subagent_type="aops-core:qa", model="opus", prompt=`
Re-verify after addressing previous issues.

**Previous issues**:
1. [issue from previous QA]
2. [issue from previous QA]

**Fixes made**:
- [describe fix for issue #1]
- [describe fix for issue #2]

**Verification dimensions**:
1. Previous issues resolved?
2. No new issues introduced?
3. All acceptance criteria still met?

Produce VERIFIED or ISSUES verdict.
`)
```

Repeat until VERIFIED.

## QA Verification Dimensions

The QA verifier checks three dimensions:

### 1. Functionality

**Does it work?**
- Acceptance criteria met?
- Edge cases handled?
- Error cases handled gracefully?
- Integration points work correctly?

**Verification methods:**
- Run the code/tests
- Try edge cases
- Check error handling
- Test integration points

### 2. Quality

**Does it meet standards?**
- Code follows project style?
- Tests are comprehensive?
- Documentation is clear?
- No security issues?
- Performance acceptable?

**Verification methods:**
- Review code changes
- Check test coverage
- Look for anti-patterns
- Security scan
- Performance check if relevant

### 3. Completeness

**Is everything done?**
- All acceptance criteria addressed?
- All TODOs completed?
- All tests passing?
- No debug code left behind?
- Documentation updated?

**Verification methods:**
- Cross-check against acceptance criteria
- Search for TODO comments
- Run full test suite
- Check for console.logs, print statements
- Review relevant docs

## QA Verifier Output Format

The QA verifier should provide:

```markdown
## QA Verification Result

**Verdict**: VERIFIED | ISSUES

### Functionality
- ✓ Criterion #1: [verification method]
- ✓ Criterion #2: [verification method]
- ✗ Criterion #3: [issue found]

### Quality
- ✓ Code style: [check passed]
- ✓ Tests: [coverage details]
- ✗ Security: [issue found]

### Completeness
- ✓ All criteria addressed
- ✓ Tests passing
- ✗ Documentation incomplete

### Issues Found (if any)

**Critical:**
- [issue description and recommendation]

**Major:**
- [issue description and recommendation]

**Minor:**
- [issue description and recommendation]

### Recommendation

[VERIFIED: Proceed with commit and push | ISSUES: Fix critical/major issues before completing]
```

## When to Skip QA Verification

QA verification can be skipped for:
- Trivial changes (typo fixes, comment updates)
- Changes already reviewed by user
- Work explicitly marked as draft/WIP
- Emergency hotfixes (but note QA was skipped)

For all other work, QA verification is mandatory.

## Success Metrics

- [ ] QA verifier produces clear VERIFIED or ISSUES verdict
- [ ] All three dimensions checked (functionality, quality, completeness)
- [ ] Critical and major issues fixed before completion
- [ ] No regressions introduced by fixes
- [ ] Work meets all acceptance criteria
