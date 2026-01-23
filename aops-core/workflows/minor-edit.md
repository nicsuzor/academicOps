# Minor Edit Workflow

Small, focused change. Single file, obvious fix.

Extends: base-task-tracking, base-tdd, base-verification, base-commit

## When to Use

Use this workflow when:
- Making typo fixes, small bug fixes, or minor refactoring
- Updating documentation or config files
- Someone says "quick change" or "simple fix"

Do NOT use for:
- Multiple files involved (use design)
- Architectural decisions needed (use design)
- Complex logic required (use design)

## Constraints

### Scope Limits

- Changes must affect exactly one file
- The fix must be obvious—no design decisions required

### Upgrade Trigger

If you discover complexity during implementation (multiple files needed, design decisions required, edge cases found), **stop immediately and switch to the design workflow**.

### Inherited Constraints

All constraints from base workflows apply:
- base-task-tracking: task management rules
- base-tdd: test-first when applicable
- base-verification: verify before commit
- base-commit: commit workflow rules

## Triggers

- If multiple files are needed → upgrade to design workflow
- If a design decision is needed → upgrade to design workflow
- If an edge case is discovered → upgrade to design workflow

## How to Check

- Single file scope: changes affect exactly 1 file
- Obvious fix: no design decisions required, fix is self-evident
- Complexity discovered: multiple files needed, or design decision needed, or edge case discovered
