---
id: feature-dev
title: Feature Development Workflow
type: workflow
category: development
dependencies: []
steps:
  - id: claim-issue
    name: Fetch or create bd issue, mark as in-progress
    workflow: null
    description: Identify and claim the work item in issue tracker
  - id: acceptance-criteria
    name: Articulate clear acceptance criteria
    workflow: null
    description: Define what constitutes success for this feature
  - id: create-plan
    name: Create a plan, save to bd issue
    workflow: null
    description: Design implementation approach and document it
  - id: critic-review
    name: Get critic review
    workflow: "[[spec-review]]"
    description: Have critic agent review the plan for issues
  - id: tdd-implementation
    name: Execute plan steps with TDD
    workflow: "[[tdd-cycle]]"
    description: Implement using test-driven development
  - id: checkpoint-tests
    name: CHECKPOINT - All tests pass
    workflow: null
    description: Verify all tests are passing before QA
  - id: qa-verification
    name: Invoke QA agent to validate against acceptance criteria
    workflow: "[[qa-demo]]"
    description: Independent verification of implementation
  - id: commit-push
    name: Commit, push, update bd issue
    workflow: null
    description: Land changes and update issue tracking
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

### 1. Fetch or create bd issue, mark as in-progress

Check if a related issue exists:
```bash
bd ready                    # Show issues ready to work
bd list --status=open       # All open issues
```

Claim the issue:
```bash
bd update <id> --status=in_progress
```

Or create a new issue if needed:
```bash
bd create --title="..." --type=feature --priority=2
```

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
Task(subagent_type="qa-verifier", model="opus", prompt=`
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

### 8. Commit, push, update bd issue

Final commit and sync:
```bash
./scripts/format.sh         # Format all files
git add -A                   # Stage everything
git commit -m "feat: [description]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git pull --rebase           # Get latest changes
bd sync                      # Sync bd changes
git push                     # Push to remote

bd close <id>                # Close the issue
```

Verify push succeeded:
```bash
git status                   # Should show "up to date with origin"
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
