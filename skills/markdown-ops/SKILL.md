---
name: markdown-ops
description: This skill should be used for every operation that writes or edits markdown files. Enforces academicOps structure rules and Basic Memory syntax compliance. Use when creating, editing, or moving markdown files in either aOps framework or Basic Memory projects.
license: Apache 2.0
permalink: aops/skills/markdown-ops/skill
---

# Markdown Operations

## Framework Context

@resources/SKILL-PRIMER.md
@resources/AXIOMS.md
@resources/INFRASTRUCTURE.md

## Overview

Guide all markdown file operations to ensure:
1. Files are created in the correct location (aOps structure rules)
2. Files follow appropriate syntax (Basic Memory vs regular markdown)
3. Anti-bloat principles are enforced
4. Templates are used for standardized file types

This skill provides decision trees, structure rules, and syntax specifications to ensure compliance across all markdown operations.

## When to Use This Skill

Use markdown-ops for:

- **Creating markdown files** in aOps repo or Basic Memory projects
- **Editing existing markdown** to ensure format compliance
- **Moving/reorganizing** markdown files
- **Converting regular markdown** to Basic Memory format
- **Validating structure** before writing files
- **Choosing templates** for standardized file types

**Trigger examples**:
- "Create experiment log for X changes"
- "Document this in Basic Memory"
- "Add new agent/skill/command to aOps"
- "Convert this markdown to Basic Memory format"
- "Where should I put this documentation?"

## Workflow Decision Tree

### Step 1: Identify Target Repository

```
Q: Which repository is the target?

A. academicOps framework ($ACADEMICOPS)
   → Go to Step 2A: aOps Structure Rules

B. Basic Memory project (writing, research, etc.)
   → Go to Step 2B: Basic Memory Syntax

C. Other project repository
   → Use regular markdown, no special structure
```

### Step 2A: aOps Structure Rules

**Consult**: `@references/aops-structure.md` for complete directory structure

**Quick reference**:

| File Type | Location | Template |
|-----------|----------|----------|
| Experiment log | `experiments/YYYY-MM-DD_name.md` | `@assets/experiment-template.md` |
| Agent | `agents/AGENT-NAME.md` | YAML frontmatter + workflow |
| Skill | `skills/skill-name/SKILL.md` | Use skill-creator skill |
| Command | `commands/command-name.md` | YAML frontmatter + skill invocation |
| Chunk | `chunks/CONCEPT.md` | DRY single source |
| Framework doc | `docs/filename.md` | Regular markdown |
| Agent dev doc | `docs/bots/filename.md` | Regular markdown |
| Domain doc | `docs/_CHUNKS/DOMAIN.md` | Regular markdown |
| Audit | `docs/AUDIT.md` | Current state tracking |
| Hook | `hooks/hookname.py` | Python with docstring |
| Script | `scripts/scriptname.py` | Python/Bash |

**Anti-bloat checklist** (before creating):

- [ ] Is there existing content to reference instead?
- [ ] Does this duplicate chunks/ or other files?
- [ ] Can this be consolidated with existing documentation?
- [ ] Is this the minimal effective location?
- [ ] Will file stay under limits? (Skills <300, Agents <500)

**Critical rule**: ALL changes to aOps framework REQUIRE experiment log in `experiments/`.

### Step 2B: Basic Memory Syntax

**Consult**: `@references/bmem-syntax.md` for complete specification

**Quick checklist**:

1. **YAML frontmatter** (required):
   - `title`: Entity name (used in `[[references]]`)
   - `permalink`: URL-friendly slug
   - `type`: note/person/project/meeting/decision/spec
   - `tags`: Optional array

2. **Content structure**:
   - `# Title` (matches frontmatter)
   - `## Context` (1-3 sentence overview)
   - `## Observations` (categorized facts with tags)
   - `## Relations` (entity links)

3. **Observation syntax**:
   - `- [category] content #tag1 #tag2`
   - Common categories: fact, idea, decision, technique, requirement, insight, problem, solution, question

4. **Relation syntax**:
   - `- relation_type [[Target Entity]]`
   - Common relations: relates_to, implements, requires, extends, part_of

**Use template**: `@assets/bmem-template.md` for new Basic Memory files

### Step 3: File Creation

**For aOps framework files**:

1. Verify location using `@references/aops-structure.md` decision tree
2. Use appropriate template if available:
   - Experiments: `@assets/experiment-template.md`
   - Agents/Skills/Commands: Use skill-creator or follow existing patterns
3. Enforce anti-bloat limits:
   - Skills: <300 lines
   - Agents: <500 lines
   - >10 lines addition: Requires GitHub issue + approval
4. Add resources/ symlinks for skills (MANDATORY)
5. Create experiment log documenting the change

**For Basic Memory files**:

1. Start with `@assets/bmem-template.md`
2. Fill YAML frontmatter:
   - title: Human-readable entity name
   - permalink: lowercase-with-hyphens
   - type: note (or person/project/meeting/decision/spec)
   - tags: Relevant categorization tags
3. Add Context section (1-3 sentences)
4. Convert prose to Observations:
   - Extract atomic facts
   - Categorize each observation
   - Add relevant tags
5. Add Relations:
   - Identify connections to other entities
   - Use `[[Entity Title]]` syntax
   - Choose appropriate relation type
6. Save in appropriate folder within Basic Memory project

**For regular markdown** (non-aOps, non-Basic Memory):

