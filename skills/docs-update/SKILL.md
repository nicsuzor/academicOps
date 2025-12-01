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

### 4. Generate Concise File Tree with Annotations

**Objective**: Create concise file tree showing only files/directories with meaningful annotations.

**Core Principle**: Only include files that have annotations explaining their purpose. If a file doesn't need an annotation for discoverability, it shouldn't be in the tree.

**High-Level Overview**

Show directory structure with inline annotations for all entries:

```
$AOPS/
├── AXIOMS.md
├── README.md
├── CLAUDE.md
├── BMEM-*.md files
├── pyproject.toml
├── uv.lock
├── setup.sh
├── update_hooks.py
├── __init__.py
├── .gitignore
│
├── .github/workflows/
│   ├── beta-release.yml
│   ├── claude-code-review.yml
│   └── ...
│
├── skills/
│   ├── README.md
│   ├── analyst/
│   │   ├── SKILL.md
│   │   ├── scripts/           # List ALL scripts with annotations
│   │   └── references/        # List ALL references with annotations
│   ├── bmem/
│   ├── docs-update/
│   ├── framework/
│   │   ├── SKILL.md
│   │   ├── scripts/           # CRITICAL: Show scripts to catch misplaced files
│   │   ├── references/
│   │   ├── workflows/
│   │   └── tests/
│   └── ... (expand each skill showing scripts/ and references/)
│
├── hooks/
│   ├── README.md
│   ├── sessionstart_load_axioms.py
│   ├── user_prompt_submit.py
│   └── ... (list each hook file)
│
├── commands/
│   ├── archive-extract.md
│   ├── bmem.md
│   └── ... (list each command file)
│
├── agents/
│   ├── dev.md
│   └── ... (list each agent file)
│
├── experiments/
│   └── ... (list experiment files)
│
├── scripts/
│   └── ... (list script files)
│
├── lib/
│   └── ... (list lib files)
│
├── tests/
│   ├── README.md
│   ├── test_*.py
│   ├── integration/
│   └── tools/
│
└── config/
    └── claude/
```

**Key principles**:
1. **MANDATORY**: Every entry must have an inline comment explaining its purpose - NO EXCEPTIONS
2. **Nested README files**: Must explain what additional documentation they contain (e.g., `README.md  # Skill catalog with usage details`)
3. **SHOW ALL SCRIPTS**: Every `scripts/` directory inside skills MUST be expanded to show individual files with annotations. This catches misplaced files (e.g., task_viz scripts in framework/ instead of tasks/)
4. **SHOW ALL REFERENCES**: Every `references/` directory MUST be expanded - these are critical context documents
5. Group test files (e.g., `test_*.py`) but NOT scripts or references
6. Keep total README.md length under 400 lines (increased to accommodate script visibility)

**AXIOM #22 enforcement**: Information must be DISCOVERABLE, not just exist. An unannotated entry fails this test - agents won't know to read it when needed.

**Annotations must DISTINGUISH, not just describe**. The test: could someone confuse this with another file? If yes, the annotation is useless.

**Example - Good (annotations that distinguish)**:
```
├── commands/
│   ├── task-viz.md          # Launches task-viz agent (just a wrapper)
│   └── meta.md              # Invokes framework skill for strategic decisions
│
├── agents/
│   └── task-viz.md          # Full task visualization logic (bmem → excalidraw)
│
├── skills/excalidraw/
│   ├── SKILL.md
│   └── scripts/
│       ├── task_viz_layout.py   # Force-directed graph layout (networkx)
│       └── generate_task_viz.py # JSON → Excalidraw format conversion
```

**Example - Bad (useless annotations)**:
```
├── commands/
│   ├── task-viz.md          # Task visualization        <-- USELESS: says what, not how/why
│
├── agents/
│   └── task-viz.md          # Task graph visualization  <-- USELESS: same as above, no distinction
```

**The distinction test**: Reading only the annotations, can you tell which file to look at for what purpose? If "task visualization" and "task graph visualization" both appear, your annotations have failed.

### 5. Validate All Cross-References

**Objective**: Ensure all references resolve to existing files. Catch aspirational documentation.

**Check these reference types**:

1. **Wikilinks**: `[[path/to/file.md]]`
2. **Markdown links**: `[text](path/to/file.md)`
3. **See Also references**: "See agents/X.md" or "See [[X]]"
4. **Agent references in commands**: Commands that mention `agents/X.md` or invoke agent types

**Actions**:

```bash
# Find all wikilink references
grep -r '\[\[.*\]\]' $AOPS --include="*.md" -h | grep -o '\[\[[^]]*\]\]' | sort -u

# Find markdown links to local files
grep -r '\]\(\./' $AOPS --include="*.md" -h
grep -r '\]\([a-zA-Z]' $AOPS --include="*.md" -h | grep -v 'http'

# Check commands for agent references
grep -r 'agents/' $AOPS/commands --include="*.md"
grep -r 'See.*\.md' $AOPS --include="*.md"
```

**For each reference found**:
1. Extract the target path
2. Resolve relative to source file location
3. Check if target file exists
4. If missing: flag as **broken reference** (fail-fast)

**Special checks for commands/**:
- If command references `agents/X.md`, verify file exists
- If command invokes a subagent, verify agent definition exists
- Flag any "aspirational" references (documented but not implemented)

**Quality gate**: ALL references must resolve. Broken references = fail immediately.

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
2. Generate new concise file tree with annotations
3. Use Write tool to replace README.md with updated version
4. Preserve all other README.md content (description, contact, bmem section, etc.)
5. Ensure total length stays under 300 lines

**Format**:

```markdown
## academicOps Repository Structure

**Note**: User-specific files...

### High-Level Overview

```
$AOPS/
├── [annotated tree from step 4]
```

[Rest of README sections: Runtime and Debug Locations, bmem, User Data Repository Structure, Installation in Other Projects, Contact, etc.]
```

**Review**: Verify annotations present, total length reasonable, all critical information preserved.

### 8. Final Validation

**Objective**: Verify updated documentation is complete and accurate.

**Checks**:

- [ ] All critical files/directories have annotations
- [ ] No unannotated files in the tree
- [ ] All wikilink references resolve
- [ ] README.md length under 300 lines
- [ ] No conflicts detected in step 6
- [ ] Format consistent and readable
- [ ] All other README sections preserved (Runtime and Debug Locations, bmem, User Data Repository Structure, Installation in Other Projects, Contact)

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
- Broken cross-references found (wikilinks, markdown links, agent refs)
- Aspirational documentation detected (commands referencing non-existent agents)
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

1. **Completeness**: All critical files/directories documented with annotations
2. **Accuracy**: No documented files that don't exist
3. **References**: All wikilinks resolve
4. **Conflicts**: No contradictions detected
5. **Format**: Annotated tree structure present
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
4. Generates annotated tree with inline descriptions
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
