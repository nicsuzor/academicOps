---
id: feature-dev
category: development
---

# Feature Development Workflow

## Overview

Test-driven implementation workflow. Takes a designed feature (with spec, acceptance criteria, and plan) and implements it through TDD cycles with QA verification.

**Input**: bd issue with approved spec, acceptance criteria, and implementation plan (from [[design]] workflow).

## When to Use

- Implementing features that have been designed and approved
- TDD-style development with red-green-refactor cycles
- Work requiring independent QA verification

## Prerequisites

Before starting, verify you have:

1. **bd issue** with feature tracked
2. **Acceptance criteria** documented and approved
3. **Implementation plan** reviewed by critic

**Don't have these?** Run [[design]] workflow first.

For simple changes that don't need full design, see [[minor-edit]].

## Steps

### 1. Execute plan with TDD ([[tdd-cycle]])

For each acceptance criterion:

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

**Commit:**
```bash
git add .
git commit -m "feat: [description] - [criterion]"
```

Repeat red-green-commit for each criterion.

### 2. CHECKPOINT: All tests pass

Before QA, verify everything works:

```bash
uv run pytest -v           # All tests must pass
./scripts/format.sh        # Format code
uv run ruff check .        # Linting passes
```

If anything fails, fix before proceeding.

### 3. QA verification

Spawn QA agent to validate against acceptance criteria:

```javascript
Task(subagent_type="qa", model="opus", prompt=`
Verify the implementation is complete.

**Feature**: [description]
**bd issue**: [id]

**Acceptance criteria**:
1. [criterion from plan]
2. [criterion from plan]

**Work completed**:
- [files changed]
- [tests added]

Check functionality, quality, and completeness. Return verdict.
`)
```

**If VERIFIED**: Proceed to commit and push
**If ISSUES**: Fix issues, re-run checkpoint, re-verify

### 4. Commit, push, close ([[bd-workflow]])

```bash
./scripts/format.sh         # Format all files
git add -A                   # Stage everything
git commit -m "feat: [description]

Co-Authored-By: Claude <noreply@anthropic.com>"

git pull --rebase           # Get latest changes
bd sync                      # Sync bd
git push                     # Push to remote

bd close <id>                # Mark complete
git status                   # Verify "up to date with origin"
```

## Quality Gates

1. **TDD** - Tests written before implementation
2. **Checkpoint** - All tests pass before QA
3. **QA Verification** - Independent validation
4. **Format/Lint** - Code quality checks

## Success Metrics

- [ ] All acceptance criteria implemented
- [ ] All tests pass
- [ ] QA verifier approves
- [ ] Code formatted and linted
- [ ] Changes pushed to remote
- [ ] bd issue closed

## Integration with Other Workflows

- **design**: Provides the spec, acceptance criteria, and plan this workflow implements
- **tdd-cycle**: The core red-green-refactor loop used in Step 1
- **bd-workflow**: Tracks work throughout implementation
- **minor-edit**: For simpler changes that don't need full TDD cycle
