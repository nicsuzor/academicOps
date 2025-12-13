---
name: cleanup
description: Check knowledge base compliance against framework rules. Report and fix non-compliant files.
allowed-tools: Read,Grep,Glob,Edit,Bash,mcp__bmem__search_notes,mcp__bmem__read_note
version: 1.0.0
permalink: skills-cleanup-skill
---

# Cleanup Skill

**When to invoke**: To verify `$ACA_DATA/` files comply with framework rules.

**What it does**: Scans directories, identifies non-compliant files, reports/fixes them.

**Invocation**: Via `framework` skill delegation only (requires `FRAMEWORK SKILL CHECKED` token).

## Compliance Rules

Source: `framework` skill → Framework Project Data section

### `$ACA_DATA/projects/aops/` Structure

| Location | Allowed Content |
|----------|----------------|
| `aops.md` | Project index (folder naming convention) |
| `VISION.md` | Goals - edit in place |
| `ROADMAP.md` | Progression - edit in place |
| `specs/` | Design docs with status frontmatter |
| `experiments/` | Hypothesis → results, date-prefixed |
| `learning/` | Patterns from experience, thematic |
| `decisions/` | Architectural choices, immutable |
| `bugs/` | Bug investigations, delete when fixed |
| `qa/` | Verification reports, delete when resolved |

### Prohibited

- Root-level files (except aops.md, VISION.md, ROADMAP.md)
- Files without clear category
- Duplicate content
- Index/Summary files
- Session detritus

## Workflow

### 1. Scan

```bash
# List all files in target directory
find $TARGET -type f -name "*.md"
```

### 2. Categorize Each File

For each file, determine:
- **Compliant**: In allowed location per rules above
- **Relocatable**: Has clear category, wrong location → move
- **Extractable**: Contains valuable info but wrong format → extract to bmem, delete file
- **Deletable**: No value, session detritus → delete

### 3. Report

Output format:
```
## Compliance Report: [directory]

### Compliant (N files)
- path/file.md

### Action Required (N files)

| File | Issue | Recommendation |
|------|-------|----------------|
| path/file.md | Root-level working doc | Extract to bmem → delete |
```

### 4. Execute (with confirmation)

For each non-compliant file:
1. Show file content summary
2. Propose action (move/extract/delete)
3. Execute after user confirms

## Before Deleting

Always check:
1. **Is there unique value?** → Extract to bmem first
2. **Is it referenced elsewhere?** → Update references
3. **Git history preserves it** → Safe to delete

## Extraction Pattern

When extracting value before deletion:

```
FRAMEWORK SKILL CHECKED

Categorical Rule: Valuable information must be preserved in bmem before file deletion
Skill: bmem
Operation: write_note with extracted observations
Scope: [source file path]
```

## When Done

Report summary:
- Files scanned
- Compliant count
- Actions taken
- Remaining issues (if any)
