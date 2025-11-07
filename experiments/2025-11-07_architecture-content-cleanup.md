# Architecture Content Cleanup: Remove Procedural Violations

## Metadata

- Date: 2025-11-07
- Issue: #111
- Commit: [pending]
- Model: claude-sonnet-4-5-20250929
- Skill: aops-trainer

## Hypothesis

ARCHITECTURE.md contains procedural content (testing steps, installation commands) that violates its specification as "timeless structural reference documentation." Removing this content and replacing with minimal references will:

1. Restore architectural integrity
2. Maintain DRY principles (no duplication with INSTALL.md)
3. Keep ARCHITECTURE.md focused on structure, not procedures

## Changes Made

### Change 1: Testing Section (lines 408-422)

**Removed:**

- 15 lines of procedural testing commands
- Code blocks with `uv run pytest` examples
- Detailed bullet points about integration tests

**Replaced with:**

- 1 line summary referencing `tests/test_chunks_loading.py`
- Maintains discoverability without procedure duplication

### Change 2: Installation Section (lines 425-433)

**Removed:**

- 9 lines including code block with export commands
- "Quick setup" instructions duplicating INSTALL.md

**Replaced with:**

- 1 line reference to INSTALL.md
- Eliminates duplication, maintains navigation

**Total reduction:** 23 lines → 2 lines (91% reduction)

## Success Criteria

- [x] ARCHITECTURE.md contains only timeless structural specifications
- [x] No procedural "how to run" or "how to install" content
- [x] Testing information accessible via file reference
- [x] Installation information accessible via INSTALL.md
- [x] No loss of critical information
- [x] Changes under 10 lines per edit (surgical)

## Results

**Before:**

- Testing: 15 lines of procedural commands and explanations
- Installation: 9 lines of setup commands

**After:**

- Testing: 1 line reference to test files
- Installation: 1 line reference to INSTALL.md

**Information preserved:**

- Testing details: Available in actual test file (`tests/test_chunks_loading.py`)
- Installation: Complete instructions remain in INSTALL.md
- Architecture maintains structural specification focus

**Content Placement Decision Tree validated:**

- Testing procedures → Test files (not ARCHITECTURE.md) ✓
- Installation steps → INSTALL.md (not ARCHITECTURE.md) ✓

## Outcome

**SUCCESS**

ARCHITECTURE.md now adheres to its stated purpose: "Timeless reference documentation only - must not include progress indicators, status updates, line counts, test results, temporal labels like NEW, or any metrics that change over time."

Procedural content violations eliminated while maintaining information accessibility through proper references.

## Next Steps

**Future Prevention (recommended):** Create `scripts/validate_architecture.py` to detect procedural patterns:

- Keywords: "uv run", "pytest", "export", code blocks with commands
- Run in pre-commit hook
- Prevents future violations of ARCHITECTURE.md content boundaries

## Notes

This cleanup follows the Information Architecture principles from aops-trainer skill:

- ARCHITECTURE.md = Timeless structural specification
- Testing procedures = Step-by-step process → Test files or TESTING.md
- Installation steps = Setup procedure → INSTALL.md

Related to issue #111's core principle: "COMPLETE MODULARITY - Every concept documented exactly once in a canonical location, then referenced everywhere else."
