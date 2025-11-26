# Documentation Update Skill

Update and verify framework documentation, particularly README.md file tree structure. Ensures documentation stays authoritative and conflict-free.

## Overview

This skill verifies that README.md accurately reflects the current repository structure and detects documentation conflicts. It ensures every file in the repository has a corresponding entry in the documentation.

**When to use**:
- Before committing framework changes
- After adding new files (skills, hooks, commands, scripts)
- When documentation drift is suspected
- To generate updated file tree structure
- To detect conflicts between documentation files

**Critical**: This skill enforces that README.md is the single source of truth for repository structure.

## Workflow

### 1. Scan Repository Structure

**Objective**: Discover all files in the academicOps repository.

**Actions**:

```bash
# Get all files in the repository (excluding .git and common ignore patterns)
find $AOPS -type f \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*/.pytest_cache/*" \
  -not -path "*/venv/*" \
  -not -name "*.pyc" \
  | sort
```

**Expected output**: Complete list of all files in repository with absolute paths.

### 2. Read Current README.md

**Objective**: Understand currently documented structure.

**Actions**:

1. Read README.md file
2. Identify the file tree section(s)
3. Extract documented paths and structure
4. Note any inline comments or descriptions (must preserve these)

**Critical**: Preserve all human-written comments and descriptions when updating.

### 3. Compare Actual vs Documented

**Objective**: Identify discrepancies between filesystem and documentation.

**Analysis**:

