---
description: Load development workflow and coding standards
permalink: aops/commands/dev
---

**STEP 1: Load Development Context** (3-tier: framework → personal → project)

Execute these commands to load complete development context:

```bash
uv run python ${ACADEMICOPS}/hooks/load_instructions.py DEVELOPMENT.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py TESTING.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py DEBUGGING.md
uv run python ${ACADEMICOPS}/hooks/load_instructions.py STYLE.md
```

**STEP 2: Invoke Supervisor Skill - MANDATORY FOR ALL /DEV TASKS**

ALL tasks initiated via /dev require supervisor orchestration, including:

- Code implementation and new features
- Debugging and investigation work
- Refactoring and code cleanup
- Understanding infrastructure before making changes

The ONLY exception: Pure information questions with no implementation intent (e.g., "What is X?", "Explain how Y works").

If unclear whether task requires implementation, default to invoking supervisor.

Invoke supervisor skill with complete user request and loaded context:

```
Skill(skill: "supervisor")
```

Then follow the supervisor workflow with the user's request.

**Supervisor MUST create explicit TodoWrite checklist containing**:

1. ✓ **Planning Phase**: Create success checklist with measurable criteria
2. ✓ **Independent Plan Review**: Second Explore/Plan agent reviews plan before implementation
3. ✓ **TDD Cycles**: Break into atomic todo items (one test → one implementation → one commit per item)
4. ✓ **Quality Gates**: All tests pass, git-commit skill validates each commit
5. ✓ **E2E Validation**: Live end-to-end tests pass with real data/APIs (MANDATORY for task completion)
6. ✓ **Independent Review**: Compare actual outcome vs original plan, verify all requirements met
7. ✓ **Persistence**: All commits pushed to remote repository

ARGUMENTS: $ARGUMENTS
