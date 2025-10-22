# Deployment Architecture Specification

**Issue**: #128 - Flat Architecture Implementation
**Status**: Pre-Release Specification (tests define requirements)
**Validation**: `uv run pytest tests/test_deployment_architecture.py`

This document specifies the "flat architecture" deployment model for academicOps. The architecture is validated through executable tests rather than prose specifications.

## Philosophy: Test-Driven Architecture

**Core Principle**: Tests ARE the specification.

- Requirements defined as executable tests
- Tests written FIRST (TDD)
- Most tests will FAIL initially (validates real requirements)
- Pre-release ready when all tests PASS
- Prevents speculation - validates actual behavior

## Architecture Overview

### Design Goals

1. **Path Predictability**: Same folder hierarchy everywhere
2. **Dogfooding**: academicOps installs into itself without conflicts
3. **Zero Duplication**: Framework files symlinked, not copied
4. **Modular Instructions**: /bots/ contains ALL core instructions
5. **Project Overrides**: Projects add only project-specific content
6. **Just-in-Time Loading**: CLAUDE.md provides context-appropriate documentation
7. **Standard Tools**: Piggyback on pre-commit for git hooks
8. **No Confusion**: Everything lives in ONE place

### Predictable Paths Table

| Path | academicOps | Personal Repo | Project Repo | Description |
|------|-------------|---------------|--------------|-------------|
| `/bots/` | ✅ Real (source) | ✅ Real | ✅ Real | Core + project overrides |
| `/bots/agents/` | ✅ Source files | ✅ Personal agents | ✅ Project agents | Agent instructions |
| `/bots/hooks/` | ✅ Source files | Symlink → bot | Symlink → bot | Hook scripts |
| `/.claude/` | ✅ Real | ✅ Real | ✅ Real | Claude Code config |
| `/.claude/settings.json` | ✅ Real | ✅ Real | ✅ Copied from dist/ | Configuration |
| `/.claude/agents/` | Symlink → bots/agents | Symlink → bot | Symlink → bot | Agent discovery |
| `/.claude/commands/` | ✅ Real | Symlink → bot | Symlink → bot | Slash commands |
| `/.claude/skills/` | ✅ Real | Symlink → bot | Symlink → bot | Skills |
| `/data/` | N/A | ✅ Real (private) | N/A | Strategic context |
| `/CLAUDE.md` | ✅ → agents/_CORE.md | ✅ Real | ✅ Real | Entry point |
| `/tests/CLAUDE.md` | ✅ → TESTING.md | N/A | N/A | Test context |
| `/scripts/CLAUDE.md` | ✅ → FAIL-FAST.md | N/A | N/A | Script context |

**Legend**:
- ✅ Real: Actual directory/file
- Symlink → X: Symbolic link to X
- N/A: Not applicable

### Repository Types

**${ACADEMICOPS}** (`/home/nic/src/bot`):
- Framework source code
- /bots/ is REAL (source of truth)
- /.claude/ contains real skills/commands (development)
- Also a valid deployment target (dogfooding)

**${ACADEMICOPS_PERSONAL}** (e.g., `/home/nic/src/writing`):
- User's personal repository
- /bots/ for personal agent overrides
- /data/ for strategic context (private)
- /.claude/ with symlinks to framework

**Project Repos** (e.g., `/home/nic/src/buttermilk`):
- Third-party project repositories
- /bots/ for project-specific overrides
- /.claude/ with symlinks to framework
- Symlinks gitignored (safe to share repo)

## Requirements Validation

Each requirement has executable tests. Run tests to validate architecture:

```bash
# All deployment tests
uv run pytest tests/test_deployment_architecture.py -v

# Dogfooding integration tests (slow)
uv run pytest tests/integration/test_dogfooding.py -v --slow

# Specific requirement class
uv run pytest tests/test_deployment_architecture.py::TestPathPredictability -v
```

### Requirement 1: Path Predictability

**Goal**: Same folder hierarchy across all repository types.

