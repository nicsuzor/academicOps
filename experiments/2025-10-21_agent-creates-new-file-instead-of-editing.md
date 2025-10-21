# Experiment: Agent Creates _new.sh Instead of Editing Existing File

**Date**: 2025-10-21
**Commit**: (current session, not yet committed)
**Issue**: #139
**Agent**: Main assistant (general-purpose)

## Hypothesis

Agent was asked to simplify `setup_academicops.sh` to use single `.academicOps/` symlink instead of multiple symlinks. Agent should have edited the existing file directly.

## Implementation

Agent created `setup_academicops_new.sh` with the new simplified version, then only moved it to replace the original when user explicitly said "no duplication."

## Violations

- **Axiom #10 violated**: "DRY, modular, and EXPLICIT: one golden path, no defaults, no guessing, no backwards compatibility"
  - Creating duplicate file with `_new` suffix violates DRY
  - Reference: `bots/agents/_CORE.md:44`

- **Version Control Philosophy**: Should trust git for safety, not create backup copies
  - Git provides version history - no need for manual `_new` files
  - If edit breaks something, `git restore` or `git revert` fixes it

## Outcome

**FAILED**: Agent didn't trust version control, created unnecessary duplication

## Lessons

### For Core Axioms Enforcement

**Add explicit instruction about trusting version control:**

Add to `bots/agents/_CORE.md` near Axiom #10 (DRY):

```markdown
**Trust Version Control**: Never create `_new`, `_backup`, or `_old` files
- Git tracks all changes - use `git diff`, `git restore`, `git revert`
- Edit files directly, commit atomically
- ❌ PROHIBITED: `file_new.sh`, `file.bak`, `file_2.sh`
- ✅ REQUIRED: Edit `file.sh` directly, rely on git history
```

### For Instruction Clarity

Current DRY axiom doesn't explicitly cover file-level duplication during edits. Agents may interpret DRY as "don't duplicate code" but not realize it also means "don't duplicate files while editing."

### Pattern

This is defensive behavior - agent creating safety net instead of trusting infrastructure (version control). Similar to code using try/except fallbacks instead of failing fast.

## Related Issues

- None directly related
- Related to fail-fast philosophy (trust infrastructure, don't work around it)

## Modified Files

- `experiments/2025-10-21_agent-creates-new-file-instead-of-editing.md` (created)
- `experiments/INDEX.md` (to be updated)
