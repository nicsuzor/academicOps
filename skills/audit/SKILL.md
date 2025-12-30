---
name: audit
description: Comprehensive framework governance audit - structure checking, justification checking, and index file updates.
allowed-tools: Read,Glob,Grep,Edit,Write,Bash
version: 3.0.0
permalink: skills-audit
---

# Framework Audit Skill

Comprehensive governance audit for the academicOps framework.

## Workflow

### Phase 1: Structure Audit

Compare filesystem to documentation:

1. **Scan filesystem**: `find $AOPS -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" | sort`
2. **Compare to INDEX.md**: Flag missing or extra entries
3. **Check cross-references**: Verify `→` references point to existing files
4. **Find broken wikilinks**: Grep for `[[...]]` patterns, validate targets exist

### Phase 2: Reference Graph & Link Audit

Build reference graph and check linking conventions:

```bash
# Generate graph
PYTHONPATH=$AOPS uv run python $AOPS/skills/audit/scripts/build_reference_map.py

# Find orphans and violations
PYTHONPATH=$AOPS uv run python $AOPS/skills/audit/scripts/find_orphans.py
```

**Linking rules to enforce**:
- Skills via invocation (`Skill(skill="x")`), not file paths
- No backward links (children → parent)
- Parents must reference children
- Use wikilinks, not backticks for graph connectivity
- Full relative paths in wikilinks

### Phase 3: Skill Content Audit

For each `$AOPS/skills/*/SKILL.md`:

1. **Size check**: Must be <500 lines
2. **Actionability test**: Each section must tell agents WHAT TO DO
3. **Content separation violations**:
   - ❌ Multi-paragraph "why" → move to spec
   - ❌ Historical context → delete
   - ❌ Reference material >20 lines → move to `references/`

### Phase 4: Justification Audit

For each significant file in `$AOPS/`:

1. **Search specs**: Grep `$AOPS/specs/` for references
2. **Check core docs**: JIT-INJECTION.md, README.md, INDEX.md
3. **Classify**: Justified / Implicit / Orphan

**Skip**: `__pycache__/`, `.git/`, individual files within skills, tests, assets

### Phase 5: Documentation Accuracy

Verify `docs/execution-flow.md` reflects actual hook architecture:

1. Parse Mermaid for hook names
2. Compare to hooks/router.py dispatch mappings
3. Compare to settings.json hook events
4. Flag drift

### Phase 6: Updates

1. **Fix INDEX.md**: Add missing, remove stale
2. **Fix README.md**: Update tables
3. **Report orphans**: Flag for human review (do NOT auto-delete)
4. **Report violations**: List with file:line refs

## Report Format

Output a structured report:

```
## Audit Report

### Structure Issues
- Missing from INDEX.md: skills/foo/
- Broken wikilinks: [[nonexistent.md]] in X.md

### Skill Content Violations
- skills/foo/SKILL.md:45-67 - explanatory content (move to spec)
- skills/bar/SKILL.md - 623 lines (>500 limit)

### Execution Flow Drift
- Hook in code, missing from diagram: unified_logger.py (PostToolUse)
- Hook in diagram, not in router.py: old_hook.py

### Justification Status

**Justified** (N files) - spec exists:
- AXIOMS.md → specs/meta-framework.md
- hooks/user_prompt_submit.py → specs/prompt-enricher.md

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
- All SKILL.md files < 500 lines
- No explanatory content in SKILL.md files
- Orphan count reported (0 ideal)
- `docs/execution-flow.md` matches hooks/router.py dispatch table
