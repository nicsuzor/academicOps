---
id: feature-dev
category: development
---

# Feature Development Workflow

## Overview

Full test-driven development workflow for feature implementation. Ensures quality through clear acceptance criteria, critic review, TDD implementation, and independent QA verification.

## When to Use

- Adding new features
- Complex modifications affecting multiple files
- Work requiring architectural decisions
- Any development work beyond minor edits

## Steps

### 1. Track work in bd ([[bd-workflow]])

Follow the [[bd-workflow]] to set up issue tracking:
- Check for existing issues
- Create issue if needed
- Mark as in-progress

This ensures work is tracked and visible.

### 2. Articulate clear acceptance criteria

Define specific, verifiable conditions for success:
- What functionality must work?
- What edge cases must be handled?
- What quality gates must pass?

Document these in the bd issue or plan file.

### 3. Create a plan, save to bd issue

Design the implementation approach:
- What files need to change?
- What new components are needed?
- What dependencies exist?
- What testing strategy will be used?

Save the plan to the bd issue for tracking.

### 4. Get critic review ([[spec-review]])

Have the critic agent review your plan:
- Are there edge cases missing?
- Are there simpler approaches?
- Are there potential issues?

Iterate on the plan based on feedback.

### 5. Execute plan steps with TDD ([[tdd-cycle]])

For each feature or component:

**Red phase:**
```bash
# Write failing test for acceptance criterion
uv run pytest -v           # Should fail
```

**Green phase:**
```bash
# Minimal implementation to pass test
uv run pytest -v           # Should pass
```

**Evidence:**
Include test output showing pass/fail states.

**Commit:**
```bash
git add .
git commit -m "feat: [description] - [phase]"
```

Repeat red-green-commit for each criterion.

### 6. CHECKPOINT: All tests pass

Before moving to QA, verify:
```bash
uv run pytest -v           # All tests must pass
./scripts/format.sh        # Format code
uv run ruff check .        # Linting passes
```

If anything fails, fix it before proceeding.

### 7. Invoke QA agent to validate against acceptance criteria

Spawn the QA verifier agent:
```javascript
Task(subagent_type="qa", model="opus", prompt=`
Verify the work is complete.

**Original request**: [feature description]

**Acceptance criteria**:
1. [criterion from plan]
2. [criterion from plan]

**Work completed**:
- [files changed]
- [tests added]

Check all three dimensions and produce verdict.
`)
```

**If VERIFIED**: Proceed to commit and push
**If ISSUES**: Fix the issues, then re-verify before completing

### 8. Commit, push, close bd issue ([[bd-workflow]])

Format, commit, and push:
```bash
./scripts/format.sh         # Format all files
git add -A                   # Stage everything
git commit -m "feat: [description]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git pull --rebase           # Get latest changes
bd sync                      # Sync bd changes (per [[bd-workflow]])
git push                     # Push to remote
```

Close the issue per [[bd-workflow]]:
```bash
bd close <id>                # Mark work complete
git status                   # Verify "up to date with origin"
```

## Quality Gates

This workflow includes multiple quality gates:

1. **Acceptance Criteria** - Clear definition of success
2. **Critic Review** - Early feedback on approach
3. **TDD** - Tests written before implementation
4. **Checkpoint** - All tests pass before QA
5. **QA Verification** - Independent validation
6. **Format/Lint** - Code quality checks

## Success Metrics

- [ ] Feature implements all acceptance criteria
- [ ] All tests pass (100% of committed tests)
- [ ] QA verifier approves implementation
- [ ] Code follows project style (format.sh, ruff)
- [ ] Changes committed and pushed to remote
- [ ] bd issue closed with completion status
