# Task Spec: Fix LOG.md Path References

**Created**: 2025-11-18
**Status**: Approved
**Priority**: P0 - Broken Infrastructure
**Pattern**: #framework-paths #log-infrastructure #documentation-integrity

## Problem Statement

Multiple framework components reference LOG.md at incorrect paths, causing the /log command and framework skill to fail when attempting to append learning patterns.

**Current state**:
- LOG.md EXISTS at: `$ACA_DATA/projects/aops/experiments/LOG.md`
- LOG.md has 360 lines, 36 entries, proper bmem frontmatter ✅
- Framework SKILL.md references: `bots/experiments/LOG.md` ❌
- /log command references: `data/projects/aops/experiments/LOG.md` (missing $ACA_DATA prefix) ⚠️
- README.md documents: `$ACA_DATA/projects/aops/experiments/LOG.md` ✅

**Impact**:
- /log command cannot append entries
- Framework skill cannot load learning patterns
- Institutional knowledge system broken

## Architecture Context

**Authoritative location**:
```
$ACA_DATA/projects/aops/experiments/LOG.md
```

Where:
- `$ACA_DATA` = `/home/nic/src/writing/data` (user's private knowledge base)
- User data must be in Obsidian-compatible bmem markdown format
- LOG.md is append-only, never delete entries
- LOG.md contains 36 learning patterns (critical institutional knowledge)

**Cross-repo access pattern**:
- Skills invoked from ANY directory must access LOG.md via `$ACA_DATA` environment variable
- No assumptions about current working directory
- Framework lives in `$AOPS`, user data lives in `$ACA_DATA` (separate locations)

## Scope

### In Scope
1. Update framework/SKILL.md: Change `bots/experiments/LOG.md` → `$ACA_DATA/projects/aops/experiments/LOG.md`
2. Update /log command: Change `data/projects/aops/experiments/LOG.md` → `$ACA_DATA/projects/aops/experiments/LOG.md`
3. Verify README.md documentation already correct
4. Add integration test: /log command successfully appends entry
5. Add integration test: framework skill loads LOG.md without errors

### Out of Scope
- Migrating LOG.md location (keep in $ACA_DATA)
- Consolidating experiment logs vs LOG.md (architectural decision deferred)
- Modifying LOG.md content or format

## Success Criteria

**Functional Requirements**:
1. /log command appends entries to correct LOG.md file
2. Framework skill loads LOG.md learning patterns successfully
3. All path references use `$ACA_DATA` environment variable (not hardcoded paths)
4. Integration tests pass in both local and remote environments

**Testing Strategy**:
```python
# tests/integration/test_log_command.py
def test_log_command_appends_to_correct_file(tmp_path):
    """Test /log command writes to $ACA_DATA/projects/aops/experiments/LOG.md"""
    # Set up test environment with $ACA_DATA
    test_data_dir = tmp_path / "data"
    test_log = test_data_dir / "projects/aops/experiments/LOG.md"
    test_log.parent.mkdir(parents=True)
    test_log.write_text("---\ntitle: Test Log\n---\n\n# Test\n")

    # Mock $ACA_DATA environment
    with mock.patch.dict(os.environ, {"ACA_DATA": str(test_data_dir)}):
        # Execute /log command workflow
        result = invoke_log_command(
            category="Meta-Framework",
            title="Test Entry",
            observation="Test observation",
            significance="Test significance",
            lesson="Test lesson"
        )

        # Verify entry appended to correct file
        assert test_log.exists()
        content = test_log.read_text()
        assert "Test Entry" in content

# tests/integration/test_framework_skill_loads_log.py
def test_framework_skill_loads_learning_patterns():
    """Framework skill must load LOG.md from $ACA_DATA"""
    # Verify $ACA_DATA is set
    assert os.getenv("ACA_DATA"), "ACA_DATA environment variable required"

    log_path = Path(os.getenv("ACA_DATA")) / "projects/aops/experiments/LOG.md"

    # Verify LOG.md exists at documented location
    assert log_path.exists(), f"LOG.md missing at {log_path}"
    assert log_path.is_file()

    # Verify framework skill can read it
    # (test framework skill invocation with strategic partner mode)
```

**Documentation Requirements**:
- Update framework/SKILL.md line 51: Use `$ACA_DATA/projects/aops/experiments/LOG.md`
- Update /log command line 16: Use `$ACA_DATA/projects/aops/experiments/LOG.md`
- Add comment explaining environment variable usage for cross-repo access

## Implementation Notes

**Files to update**:
1. `skills/framework/SKILL.md`:
   - Line 51: `log = read("bots/experiments/LOG.md")` → `log = read(os.path.join(os.getenv("ACA_DATA"), "projects/aops/experiments/LOG.md"))`
   - Or use environment variable syntax if framework supports it directly

2. `commands/log.md`:
   - Line 16: `data/projects/aops/experiments/LOG.md` → `$ACA_DATA/projects/aops/experiments/LOG.md`

**Validation approach**:
1. Check $ACA_DATA environment variable is set
2. Verify LOG.md exists at `$ACA_DATA/projects/aops/experiments/LOG.md`
3. Test /log command appends entry successfully
4. Test framework skill reads LOG.md without errors
5. Run integration tests

**Edge cases**:
- $ACA_DATA not set: Fail fast with clear error message
- LOG.md missing: Create with proper bmem frontmatter (use template from current LOG.md)
- LOG.md corrupted: Validate frontmatter before appending

## Dependencies

**Blocks**: None (LOG.md already exists and is functional)

**Blocked By**:
- Task 1 (Fix framework path references) - should be done together for consistency

**Related**:
- Task 3 (Document data architecture) - clarifies $AOPS vs $ACA_DATA separation

## Risks

**Low Risk**: LOG.md already exists with correct content at correct location
- Only updating references, not moving files
- Integration tests will catch any path resolution issues

**Mitigation**:
- Test in current working directory ($AOPS)
- Test from other directories to verify $ACA_DATA resolution works

## Success Metrics

- /log command successfully appends entries to LOG.md
- Framework skill loads 36 existing learning patterns without errors
- Integration tests pass in CI
- Zero file-not-found errors when accessing LOG.md