**Test Class**: `TestPathPredictability`

**Validates**:
- ${ACADEMICOPS}/bots/ has standard structure (agents/, hooks/, scripts/)
- ${ACADEMICOPS}/.claude/ matches project installation structure
- Project /bots/ mirrors ${ACADEMICOPS}/bots/ structure

**Success Criteria**:
- All `TestPathPredictability` tests pass
- Developer can predict where files live without documentation

### Requirement 2: Symlink Creation

**Goal**: Framework files symlinked, not duplicated.

**Test Class**: `TestSymlinkCreation`

**Validates**:
- .claude/agents/ is symlink to framework
- .claude/commands/ is symlink to framework
- .claude/skills/ is symlink to framework
- # Scripts accessed via .academicOps/scripts/ is symlink to framework

**Success Criteria**:
- All `TestSymlinkCreation` tests pass
- Changes to framework immediately available in all projects
- No file duplication

**Implementation**: Installation script creates symlinks:

```bash
# Example (pseudocode)
ln -s ${ACADEMICOPS_BOT}/.claude/commands <project>/.claude/commands
ln -s ${ACADEMICOPS_BOT}/.claude/skills <project>/.claude/skills
# Scripts accessed via .academicOps/scripts/ symlink
```

### Requirement 3: Gitignore Coverage

**Goal**: Symlinks gitignored, custom files preserved.

**Test Class**: `TestGitignoreCoverage`

**Validates**:
- dist/.gitignore ignores all framework symlinks
- dist/.gitignore does NOT block custom /bots/ files
- Projects can add custom agent instructions without git conflicts

**Success Criteria**:
- All `TestGitignoreCoverage` tests pass
- Project repos safe to share publicly (no framework files leaked)
- Custom project instructions tracked in git

**Template**: `dist/.gitignore` contains:

```gitignore
# academicOps managed files - DO NOT COMMIT
.claude/settings.json
.claude/agents/
.claude/commands/
.claude/skills/
.claude/settings.local.json

# Symlinked scripts
# Scripts accessed via .academicOps/scripts/

# Local overrides
*.local.*
```

### Requirement 4: Modular Instructions

**Goal**: /bots/ contains ALL core instructions in modular form.

**Test Class**: `TestModularInstructions`

**Validates**:
- bots/agents/ contains core agent files (_CORE.md, trainer.md, etc.)
- bots/hooks/ contains validation scripts (executable)
- Instructions are modular (no duplication)

**Success Criteria**:
- All `TestModularInstructions` tests pass
- Core instructions centralized in ${ACADEMICOPS}/bots/
- Projects reference framework instructions, don't duplicate

### Requirement 5: Project Overrides

**Goal**: Projects add project-specific instructions without modifying framework.

**Test Class**: `TestProjectOverrides`

**Validates**:
- Projects can create custom agents in bots/agents/
- Project files don't conflict with framework symlinks
- Load order: framework → project (both loaded, project second)

**Success Criteria**:
- All `TestProjectOverrides` tests pass
- Projects can customize without forking framework
- Changes to framework don't break project customizations

**Example**: Buttermilk adds `bots/agents/dbt-analyst.md`:

```markdown
# DBT Analyst Agent

Load framework agents:
@_CORE.md
@ANALYST.md

Project-specific DBT patterns:
- Use buttermilk schema conventions
- Load from bots/dbt/profiles.yml
```

### Requirement 6: CLAUDE.md Discovery

**Goal**: Just-in-time documentation loading via CLAUDE.md.

**Test Class**: `TestCLAUDEmdDiscovery`

**Validates**:
- Key directories have CLAUDE.md files
- CLAUDE.md files contain ONLY @ references (no duplication)
- Context loads when working in specific directories

**Success Criteria**:
- All `TestCLAUDEmdDiscovery` tests pass
- Token-efficient (only relevant context loaded)
- Zero content duplication

**Reference**: Issue #120 (implemented in commit b612f85)

**Example**: `bots/CLAUDE.md`

