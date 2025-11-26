# Task: Documentation Update Skill

**Date**: 2025-11-26
**Stage**: 2 (Scripted Tasks)
**Priority**: P1 (Critical for maintaining framework integrity)

## Problem Statement

**What manual work are we automating?**

Currently, keeping README.md up to date requires manual verification:
- Checking if new files are documented in the file tree
- Ensuring the tree structure matches actual filesystem
- Detecting documentation drift between README.md and reality
- Identifying conflicts between documentation files
- Verifying all references resolve correctly

This is error-prone and time-consuming, leading to documentation drift.

**Why does this matter?**

README.md is intended to be the authoritative source of truth for framework structure. When it's out of date:
- New developers can't find files
- Documentation conflicts go undetected
- SSoT principle is violated
- Trust in documentation erodes

**Who benefits?**

Nic and any future framework maintainers - ensures documentation stays trustworthy.

## Success Criteria

**The automation is successful when**:

1. Every file in the repository has a corresponding entry in README.md file tree
2. Documentation conflicts are automatically detected before commits
3. README.md file tree structure accurately reflects actual filesystem
4. All wikilink-style references resolve to existing files
5. Zero manual verification needed to trust README.md is current

**Quality threshold**: Fail-fast on any discrepancy. Documentation must be 100% accurate or the skill reports failure.

## Scope

### In Scope

- Scan filesystem to discover all files in academicOps repository
- Parse README.md to extract documented file tree
- Compare actual vs documented state
- Generate two-level file tree structure:
  - Level 1: High-level overview (show directories like `skills/` but not their contents)
  - Level 2: Detailed breakdown (all files, including those referenced in skill files)
