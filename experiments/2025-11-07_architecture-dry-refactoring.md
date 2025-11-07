# Experiment: ARCHITECTURE.md DRY Refactoring

## Metadata
- Date: 2025-11-07
- Issue: #111
- Commit: [to be added]
- Model: claude-sonnet-4-5
- Skill: aops-trainer

## Hypothesis

Refactoring ARCHITECTURE.md to reference authoritative sources (paths.toml, chunks/INFRASTRUCTURE.md) instead of duplicating content will:
1. Enforce DRY principles per issue #111
2. Maintain ARCHITECTURE.md's usefulness as specification
3. Reduce bloat while improving maintainability

## Context

Recent work established paths.toml as authoritative source for path configuration. ARCHITECTURE.md was identified as duplicating:
- File structure trees (already in chunks/INFRASTRUCTURE.md)
- Environment variable definitions (authoritative source: paths.toml)
- Three-tier loading details (already in chunks/INFRASTRUCTURE.md)

User requested: "now that architecture.md isn't authoritative, you should chunk it up and make it modular and dry."

## Changes Made

### 1. Environment Variables Section (lines 129-136)
**Before** (7 lines):
```markdown
### Environment Variables

Required variables:

- `$ACADEMICOPS` - Path to framework repository (PUBLIC)
- `$ACADEMICOPS_PERSONAL` - Path to user's personal repository (PRIVATE)

Used for path resolution, three-tier loading, and hook invocation.
```

**After** (3 lines):
```markdown
### Environment Variables

See `paths.toml` for authoritative path configuration.

Required: `$ACADEMICOPS` (framework repository), `$ACADEMICOPS_PERSONAL` (personal repository)
```

### 2. File Structure Section (lines 21-90)
**Before** (70 lines): Four complete directory trees for framework/personal/project/installation

**After** (8 lines):
```markdown
## File Structure

See `chunks/INFRASTRUCTURE.md` for directory structure and `paths.toml` for path configuration.

**Repository tiers**:
- **Framework**: `$ACADEMICOPS/` (agents/, skills/, commands/, hooks/, core/, chunks/, docs/)
- **Personal**: `$ACADEMICOPS_PERSONAL/` (core/, docs/bots/ for user customizations)
- **Project**: `$PWD/` (core/, docs/bots/ for project-specific context)
- **Installation**: `~/.claude/` (installed skills, settings, session logs)
```

### 3. Instruction Loading System (lines 76-81)
**Before** (22 lines): Complete loading behavior explanation with code examples

**After** (4 lines):
```markdown
## Instruction Loading System

See `chunks/INFRASTRUCTURE.md` for complete three-tier loading details.

**SessionStart hook**: Loads `_CORE.md` from three tiers (framework → personal → project). Framework tier required, personal/project optional. Priority in conflicts: Project > Personal > Framework.
```

### Line Count Reduction
- Before: 413 lines
- After: 329 lines
- Reduction: 84 lines (~20%)

## Success Criteria

- [x] Environment variables reference paths.toml as authoritative source
- [x] File structure references chunks/INFRASTRUCTURE.md and paths.toml
- [x] Three-tier loading references chunks/INFRASTRUCTURE.md
- [x] Component Specifications section unchanged (ARCHITECTURE.md's core purpose)
- [x] Design Principles section unchanged (architectural patterns)
- [ ] User confirms ARCHITECTURE.md still useful as specification
- [ ] No information loss (all details accessible via references)

## Test Procedure

1. Verify referenced files contain complete information:
   - paths.toml has environment variables and path configuration
   - chunks/INFRASTRUCTURE.md has directory structure and three-tier loading

2. User review: Does ARCHITECTURE.md still serve its purpose as "timeless structural specification"?

3. Check: Can someone understand the architecture by reading ARCHITECTURE.md + following references?

## Expected Challenges

- User may find reduced detail makes ARCHITECTURE.md less standalone
- Balance between DRY compliance and document usability
- Ensuring referenced files are discoverable

## Results

[To be filled after user review]

## Outcome

[Success/Failure/Partial - to be determined]

## Analysis

[What worked, what didn't, why - to be filled]

## Next Steps

[Based on outcome - to be filled]
