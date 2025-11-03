---
description: Load development workflow and coding standards
---

**STEP 1: Load Development Context** (3-tier: framework → personal → project)

Execute these commands to load complete development context:

```bash
uv run python ${ACADEMICOPS}/hooks/load_instructions.py DEVELOPMENT.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py TESTING.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py DEBUGGING.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py STYLE.md
```

**STEP 2: MANDATORY - Invoke Supervisor Agent**

You MUST invoke the supervisor agent to orchestrate this work. Do NOT attempt development tasks directly.

**Supervisor MUST create explicit TodoWrite checklist containing**:

1. ✓ **Planning Phase**: Create success checklist with measurable criteria
2. ✓ **Independent Plan Review**: Second Explore/Plan agent reviews plan before implementation
3. ✓ **TDD Cycles**: Break into atomic todo items (one test → one implementation → one commit per item)
4. ✓ **Quality Gates**: All tests pass, git-commit skill validates each commit
5. ✓ **E2E Validation**: Live end-to-end tests pass with real data/APIs (MANDATORY for task completion)
6. ✓ **Independent Review**: Compare actual outcome vs original plan, verify all requirements met
7. ✓ **Persistence**: All commits pushed to remote repository

**Context Efficiency Strategy**:

The supervisor will:
- Read all loaded instructions (DEVELOPMENT, TESTING, DEBUGGING, STYLE)
- Delegate atomic tasks to specialized subagents (dev, tester, etc.)
- Each subagent loads only its needed context
- Supervisor maintains overall workflow and quality gates

This approach saves context by having supervisor coordinate while subagents execute with focused context.

ARGUMENTS: $ARGUMENTS