```markdown
# Python Development Context

@../agents/_CORE.md
@../docs/_CHUNKS/FAIL-FAST.md
@../.claude/skills/python-dev/SKILL.md

## Key Principles
- Fail-fast: No defaults
- Type safety: Use Pydantic
```

### Requirement 7: Script Invocation

**Goal**: Scripts accessible via symlink at # Scripts accessed via .academicOps/scripts/.

**Test Class**: `TestScriptInvocation`

**Validates**:
- # Scripts accessed via .academicOps/scripts/ is symlink to framework scripts
- Scripts are executable via symlink
- Scripts invokable from project without absolute paths

**Success Criteria**:
- All `TestScriptInvocation` tests pass
- Projects invoke scripts via `# Scripts accessed via .academicOps/scripts/script.sh`
- No hardcoded paths to ${ACADEMICOPS}

### Requirement 8: Pre-commit Integration

**Goal**: Use pre-commit for git hooks (no custom scripts).

**Test Class**: `TestPreCommitIntegration`

**Validates**:
- .pre-commit-config.yaml exists
- No custom git hooks (only pre-commit managed)
- Hooks installed via `pre-commit install`

**Success Criteria**:
- All `TestPreCommitIntegration` tests pass
- Standard tool used (not custom scripts)
- Maintainable by community

**Reference**: Issue #130 (custom hooks eliminated)

### Requirement 9: Dogfooding

**Goal**: academicOps can install into itself without conflicts.

**Test Class**: `TestDogfooding` + `TestDogfoodingInstallation`

**Validates**:
- ${ACADEMICOPS}/bots/ is real (not symlink)
- ${ACADEMICOPS}/.claude/ matches project structure
- Development files coexist with deployment files
- Installation script runs successfully in ${ACADEMICOPS}
- Hooks execute correctly in ${ACADEMICOPS}

**Success Criteria**:
- All `TestDogfooding*` tests pass
- Running Claude in ${ACADEMICOPS} identical to running in project
- No conflicts between source code and deployment structure

## Installation Process

### For New Project Repos

```bash
# 1. Navigate to project
cd /path/to/project

# 2. Run installation script
${ACADEMICOPS_BOT}/scripts/setup_academicops.sh

# 3. Verify installation
${ACADEMICOPS_BOT}/# Scripts accessed via .academicOps/scripts/check_instruction_orphans.py

# 4. Customize (optional)
# Add project-specific agents to bots/agents/
# Add CLAUDE.md files for just-in-time context
```

### For ${ACADEMICOPS} Itself (Dogfooding)

```bash
# 1. Navigate to academicOps
cd ${ACADEMICOPS_BOT}

# 2. Run installation on itself
./scripts/setup_academicops.sh .

# 3. Verify no conflicts
git status  # Should not show unexpected changes

# 4. Test hooks work
uv run python bots/hooks/load_instructions.py _CORE.md
```

### For ${ACADEMICOPS_PERSONAL}

```bash
# 1. Navigate to personal repo
cd ${ACADEMICOPS_PERSONAL}

# 2. Run installation
${ACADEMICOPS_BOT}/scripts/setup_academicops.sh

# 3. Add personal customizations
# - bots/agents/INSTRUCTIONS.md (personal preferences)
# - data/ (strategic context, gitignored)

# 4. Verify privacy
git status  # Symlinks should be ignored
```

## Validation Workflow

### Pre-Release Checklist

Before declaring architecture complete:

1. **Run full test suite**:
   ```bash
   uv run pytest tests/test_deployment_architecture.py -v
   uv run pytest tests/integration/test_dogfooding.py -v --slow
   ```

2. **All tests PASS**: No failures, no skips

3. **Manual validation**:
   - Install in fresh project repo
   - Verify hooks execute
   - Verify agents load
   - Verify git operations work

4. **Documentation complete**:
   - This file explains all requirements
   - Each requirement references validating test
   - Troubleshooting guide exists

5. **User acceptance**:
   - User confirms architecture meets needs
   - Edge cases documented