For each file found in step 1:
- Is it documented in README.md?
- If documented, is the path correct?
- Are there obsolete entries (documented but don't exist)?

**Report**:
- Missing entries: Files that exist but aren't documented
- Extra entries: Documented files that don't exist
- Path mismatches: Files at different location than documented

**Quality gate**: If discrepancies found, document them clearly before proceeding.

### 4. Generate Two-Level File Tree

**Objective**: Create updated file tree with two levels of detail.

**Level 1: High-Level Overview**

Show main directory structure but NOT contents of subdirectories:

```
$AOPS/
├── AXIOMS.md
├── README.md
├── CLAUDE.md
├── skills/              # Agent skills (subdirectories below)
├── hooks/               # Lifecycle automation (subdirectories below)
├── commands/            # Slash commands (subdirectories below)
├── experiments/         # Temporary experiments
├── scripts/             # Deployment scripts
├── lib/                 # Shared utilities
├── tests/               # Integration tests (subdirectories below)
├── agents/              # Agentic workflows (future)
└── config/              # Configuration files
```

**Level 2: Detailed Breakdown**

Show ALL files organized by category:

**Skills** (`skills/`):
- List each skill directory
- List all files within each skill (SKILL.md, README.md, scripts/, workflows/, etc.)
- Include files that skills reference (via wikilinks or imports)

**Hooks** (`hooks/`):
- List each hook file
- List prompts/ directory contents
- Include README.md

**Commands** (`commands/`):
- List each command file (.md files)

**Tests** (`tests/`):
- List test files
- List integration/ subdirectory contents
- Include conftest.py and supporting files

**Root-level files**:
- All markdown files at root
- Configuration files
- Other important files

**Scripts and Lib**:
- List scripts/ contents
- List lib/ contents

**Format**: Use consistent tree structure with clear hierarchy. Preserve inline comments from current README.md.

### 5. Validate References

**Objective**: Ensure all wikilink-style references resolve to existing files.

**Actions**:

```bash
# Find all wikilink references in documentation
grep -r '\[\[.*\.md\]\]' $AOPS --include="*.md" -h | \
  grep -o '\[\[.*\.md\]\]' | \
  sort -u
```

For each reference found:
1. Extract the file path
2. Check if file exists
3. Report broken references

**Quality gate**: All references must resolve. Fail-fast if broken references found.

### 6. Detect Documentation Conflicts

**Objective**: Find contradictory information across documentation files.

**Check for**:

1. **Duplication of principles**:
   - Grep for key AXIOMS.md concepts in other files
   - Flag multi-line explanations after references (SSoT violation)

2. **Conflicting instructions**:
   - Check CLAUDE.md vs README.md for contradictions
   - Verify skill descriptions match skill SKILL.md files

3. **Outdated references**:
   - Check for references to moved/deleted files
   - Verify directory structure comments match reality

**Actions**:

```bash
# Find potential AXIOMS duplication
grep -r "fail-fast\|single source\|DRY\|explicit" $AOPS --include="*.md" \
  -A 3 -B 1 | \
  grep -v "AXIOMS.md"

# Find wikilink references
grep -r '\[\[.*\]\]' $AOPS --include="*.md"

# Find multi-line summaries after references (potential bloat)
# (Manual review - look for reference followed by multi-line explanation)
```

**Quality gate**: No conflicts allowed in commits to dev branch.

### 7. Update README.md

**Objective**: Apply corrected file tree to README.md.

**Actions**:

1. Create backup of current README.md content
2. Generate new file tree sections (Level 1 and Level 2)
3. Use Edit tool to replace old tree with new tree
4. Preserve all other README.md content (description, contact, etc.)
5. Preserve human-written inline comments in tree

**Format**:

```markdown
## academicOps Repository Structure

**Note**: User-specific files...

### High-Level Overview

```
$AOPS/
├── [high-level tree from step 4]
```

### Detailed File Breakdown

#### Skills

```
skills/
├── framework/
│   ├── SKILL.md
│   ├── workflows/
│   │   ├── 01-design-new-component.md
│   │   └── ...
│   └── ...
├── analyst/
│   └── SKILL.md
└── ...
```

[Continue for hooks/, commands/, tests/, etc.]
```

**Review**: Show diff before applying. Verify all files included, structure correct, comments preserved.

### 8. Final Validation

**Objective**: Verify updated documentation is complete and accurate.

**Checks**:

- [ ] All files from step 1 appear in updated README.md
- [ ] No extra entries (documented but don't exist)
- [ ] All wikilink references resolve
- [ ] Human-written comments preserved
- [ ] Two-level structure present and correct
- [ ] No conflicts detected in step 6
- [ ] Format consistent and readable

**Output**: Report of verification status:
- ✅ All files documented
- ✅ All references valid
- ✅ No conflicts detected
- ✅ README.md updated successfully

OR

- ❌ Issues found: [detailed list]
- Action required: [specific fixes needed]

## Error Handling

**Fail-fast cases** (halt immediately):

- $AOPS environment variable not set
- README.md doesn't exist or unreadable
- Unable to write to README.md
- Broken wikilink references found
- Documentation conflicts detected

**Report format**:

```
❌ DOCUMENTATION UPDATE FAILED

Reason: [specific error]

Details:
- [Error detail 1]
- [Error detail 2]

Required action:
[Clear next step to resolve]
```

**Recovery**:
- All changes are in memory until final write
- Original README.md preserved until verification complete
- User can reject changes and investigate issues

## Quality Gates

Before completing skill execution:

1. **Completeness**: Every file in repo has tree entry
2. **Accuracy**: No documented files that don't exist
3. **References**: All wikilinks resolve
4. **Conflicts**: No contradictions detected
5. **Format**: Two-level tree structure present
6. **Preservation**: Human comments retained

**All gates must pass**. If any fail, report and halt without writing changes.

## Integration with Framework Workflows

**Before commits**: Run this skill to verify documentation current

**After adding files**: Run to update file tree

**When refactoring**: Run to catch moved/deleted file references

**Weekly check**: Run as part of framework health monitoring

## Example Session

**User**: "Update the framework documentation"

**Agent**:
1. Scans repository → finds 127 files
2. Reads README.md → extracts documented structure
3. Compares → finds 3 missing entries (new skill files)
4. Generates two-level tree
5. Validates references → all resolve
6. Checks conflicts → none found
7. Updates README.md with new tree
8. Reports: "✅ Documentation updated. Added 3 new entries to README.md file tree."

## Maintenance Notes

**Known limitations**:
- Assumes specific README.md structure (tree in fenced code blocks)
- Manual review recommended for first use on new repository
- Large repositories (>1000 files) may need optimization

**Future improvements**:
- Semantic conflict detection (understanding contradictions, not just duplication)
- Auto-generate file descriptions from docstrings/comments
- Track documentation health metrics over time
- Integration with pre-commit hooks

**Dependencies**: None beyond standard Claude Code tools (Read, Write, Edit, Bash, Grep, Glob)

## See Also

- [[workflows/04-monitor-prevent-bloat.md]] - Preventing documentation bloat
- [[workflows/02-debug-framework-issue.md]] - Debugging documentation conflicts
- Specification: [[specs/docs-update-skill.md]]
