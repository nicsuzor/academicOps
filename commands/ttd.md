---
name: ttd
description: Alias for /supervise tdd - Test-first development workflow
permalink: aops/commands/ttd
---

# /ttd - Test-First Development (Alias)

Equivalent to `/do` with TDD workflow loaded.

## Usage

```
/ttd {task description}
```

## Execution

Load the TDD workflow template and execute via /do pipeline:

1. Read `skills/supervisor/workflows/tdd.md` to get iteration-unit, quality-gate, required-skills
2. Follow /do phases with TDD-specific constraints:
   - Failing test → minimal implementation → verification cycle
   - Mandatory `python-dev` skill invocation
   - Quality gates (critic review, fail-fast compliance)
   - Commit and push after each cycle

See [[skills/supervisor/workflows/tdd.md]] for workflow details.
