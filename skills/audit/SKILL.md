---
name: audit
description: Comprehensive framework governance audit - structure checking, justification checking, and index file updates.
allowed-tools: Read,Glob,Grep,Edit,Write,Bash
version: 2.0.0
permalink: skills-audit
---

# Framework Audit Skill

Comprehensive governance audit for the academicOps framework. Performs structure checking, justification checking, and updates index files in one pass.

## Workflow

### Phase 1: Structure Audit

Compare filesystem to documentation:

1. **Scan filesystem**: `find $AOPS -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" | sort`
2. **Compare to INDEX.md**: Flag missing or extra entries
3. **Check cross-references**: Verify `→` references point to existing files
4. **Find broken wikilinks**: Grep for `[[...]]` patterns, validate targets exist

### Phase 2: Justification Audit

For each significant file in `$AOPS/`:

1. **Search specs**: Grep `$ACA_DATA/projects/aops/specs/` for references to this file
2. **Check core docs**: Is it mentioned in JIT-INJECTION.md, README.md, INDEX.md?
3. **Classify**:
   - **Justified**: Spec explicitly mandates this file
   - **Implicit**: Referenced in docs but no dedicated spec
   - **Orphan**: No spec or doc reference found

**Scope**: Focus on top-level files and skill/hook/command/agent directories. Skip:
- `__pycache__/`, `.git/`, `node_modules/`
- Individual files within skills (specs cover skill, not each file inside)
- Test files, assets, fonts

### Phase 3: Updates

1. **Fix INDEX.md**: Add missing entries, remove stale entries
2. **Fix README.md**: Update skill/command/hook tables
3. **Report orphans**: Flag for human review (do NOT auto-delete)

## Report Format

Output a structured report:

```
## Audit Report

### Structure Issues Found
- Missing from INDEX.md: skills/foo/
- Extra in INDEX.md: skills/deleted/ (no longer exists)
- Broken wikilinks: [[nonexistent.md]] in X.md

### Justification Status

**Justified** (N files) - spec exists:
- AXIOMS.md → specs/meta-framework.md
- hooks/prompt_router.py → specs/intent-router-spec.md

**Implicit** (N files) - in docs, no dedicated spec:
- FRAMEWORK.md → JIT-INJECTION.md
- README.md → framework convention

**Orphan candidates** (N files) - no reference found:
- docs/OLD-FILE.md

### Actions Taken
- Added skills/foo/ to INDEX.md line 45
- Updated README.md commands table

### Requires Human Review
- Orphan: docs/OLD-FILE.md - delete or create spec?
```

## README.md Structure Target

Brief overview (~100-150 lines):

```markdown
# academicOps Framework

Academic support framework for Claude Code. Minimal, fight bloat.

## Quick Start
[paths, principles links]

## Commands
[table: command | purpose]

## Skills
[table: skill | purpose]

## Hooks
[table: hook | trigger | purpose]

## Agents
[table: agent | purpose]
```

## INDEX.md Structure Target

Complete file-to-function mapping:

```markdown
# Framework Index

## File Tree
$AOPS/
├── AXIOMS.md                # Inviolable principles
├── [complete annotated tree...]

## Cross-References
### Command → Skill
### Skill → Skill
### Agent → Skill
```

## Validation Criteria

- README.md < 200 lines
- INDEX.md has every directory
- All `→` references resolve
- No broken `[[wikilinks]]`
- Orphan count reported (0 ideal)
