# Task Spec: Fix Framework Path References

**Created**: 2025-11-18
**Status**: Approved
**Priority**: P0 - Broken Infrastructure
**Pattern**: #framework-paths #documentation-integrity

## Problem Statement

Framework skill (skills/framework/SKILL.md) references paths with `bots/` prefix that don't exist in the actual repository structure. This causes file-not-found errors when framework skill attempts to load context.

**Evidence**:
- SKILL.md line 51: `read("bots/CORE.md")` → actual path: `CORE.md`
- SKILL.md line 51: `read("bots/ACCOMMODATIONS.md")` → actual path: `ACCOMMODATIONS.md`
- SKILL.md line 51: `read("bots/skills/framework/STATE.md")` → actual: `skills/framework/STATE.md`
- Multiple references throughout to `bots/tests/`, `bots/experiments/`, etc.

**Impact**: Framework skill cannot load its own required context, violating AXIOM #13 (VERIFY FIRST)

## Architecture Context

**Actual path structure**:
- `$AOPS` = `/home/nic/src/academicOps` (framework repository, may be public)
- `$ACA_DATA` = `/home/nic/src/writing/data` (user's private knowledge base)
- Framework files live at `$AOPS/` root, not under `$AOPS/bots/`
- User data lives at `$ACA_DATA/`, organized per README.md lines 90-112

**Path resolution rules**:
1. Framework files: Use `$AOPS/` or relative paths from repo root
2. User data: Use `$ACA_DATA/` with full paths
3. Cross-repo access: Skills invoked from any directory must access `$ACA_DATA` via environment variable

## Scope

### In Scope
1. Update all path references in `skills/framework/SKILL.md` to remove `bots/` prefix
2. Verify every `read()` call points to existing file or valid environment-based path
3. Update file organization diagram (SKILL.md lines 148-178) to match actual structure
4. Add integration test: framework skill loads all required context without errors
5. Document path resolution patterns for future components

### Out of Scope
- Changing actual directory structure (keep as-is)
- Updating paths in other skills (separate tasks if needed)
- Remote environment .claude/ installation solution (noted as unsolved in user requirements)

## Success Criteria

**Functional Requirements**:
1. All `read()` statements in framework/SKILL.md execute without file-not-found errors
2. File organization diagram matches `ls -R $AOPS` output structure
3. Integration test passes: framework skill invocation loads full context successfully

**Testing Strategy**:
```python
# tests/integration/test_framework_skill_loads_context.py
def test_framework_skill_loads_required_context():
    """Framework skill must load all required context without errors."""
    # Test that each documented read() path exists
    required_files = [
        "ACCOMMODATIONS.md",
        "CORE.md",
        "skills/framework/STATE.md",
        "AXIOMS.md",
        "VISION.md",
        "ROADMAP.md",
    ]

    for file_path in required_files:
        full_path = AOPS / file_path
        assert full_path.exists(), f"Framework context file missing: {file_path}"
        assert full_path.is_file(), f"Path is not a file: {file_path}"
```

**Documentation Requirements**:
- Update SKILL.md "File Organization" section to reflect actual structure
- Add comment explaining $AOPS vs $ACA_DATA path resolution
- Update "Authoritative Sources" section with correct paths

## Implementation Notes

**Path patterns to update**:
- `bots/AXIOMS.md` → `AXIOMS.md` (or `$AOPS/AXIOMS.md` for clarity)
- `bots/skills/*/` → `skills/*/`
- `bots/experiments/LOG.md` → `$ACA_DATA/projects/aops/experiments/LOG.md`
- `bots/tests/` → `tests/`

**Special cases**:
- LOG.md: Lives in user data (`$ACA_DATA/projects/aops/experiments/LOG.md`), not framework repo
- Session logs: In `$ACA_DATA/sessions/`, not framework repo
- Task data: In `$ACA_DATA/tasks/`, not framework repo

**Validation approach**:
1. Extract all `read("...")` patterns from SKILL.md
2. For each path: check if file exists at `$AOPS/{path}` or `$ACA_DATA/{path}`
3. Fix paths that don't resolve
4. Run integration test
5. Update file tree diagram to match `tree -L 2 $AOPS` output

## Dependencies

**Blocks**:
- Task 2: Create LOG.md infrastructure (depends on correct path references)
- All future framework skill invocations

**Blocked By**: None (can proceed immediately)

## Risks

**Low Risk**: Purely documentation/reference updates, no code changes
**Mitigation**: Integration test ensures all paths resolve before committing

## Success Metrics

- Zero file-not-found errors when framework skill loads context
- File organization diagram matches actual structure
- Integration test passes in CI
