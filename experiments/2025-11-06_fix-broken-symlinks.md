# Fix Broken Symlinks in Skills

## Metadata
- Date: 2025-11-06
- Issue: #194
- Commit: [to be added]
- Model: claude-sonnet-4-5-20250929

## Hypothesis

Replacing absolute symlink paths with relative paths will fix broken symlinks in skills/aops-trainer/resources/ and skills/git-commit/references/, making the repository portable and compliant with README.md specification.

## Changes Made

**Fixed 6 broken symlinks**:

1. **skills/aops-trainer/resources/**:
   - Removed broken symlinks pointing to `/home/nic/src/bot/chunks/*`
   - Created relative symlinks: `ln -s ../../../chunks/FILE.md`
   - Files: AXIOMS.md, INFRASTRUCTURE.md, SKILL-PRIMER.md

2. **skills/git-commit/references/**:
   - Removed broken symlinks pointing to `/home/nic/src/bot/docs/_CHUNKS/*`
   - Created relative symlinks: `ln -s ../../../docs/_CHUNKS/FILE.md`
   - Files: FAIL-FAST.md, GIT-WORKFLOW.md, TESTS.md

**Path calculation**:
- From `skills/[skill-name]/resources/`, need `../../../` to reach project root
- From `skills/[skill-name]/references/`, need `../../../` to reach project root
- Then navigate to `chunks/` or `docs/_CHUNKS/`

## Success Criteria

- [ ] Zero broken symlinks detected by `find . -type l ! -exec test -e {} \; -print`
- [ ] All files in skills/aops-trainer/resources/ are readable via `ls -L`
- [ ] All files in skills/git-commit/references/ are readable via `ls -L`
- [ ] Symlinks use relative paths per README.md lines 294-300

## Results

**All success criteria met**:

✓ Broken symlink count: 0 (was 6)
✓ skills/aops-trainer/resources/ readable: AXIOMS.md, INFRASTRUCTURE.md, SKILL-PRIMER.md
✓ skills/git-commit/references/ readable: FAIL-FAST.md, GIT-WORKFLOW.md, TESTS.md
✓ All symlinks now use relative paths (e.g., `../../../chunks/AXIOMS.md`)

**Validation commands**:
```bash
# Before fix: 6 broken symlinks
# After fix: 0 broken symlinks
find . -type l ! -exec test -e {} \; -print | wc -l
# Output: 0

# Verify target files readable
ls -L skills/aops-trainer/resources/
ls -L skills/git-commit/references/
```

## Outcome

**Success** - All broken symlinks fixed using relative paths as specified in README.md.

**Root cause confirmed**: Symlinks were created with absolute paths to `/home/nic/src/bot/` repository instead of relative paths to local directories. This broke portability.

**Compliance**: Repository now follows README.md specification (lines 294-300) for skill symlink structure.

**No architectural changes needed**: This was a one-time repository state fix, not a recurring behavior pattern requiring scripts/hooks/config enforcement.
