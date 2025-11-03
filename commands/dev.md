---
description: Load development workflow and coding standards
---

Invoke the `supervisor` agent to orchestrate development work through structured TDD workflow.

The supervisor agent MUST create explicit TodoWrite checklist containing:

**MANDATORY Checklist Items**:
1. ✓ Independent plan review (second Explore/Plan agent reviews initial plan before implementation)
2. ✓ TDD cycles broken into atomic todo items (one test → one implementation → one commit per item)
3. ✓ Independent review of final state (compare actual outcome vs original plan, verify all requirements met)
4. ✓ All changes committed via git-commit skill validation
5. ✓ All commits pushed to remote repository

See SUPERVISOR.md for complete TDD workflow (STEP 0-5).

ARGUMENTS: $ARGUMENTS
