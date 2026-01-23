---
id: base-commit
category: base
---

# Base: Commit

**Composable base pattern.** Used when work modifies files.

## Pattern

1. Stage specific files (not `git add -A`)
2. Commit with clear message (why, not what)
3. Push to remote

## When to Skip

- No file modifications made
- User explicitly requests no commit
