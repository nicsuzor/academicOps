# Experiment: Trust Version Control Axiom

## Metadata

- Date: 2025-11-07
- Issue: #139
- Commit: 20991489e77913371eca740d42e910a573e89e7e
- Model: claude-sonnet-4-5

## Hypothesis

Adding explicit axiom about trusting git version control will prevent agents from:

1. Creating backup files (`_new`, `.bak`, `_ARCHIVED_*`, etc.)
2. Preserving files/directories "for reference"
3. Failing to commit and push changes after operations

## Changes Made

**File: chunks/AXIOMS.md**

Added new Axiom #12 "Trust Version Control" after existing axioms, before Behavioral Rules section:

- ❌ NEVER create backup files (specific patterns listed)
- ❌ NEVER preserve "for reference" (git history is the reference)
- ✅ Edit files directly, rely on git
- ✅ Commit AND push after completing work
- ✅ Use git commands to review/restore history
- Rationale: Backup files = distrust of infrastructure
- Tool usage: git-commit skill for major changes, direct git for quick fixes

**Renumbered**: Behavioral Rules now start at #13 (was #12) to avoid conflict

## Success Criteria

1. **Backup prevention**: Agents don't create `_new`, `.bak`, `_old`, `_ARCHIVED_*`, or similar files
2. **No preserved copies**: Agents don't keep directories/files "for reference"
3. **Commit enforcement**: Agents commit AND push after completing logical work units
4. **Measured over**: 5+ agent sessions with file editing operations

## Testing Plan

1. Monitor agent sessions that involve file editing
2. Check for creation of backup/archived files (fail if any created)
3. Verify commits happen after operations (pass if consistent)
4. Track across multiple agents (general-purpose, dev, trainer, etc.)

## Results

[To be filled after testing across multiple sessions]

## Outcome

[Success/Failure/Partial - to be determined after testing]

## Notes

- Related to issue #27 (Agents must commit immediately) and #185 (git commit/push enforcement)
- Issue #185 proposes PostToolUse hook for auto-commits - this axiom provides the educational/instruction layer
- Combined approach: Axiom educates WHY (trust git), Hook enforces HOW (auto-commit)
