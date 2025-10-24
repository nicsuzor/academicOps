---
description: Load test-driven development workflow
---
Load test-driven development methodology files from the 3-tier hierarchy (bot � personal � project).

**This command is documentation-as-code:** The files listed below define what gets loaded for TTD workflow.

## Files to Load

Run `read_instructions.py` for each of these files to load from all three levels:

1. **TESTING.md** - Core testing philosophy and practices
   - Unit vs integration tests
   - Testing pyramid
   - Cost optimization (Haiku for integration tests)

2. **_CHUNKS/FAIL-FAST.md** - Fail-fast development principle
   - No fallbacks, no defensive programming
   - Explicit configuration required
   - One golden path

## Execution

Execute:

```bash
uv run python ${ACADEMICOPS_BOT}/bots/hooks/load_instructions.py TESTING.md
uv run python ${ACADEMICOPS_BOT}/bots/hooks/load_instructions.py FAIL-FAST.md
```

After loading, confirm to the user:

```
Loaded TTD workflow files
Ready for test-driven development
```

## When to Use This Command

Use `/ttd` when:
- Starting development work in a project
- Need confirmation that testing methodology is loaded
- Want to ensure fail-fast principles are active
- Beginning a coding session that will involve writing tests

## Related Commands

- `/ops` - View all available academicOps commands
- `/trainer` - Switch to trainer mode for framework improvements
