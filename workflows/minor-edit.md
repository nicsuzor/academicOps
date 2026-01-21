---
id: minor-edit
category: development
---

# Minor Edit Workflow

Streamlined workflow for small, targeted changes. Includes TDD but skips critic review and QA verification.

## When to Use

- Typo fixes
- Small bug fixes
- Minor refactoring
- Documentation updates
- Configuration changes
- Simple one-file changes

## When NOT to Use

Use feature-dev or design workflow if:
- Change affects multiple files
- Architectural decisions required
- Complex logic changes
- New features (not bug fixes)
- User-facing behavior changes

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| Single file, obvious fix | Minor edit |
| "Quick change", "simple fix" | Minor edit |
| Multiple files, design decisions | Feature-dev |

## Key Steps

1. Track work (create/claim task)
2. Write failing test (TDD)
3. Make minimal change
4. Verify tests pass
5. Commit and push

## Quality Gates

- Change is minimal and focused
- Tests pass (including new test)
- Code formatted and linted
- Task completed

## Upgrade Signal

If during implementation you discover complexity (multiple files, architectural decisions, edge cases), stop and switch to feature-dev workflow.
