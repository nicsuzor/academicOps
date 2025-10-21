---
description: Load development workflow and coding standards
---
Load developer workflow from 3-tier hierarchy.

Execute:

```bash
uv run python ${ACADEMICOPS_BOT}/bots/hooks/load_instructions.py DEVELOPER.md
```

## What This Loads

**DEVELOPER.md** provides:

1. **🚨 CRITICAL 6-Step Development Workflow**:
   - STOP & ANALYZE (check GitHub issues first)
   - EXPLORE (MANDATORY - search codebase, prevent rushing to code)
   - PLAN (document solution in issue)
   - TEST DRIVEN DEVELOPMENT (run tests first, write failing test, iterate)
   - VALIDATE (full test suite)
   - COMMIT & UPDATE (conventional commits, update issues)

2. **Project Rules**:
   - Keep projects self-contained (polyrepo, not monorepo)
   - Everything self-documenting
   - Fail-fast (no fallbacks)
   - TDD mandatory
   - Document in GitHub issues

After loading, confirm to user:

```
✅ Loaded developer workflow
Ready for development with systematic 6-step process
```

## When to Use This Command

Use `/dev` when:
- Starting development work in a project
- Need the structured workflow enforced
- Want "EXPLORE MANDATORY" reminder (prevent rushing to code)
- Beginning a coding session

## Related Commands

- `/ttd` - Load test-driven development methodology
- `/ops` - View all available academicOps commands
- `/trainer` - Switch to trainer mode for framework improvements