### Continuous Validation

After pre-release, validate architecture doesn't degrade:

```bash
# Add to pre-commit hooks
- repo: local
  hooks:
    - id: deployment-architecture
      name: Validate Deployment Architecture
      entry: uv run pytest tests/test_deployment_architecture.py -x
      language: system
      pass_filenames: false
```

## Troubleshooting

### Tests Failing: Symlinks Missing

**Symptom**: `TestSymlinkCreation` tests fail

**Cause**: Installation script not creating symlinks

**Fix**:
1. Check installation script exists: `scripts/setup_academicops.sh`
2. Verify script creates symlinks (not copies)
3. Check symlink targets are correct

### Tests Failing: Hooks Not Executable

**Symptom**: `TestModularInstructions` fails on executable check

**Cause**: Hook scripts not marked executable in git

**Fix**:
```bash
chmod +x bots/hooks/*.py
git update-index --chmod=+x bots/hooks/*.py
git commit -m "fix: Make hooks executable"
```

### Tests Failing: CLAUDE.md Missing

**Symptom**: `TestCLAUDEmdDiscovery` tests fail

**Cause**: CLAUDE.md files not created in directories

**Fix**: Implement Issue #120 (already done in commit b612f85)

### Tests Failing: Dogfooding Conflicts

**Symptom**: `TestDogfooding` fails with conflicts

**Cause**: Development files conflicting with deployment structure

**Fix**:
1. Ensure /bots/ in ${ACADEMICOPS} is real (not symlink)
2. Ensure .claude/ structure doesn't duplicate development files
3. Update .gitignore to prevent tracking symlinks

## Future Enhancements

### Validation Hooks

Add PreToolUse hook to verify deployment architecture:

```python
# bots/hooks/validate_deployment.py
def check_deployment_structure(project_root: Path) -> bool:
    """Validate deployment structure matches specification."""
    required = [
        "bots/agents",
        ".claude/settings.json",
    ]

    for path in required:
        if not (project_root / path).exists():
            return False

    return True
```

### Auto-Repair

Installation script with `--repair` flag to fix broken installations:

```bash
./scripts/setup_academicops.sh --repair /path/to/project
```

### Migration Script

For upgrading old installations to new architecture:

```bash
./scripts/migrate_to_flat_architecture.sh /path/to/project
```

## Success Metrics

**Pre-Release Ready When**:
- [ ] All deployment architecture tests pass
- [ ] All dogfooding tests pass
- [ ] Manual validation in 3+ project repos successful
- [ ] Documentation complete (this file)
- [ ] User acceptance confirmed

**Ongoing Health**:
- Deployment tests run in CI
- Zero test failures for 1+ month
- Installation script works in all target repos
- No user reports of architecture confusion

## Related Issues

- #128: Flat Architecture Implementation (this issue)
- #120: CLAUDE.md just-in-time loading (implemented)
- #121: Hooks environment variables (solved)
- #131: Commands symlink (solved)
- #111: Modular documentation architecture
- #129: Git hook conflicts (solved)
- #130: Custom hook delegation (solved)

## References

**Tests**:
- `tests/test_deployment_architecture.py` - Deployment validation
- `tests/integration/test_dogfooding.py` - Self-installation validation

**Templates**:
- `dist/.claude/settings.json` - Project settings template
- `dist/.gitignore` - Project gitignore template
- `dist/INSTRUCTIONS.md` - Project instructions template

**Scripts**:
- `scripts/setup_academicops.sh` - Installation script
- `scripts/check_instruction_orphans.py` - Validation utility

## Future Extensibility

Currently, project repos contain only `/bots/agents/` for instruction file overrides. The framework provides commands and skills via `.claude/` symlinks.

**Future possibilities** (not implemented yet):
- `/bots/commands/` - Project-specific custom commands
- `/bots/skills/` - Project-specific custom skills

These extension points may be added in future versions when the need arises. For now, the simplified structure focuses on the most useful customization point: agent instructions.
