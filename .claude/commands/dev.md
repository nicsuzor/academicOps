---
description: Load development workflow and coding standards
---
Load developer workflow files from the academicOps framework.

**This command is documentation-as-code:** The files listed below define what gets loaded for development work.

## Files to Load

Execute the following and present output to user:

```bash
${ACADEMICOPS_BOT}/scripts/read_instructions.py _CHUNKS/DEVELOPER.md
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
