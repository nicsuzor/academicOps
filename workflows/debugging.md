---
id: debugging
category: development
---

# Debugging Workflow

Systematic debugging: understand the problem before fixing it. Create durable tests that verify fix and prevent regression.

## When to Use

- Investigating bugs or unexpected behavior
- Understanding why something doesn't work
- Reproducing reported issues
- Root cause analysis

## When NOT to Use

If you already know the cause and fix:
- Simple fixes → minor-edit
- Complex fixes → feature-dev

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| "Why doesn't this work?", "Investigate bug" | Debugging |
| "Fix this bug" (cause unknown) | Debugging |
| "Fix this bug" (cause known) | Minor-edit or feature-dev |

## Key Steps

1. Track work (create/claim task)
2. Define success criteria (what "fixed" means)
3. Create reproducing test (fails now, passes after fix)
4. Investigate root cause
5. Document findings in task
6. Commit test (prevents regression)

## Quality Gates

- Root cause understood and documented
- Test reliably reproduces bug
- Test will verify fix
- Findings saved to task
- Next steps clear (fix or design fix)

## After Debugging

- Simple fix → switch to minor-edit
- Complex fix → switch to feature-dev
- Unsure → ask user, create follow-up task