- Detect missing entries in documentation
- Detect outdated entries (documented files that don't exist)
- Validate all wikilink references resolve
- Update README.md with corrected file tree
- Detect conflicts between authoritative sources (README, AXIOMS, etc.)

### Out of Scope

- Updating other documentation files (only README.md)
- Checking content quality (only structure and references)
- Validating code correctness
- Performance optimization of large repos (academicOps is small)
- Auto-generating file descriptions (human-written comments preserved)

**Boundary rationale**: This skill does ONE thing: ensure README.md file tree is complete and accurate. Content quality and other documentation maintenance are separate concerns.

## Dependencies

### Required Infrastructure

- Python 3.11+ with pathlib for filesystem operations
- Access to $AOPS environment variable
- README.md exists and is writable
- pytest for integration tests

### Data Requirements

- Read access to entire academicOps repository
- Write access to README.md
- No external data sources needed
- Gracefully handle permission errors (fail-fast with clear message)

## Integration Test Design

### Test Setup

Create temporary test repository structure with known files and outdated README.md:

```python
def test_docs_update_skill(tmp_path):
    """Test that docs-update skill detects and corrects documentation drift."""
    # Create test repo structure
    skills_dir = tmp_path / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Test Skill")

    # Create README.md missing the new skill
    readme = tmp_path / "README.md"
    readme.write_text("""# Test Repo
```
$AOPS/
├── skills/
```
""")

    # Run skill with test path
    result = run_docs_update_skill(tmp_path)

    # Verify skill detected missing entry
    assert "test-skill" in result.missing_entries

    # Verify README.md updated
    updated = readme.read_text()
    assert "test-skill" in updated
```

### Test Execution

```bash
# Run integration test
pytest tests/integration/test_docs_update_skill.py -v

# Run with actual repo (verify mode only, no writes)
python skills/framework/scripts/docs_update.py --verify
```

### Test Validation

```python
# Validation checks:
- All files in tmp repo appear in updated README.md
- No extra entries (documented but don't exist)
- Two-level tree structure present
- Wikilink references validated
- Test exits with success code
```

### Test Cleanup

```python
# pytest tmp_path fixture auto-cleans
# No persistent state changes in test mode
```

### Success Conditions

- [x] Test initially fails (README.md missing entries)
- [ ] Test passes after implementation
- [ ] Test covers happy path (all files documented)
- [ ] Test covers missing entries
- [ ] Test covers extra entries (documented but don't exist)
- [ ] Test validates wikilink resolution
- [ ] Test is idempotent
- [ ] Test cleanup leaves no artifacts

## Implementation Approach

### High-Level Design

The skill operates as an agent-invoked workflow, NOT a standalone script.

**Components**:

1. **Filesystem Scanner**: Walk repo, collect all file paths (agent uses Glob/Bash)
2. **Documentation Parser**: Extract file tree from README.md (agent uses Read tool)
3. **Comparator**: Identify discrepancies (agent uses LLM reasoning)
4. **Tree Generator**: Create two-level tree structure (agent uses LLM + template)
5. **Validator**: Check references resolve (agent uses Read + grep for wikilinks)
6. **Updater**: Write corrected README.md (agent uses Edit tool)

**Data Flow**:
1. Agent scans filesystem → file list
2. Agent reads README.md → documented tree
3. Agent compares → discrepancies list
4. Agent generates new tree → two-level structure
5. Agent validates → reference check
6. Agent updates README.md → corrected version

### Technology Choices

**Language/Tools**: Claude Code skill (agent-driven, not standalone script)

**Why agent-driven**:
- Agents have Read/Write/Edit tools built-in
- LLM can intelligently parse complex tree structures
- Agents can preserve human-written comments/descriptions
- No need for complex tree parsing libraries
- Follows "agents orchestrate" principle from framework skill

**Libraries**: None (uses Claude Code built-in tools)

**Rationale**: This is orchestration and reasoning work, perfect for agents. Writing a script would violate the "don't duplicate Claude capabilities" principle.

### Error Handling Strategy

**Fail-fast cases**:

- README.md doesn't exist or unreadable
- $AOPS environment variable not set
- File tree section missing from README.md
- Unable to write updated README.md

**Graceful degradation cases**:

- Unknown file types → include in tree anyway
- Multiple tree sections found → use first, warn about duplicates
- Ambiguous wikilink targets → list all candidates, let human choose

**Recovery mechanisms**:

- All operations are read-only until final write
- Keep backup of original README.md content
- Provide diff before applying changes
- User can reject changes and keep original

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Agent incorrectly parses README.md tree structure
   - **Detection**: Integration test validates parsing against known structure
   - **Impact**: Generated tree might be incomplete or malformed
   - **Prevention**: Clear tree format in README.md, test with multiple tree styles
   - **Recovery**: Fail-fast with clear error, preserve original README.md

2. **Failure mode**: Large repo causes performance issues
   - **Detection**: Timeout in integration test
   - **Impact**: Skill can't complete in reasonable time
   - **Prevention**: academicOps is small (~100 files), not a concern initially
   - **Recovery**: If needed later, add caching or incremental updates

3. **Failure mode**: Concurrent edits to README.md while skill runs
   - **Detection**: Git diff shows unexpected changes
   - **Impact**: Skill might overwrite user edits
   - **Prevention**: Skill runs on demand, not continuously
   - **Recovery**: Git history preserves previous version

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- Number of discrepancies found per run
- Time to complete full scan and update
- Frequency of skill invocation
- False positives (files incorrectly flagged as missing)

**Monitoring approach**:

- Log each skill invocation to experiment log
- Track discrepancies found over time (should decrease as we stabilize)
- Alert if skill finds >10 discrepancies (indicates major drift)

**Validation frequency**:

- Run before every commit to dev branch (via pre-commit hook)
- Run on demand when adding new files
- Run weekly as part of framework health check

## Documentation Requirements

### Code Documentation

- [ ] SKILL.md file with clear invocation instructions
- [ ] Docstrings for any helper functions (if needed)
- [ ] Inline comments for tree generation logic
- [ ] Examples of before/after README.md structure

### User Documentation

- [ ] Add to framework skill workflows (when to use docs-update)
- [ ] Update README.md to document its own structure expectations
- [ ] Add to pre-commit hook documentation
- [ ] Create experiment log entry when complete

### Maintenance Documentation

- [ ] Known limitations (assumes specific tree format)
- [ ] Future improvements (semantic conflict detection, auto-descriptions)
- [ ] Dependencies (none beyond Claude Code tools)

## Rollout Plan

### Phase 1: Validation (Experiment)

- Create skill and run on current academicOps repo
- Manually verify generated tree is correct
- Check for false positives/negatives
- Document findings in experiment log

**Criteria to proceed**: Skill correctly identifies all current files and generates accurate two-level tree

### Phase 2: Limited Deployment

- Use skill manually before commits
- Keep manual verification as backup
- Refine based on usage patterns
- Add to workflow documentation

**Criteria to proceed**: 5 successful runs with zero manual corrections needed

### Phase 3: Full Deployment

- Integrate into pre-commit hook
- Make mandatory for all framework commits
- Remove manual verification step
- Document as production tool

**Rollback plan**: Remove from pre-commit hook, revert to manual verification, preserve skill for on-demand use

## Risks and Mitigations

**Risk 1**: Agent LLM misunderstands tree structure and generates incorrect output

- **Likelihood**: Medium (LLMs can be unpredictable with structured data)
- **Impact**: High (incorrect documentation worse than outdated)
- **Mitigation**: Integration tests catch errors, human reviews output before committing

**Risk 2**: Skill becomes too complex and hard to maintain

- **Likelihood**: Low (scope is bounded and clear)
- **Impact**: Medium (violates minimalism principle)
- **Mitigation**: Keep skill simple, resist feature creep, review for bloat regularly

**Risk 3**: Performance degrades as repo grows

- **Likelihood**: Low (repo is small and will stay small)
- **Impact**: Low (slower updates, but still functional)
- **Mitigation**: Monitor performance, optimize if needed (caching, incremental updates)

## Open Questions

1. Should the skill auto-commit changes, or just prepare them for review?
   → **Decision**: Prepare only, human reviews and commits (safer)

2. How should inline comments in tree structure be preserved?
   → **Decision**: Agent uses LLM to intelligently preserve human-written comments

3. Should skill validate content of documentation, or just structure?
   → **Decision**: Structure only (content validation is separate concern)

4. Should detailed tree include file descriptions or just paths?
   → **Decision**: Paths only initially, descriptions are optional human additions

## Notes and Context

This skill supports the broader goal of making README.md the authoritative source of truth. By automating verification and updates, we ensure documentation drift is caught early and fixed quickly.

Related to framework principle: "No incomplete, contradictory, or conflicted documentation in any commit."

---

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably
- [ ] All failure modes addressed
- [ ] Documentation complete (SKILL.md, workflows)
- [ ] Experiment log entry created
- [ ] No documentation conflicts introduced
- [ ] Code follows AXIOMS.md principles
- [ ] Skill tested on actual academicOps repo
- [ ] Two-level tree structure implemented in README.md

## Post-Implementation Review

[After 2 weeks of production use]

**What worked well**:

- [To be completed after deployment]

**What didn't work**:

- [To be completed after deployment]

**What we learned**:

- [To be completed after deployment]

**Recommended changes**:

- [To be completed after deployment]
