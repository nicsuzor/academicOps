# Detail Level Guide: What to Capture Where

Match detail level to file type and importance.

## Task Files (Detailed Documentation)

**When task is completed, document extensively in task file:**

- Technical implementation details
- Design decisions and rationale
- Problems encountered and solutions
- Code/configuration changes made
- Full context for future resumption

**Example (GOOD for task file)**:

```markdown
---
tags:
  - pytest
  - async
  - testing-strategy
  - technical-debt
  - test-organization
---

## Observations

- [solution] Fixed async fixture issue by adding @pytest_asyncio.fixture decorator
- [decision] Chose to use real data instead of mocks for better integration coverage
- [problem] Initial approach with sync fixtures caused event loop conflicts
- [technique] Used conftest.py for shared fixtures across test modules
```

## Project Files (Strategic Updates Only)

**Location strategy:**

- **High-level metadata**: `data/projects/<project>.md` - Overview, milestones, strategic decisions
- **Detailed content**: `data/<project-slug>/` - Specifications, detailed notes, multi-file projects

**Keep `data/projects/<project>.md` at "weekly standup" level - what you'd say in 30-second verbal update:**

✅ **GOOD for `data/projects/<project>.md`** (strategic/resumption context):

- "Completed TJA scorer validation - strong success (88.9% accuracy)"
- "Framework maintenance (scribe skill, hooks)"
- "Strategic decision: Pivoting from X to Y approach due to Z constraint"
- "Milestone reached: Database migration complete, ready for testing"

❌ **TOO MUCH for `data/projects/<project>.md`** (belongs in task files, `data/<project-slug>/`, or git):

- "Fixed test_batch_cli.py: Reduced from 132 lines to 52 lines, eliminated ALL mocking..."
- "Updated config.json lines 45-67 to add new hook timeout values..."
- "Refactored authentication module to use async/await pattern..."

**Two tests before writing to `data/projects/<project>.md`:**

1. Would this appear in weekly report to supervisor? If NO → omit or put in `data/<project-slug>/` or task file
2. Would I mention this in 30-second standup? If NO → omit or put in `data/<project-slug>/` or task file

## What NOT to Capture in `data/projects/<project>.md`

**DO NOT capture in high-level project file** (documented in git log, task files, or `data/<project-slug>/`):

- Infrastructure changes → git log or `data/<project-slug>/infrastructure.md`
- Bug fixes → git log or task files
- Code refactoring → git log
- Configuration updates → git log or `data/<project-slug>/config-notes.md`
- Framework improvements → git log
- Routine meetings → omit (unless strategic decision made)
- Minor task updates → task system tracks these
- Implementation details → task files or `data/<project-slug>/`

**DO capture in `data/projects/<project>.md`**:

- Major milestones reached
- Strategic decisions affecting direction
- Resource allocation changes
- Risk assessments and mitigations
- Ruled-out approaches (with reasoning)
- External dependencies and blockers
- Resumption context for long-running work

**Use `data/<project-slug>/` when**:

- Need multiple files for project-specific content
- Detailed specifications, analysis, or documentation
- Technical details beyond "standup level"
- Link back to high-level project file: `[[../projects/<project>]]`