Use standard markdown without special requirements.

## File Editing Operations

### Editing Existing Files

**For aOps files**:

1. Read current file first
2. Check if edit violates anti-bloat limits
3. Before adding >5 lines:
   - [ ] Tried scripts/hooks/config first?
   - [ ] Checked for existing content to reference?
   - [ ] Verified not repeating chunks/ or _CORE.md?
   - [ ] Using bullet points, not prose?
   - [ ] Instructions specific, not vague?
4. If adding >10 lines: STOP, create GitHub issue
5. Create experiment log documenting the change

**For Basic Memory files**:

1. Read current file first
2. Preserve YAML frontmatter structure
3. Maintain semantic structure (Context/Observations/Relations)
4. Add new observations with proper categories and tags
5. Add new relations using exact entity titles
6. Update `updated` timestamp in frontmatter (optional)

### Converting Regular Markdown to Basic Memory

**Process**:

1. Read original markdown file
2. Extract key information:
   - Title
   - Main concepts
   - Facts and decisions
   - References to other concepts
3. Start with `@assets/bmem-template.md`
4. Fill frontmatter:
   - title: Original title or descriptive name
   - permalink: URL-friendly version
   - type: Choose appropriate type
   - tags: Extract from content
5. Convert prose to observations:
   - Break down paragraphs into atomic facts
   - Assign categories (fact/idea/decision/etc.)
   - Add tags for discoverability
6. Extract relations:
   - Identify mentioned concepts/documents
   - Create explicit `[[Entity Title]]` links
   - Choose appropriate relation type
7. Save in Basic Memory project

**Example conversion**:

```markdown
# Before (regular markdown)
The fail-fast philosophy means scripts and hooks are preferred
over instructions. This ensures reliability through automation.

# After (Basic Memory)
---
title: Fail-Fast Philosophy
permalink: fail-fast-philosophy
tags: [architecture, reliability, principles]
type: note
---

# Fail-Fast Philosophy

## Context
Architectural principle prioritizing automated enforcement over documentation.

## Observations
- [principle] Fail-fast philosophy: scripts > hooks > config > instructions #architecture
- [rationale] Ensures reliability through automation rather than documentation #design-decisions
- [technique] Move enforcement up hierarchy when agents consistently violate instructions #enforcement

## Relations
- part_of [[academicOps Framework]]
- implements [[AXIOMS]]
- relates_to [[Anti-Bloat Principles]]
```

## Moving and Reorganizing Files

### Within aOps Framework

1. Check if move violates structure rules (`@references/aops-structure.md`)
2. Update all references to moved file:
   - Internal links in other markdown files
   - Symlinks (especially for chunks/)
   - CLAUDE.md references
   - Instruction tree (regenerate with `python scripts/generate_instruction_tree.py`)
3. Create experiment log documenting the reorganization
4. Commit changes via git-commit skill

### Within Basic Memory

1. Use Basic Memory MCP tool: `move_note(identifier, destination_path, project)`
2. Tool automatically updates:
   - Database records
   - File system location
   - Internal links and references
3. Verify move completed successfully

## Templates Reference

### Experiment Log Template

Location: `@assets/experiment-template.md`

**When to use**: MANDATORY for all aOps framework changes

**Structure**:
- Metadata (Date, Issue, Commit, Model)
- Context (Background)
- Hypothesis (Expected outcome)
- Changes Made (Specific modifications)
- Success Criteria (Measurement metrics)
- Results (Actual outcome)
- Outcome (Success/Failure/Partial)
- Notes (Additional observations)

### Basic Memory Template

Location: `@assets/bmem-template.md`

**When to use**: Creating new entities in Basic Memory projects

**Structure**:
- YAML frontmatter (title, permalink, tags, type)
- Title heading
- Context section
- Observations section (with category examples)
- Relations section (with relation type examples)

## Critical Rules

**NEVER**:
- Create aOps files without consulting structure rules
- Create Basic Memory files without YAML frontmatter
- Add >10 lines to aOps files without GitHub issue
- Duplicate chunks/ content in other files
- Create files without experiment log (for aOps changes)
- Mix Basic Memory syntax with aOps framework files (separate repos)
- Forget resources/ symlinks for new skills

**ALWAYS**:
- Use templates for standardized file types
- Validate location before creating files
- Check anti-bloat limits before edits
- Create experiment logs for aOps changes
- Use proper observation categories in Basic Memory
- Reference entities exactly with `[[Entity Title]]` syntax
- Preserve semantic structure when editing

## Quick Reference

**Decision matrix**:

```
Need to create markdown file
    ↓
Is it in $ACADEMICOPS?
    YES → Use aOps structure rules (@references/aops-structure.md)
          Check anti-bloat limits
          Use experiment template if documenting changes
          Create experiment log for framework changes
    NO ↓
Is it in Basic Memory project?
    YES → Use Basic Memory syntax (@references/bmem-syntax.md)
          Start with bmem-template.md
          Follow frontmatter/observations/relations structure
    NO ↓
Regular markdown (no special requirements)
```

**Common operations**:

| Operation | aOps | Basic Memory |
|-----------|------|--------------|
| Create file | Check structure rules | Use bmem-template.md |
| Edit file | Check anti-bloat limits | Preserve semantic structure |
| Move file | Update references + instruction tree | Use move_note() tool |
| Validate | Check line count + DRY | Check frontmatter + syntax |
| Document change | Create experiment log | Update observations |
