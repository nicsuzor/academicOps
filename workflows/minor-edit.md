---
id: minor-edit
category: development
bases: [base-task-tracking, base-tdd, base-verification, base-commit]
---

# Minor Edit

Small, focused change. Single file, obvious fix.

## Routing Signals

- Typo fixes, small bug fixes, minor refactoring
- Documentation updates, config changes
- "Quick change", "simple fix"

## NOT This Workflow

- Multiple files → [[design]]
- Architectural decisions → [[design]]
- Complex logic → [[design]]

## Unique Steps

None. Just follow base workflows with minimal scope.

## Upgrade Signal

If you discover complexity during implementation (multiple files, design decisions, edge cases), **stop and switch to [[design]]**.
