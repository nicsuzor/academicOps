---
name: ttd
description: Alias for /supervise tdd - Test-first development workflow
permalink: aops/commands/ttd
tools:
  - Skill
---

# /ttd - Test-First Development (Alias)

This is an alias for `/supervise tdd`. Invoke the supervisor skill with TDD workflow:

```
Skill(skill="supervisor", args="tdd $ARGUMENTS")
```

## Usage

```
/ttd {task description}
```

Equivalent to:
```
/supervise tdd {task description}
```

## What It Does

Orchestrates test-driven development with:
- Failing test → minimal implementation → verification cycle
- Mandatory `python-dev` skill invocation
- Quality gates (critic review, fail-fast compliance, QA verification)
- Commit and push after each cycle

See [[skills/supervisor/workflows/tdd.md]] for full workflow details.
