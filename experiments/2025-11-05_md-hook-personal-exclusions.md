# Experiment: Add $ACADEMICOPS_PERSONAL Content Directory Exclusions to .md Hook

## Metadata

- Date: 2025-11-05
- Issue: #189
- Commit: f8a110d
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Adding checks for $ACADEMICOPS_PERSONAL content directories (talks/, slides/, data/) to the `_is_allowed_md_path()` function will prevent false positive warnings when creating legitimate content .md files in the writing repository, while maintaining protection against documentation bloat in other repositories.

## Changes Made

Modified `hooks/validate_tool.py`:

1. Added `import os` to access environment variables
2. Updated `_is_allowed_md_path()` function (lines 404-468):
   - Added check for $ACADEMICOPS_PERSONAL environment variable
   - If CWD matches $ACADEMICOPS_PERSONAL, allow .md files in:
     - talks/ (presentation content)
     - slides/ (slide decks)
     - data/ (data files)
   - Preserved existing block logic for root-level .md and docs/

**Rationale:** Hook enforcement is the correct layer per enforcement hierarchy (Q2). These directories contain content artifacts, not documentation, so they should be exempt from the documentation philosophy validation.

## Success Criteria

1. **Hook allows legitimate content** (primary goal):
   - Write to `$ACADEMICOPS_PERSONAL/talks/2025-digi-misinfo.md` → No warning (PASS)
   - Write to `$ACADEMICOPS_PERSONAL/slides/presentation.md` → No warning (PASS)
   - Write to `$ACADEMICOPS_PERSONAL/data/notes.md` → No warning (PASS)

2. **Hook maintains documentation blocks** (regression check):
   - Write to `$ACADEMICOPS_PERSONAL/docs/README.md` → Warning (PASS)
   - Write to `$ACADEMICOPS_PERSONAL/HOWTO.md` → Warning (PASS)

3. **Hook behavior unchanged in other repos**:
   - Write to `$ACADEMICOPS/docs/README.md` → Warning (PASS)
   - Write to any other repo's root .md file → Warning (PASS)

## Test Plan

1. Switch to writing repository (`cd $ACADEMICOPS_PERSONAL`)
2. Attempt Write tool calls to test paths above
3. Verify hook output (allow vs warn)
4. Document actual vs expected behavior

## Results

[To be filled after testing in real writing repository session]

## Outcome

[Success/Failure/Partial - to be determined after testing]

## Notes

- The hook now imports `os` module (line 14)
- Logic added at lines 444-454 (11 lines total including comments)
- Falls below bloat threshold (<15 lines)
- Solves immediate user pain point (false positives in writing repo)
- Maintains fail-safe behavior (if $ACADEMICOPS_PERSONAL not set, no behavior change)
