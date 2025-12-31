---
name: ttd
description: Alias for hypervisor tdd - Test-first development workflow
permalink: aops/commands/ttd
tools:
  - Skill
---

# /ttd - Test-First Development (Alias)

Invoke the hypervisor skill with TDD workflow:

```
Skill(skill="hypervisor", args="tdd $ARGUMENTS")
```

## Usage

```
/ttd {task description}
```

## What It Does

Orchestrates test-driven development with:
- Failing test → minimal implementation → verification cycle
- Mandatory `python-dev` skill invocation
- Quality gates (critic review, fail-fast compliance, QA verification)
- Commit and push after each cycle

See [[skills/hypervisor/workflows/tdd.md]] for full workflow details.
