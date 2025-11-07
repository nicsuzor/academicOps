---
name: bmem-ops
description: Enforce Basic Memory syntax across all markdown files in knowledge base. Converts frontmatter, adds observations, enforces link syntax for aops and $ACADEMICOPS_PERSONAL repositories.
license: Apache 2.0
permalink: aops/skills/bmem-ops/skill
---

# Basic Memory Operations

## Framework Context

@resources/AXIOMS.md

## Overview

Ensure all markdown files in the knowledge base follow Basic Memory syntax. This skill converts regular markdown to Basic Memory format, validates existing files, and maintains semantic structure across the entire knowledge base.

**Scope**: ALL markdown files in `$ACADEMICOPS` and `$ACADEMICOPS_PERSONAL` repositories (excluding specific config files).

## When to Use This Skill

Use bmem-ops when:

- **Creating markdown files** in knowledge base repos
- **Editing existing markdown** to add/enforce Basic Memory syntax
- **Converting regular markdown** to semantic format
- **Validating frontmatter** structure and completeness
- **Adding observation sections** to files that need them
- **Enforcing link syntax** with `[[Entity Title]]` references

**Do NOT use** for:

- aOps framework structure decisions (that's aops-trainer)
- Non-markdown files
- External project files outside knowledge base

## Basic Memory Syntax Reference

@references/bmem-syntax.md

## Frontmatter Enforcement

### Required Fields

ALL knowledge base markdown files MUST have:

```yaml
---
title: Entity Title
permalink: entity-title-slug
type: note
---
```

**Field rules**:

- `title`: Human-readable, used in `[[references]]`
- `permalink`: URL-friendly slug (lowercase-with-hyphens)
- `type`: One of: note, person, project, meeting, decision, spec, task, goal

### Optional But Recommended

```yaml
---
title: Entity Title
permalink: entity-title-slug
tags: [tag1, tag2, tag3]
type: note
created: 2025-01-10T14:30:00Z
---
```

### Conversion Strategy

When file lacks frontmatter:

1. Extract title from first `# Heading` or filename
2. Generate permalink from title (lowercase, spaces → hyphens)
3. Infer type from directory:
   - `data/tasks/` → task
   - `data/projects/` → project
   - `data/goals/` → goal
   - `docs/bots/` → spec
   - Default → note
4. Preserve existing tags if present
5. Add created timestamp (current time)

## Observation Sections

### What Observations ARE

**Observations are NEW, categorized facts that ADD information beyond the document body and frontmatter.**

Observations should be:

- **Specific**: Concrete facts, not vague statements
- **Atomic**: One fact per observation
- **Additive**: New information not in body/frontmatter
- **Contextual**: Enough detail to understand
- **Semantic**: Enable knowledge graph queries

### What Observations Are NOT

**NEVER create observations that**:

- Repeat the document body (self-referential)
- Duplicate frontmatter metadata (due dates, types, status)
- State the obvious ("This is a task")
- Add no new information

### Bad vs Good Observations

**❌ BAD** (self-referential, duplicates metadata):

```markdown
---
due: "2025-11-07"
type: task
status: inbox
---

## Context

Review student thesis by Nov 7.

## Observations

- [task] Review student thesis by Nov 7. #status-inbox
- [requirement] Due date: 2025-11-07 #deadline
- [fact] Task type: todo #type-todo
```

Problems:

- First observation repeats context verbatim
- Due date already in frontmatter
- Type already in frontmatter
- "todo" is meaningless - WHAT kind of work?

**✅ GOOD** (adds new information, specific, semantic):

```markdown
---
due: "2025-11-07"
type: task
status: inbox
project: phd-supervision
goal: academic-profile
---

## Context

Review Rhyle Simcock's PhD thesis lodgement. Do NOT name examiners in comments.

## Observations

- [fact] Rhyle Simcock is PhD candidate in platform governance #student-rhyle-simcock #supervision
- [requirement] Cannot name examiners in comments as student will see them #compliance #privacy
- [insight] This is thesis examination stage requiring supervisor approval #phd-process #milestone
- [decision] Will focus review on methodology and structure, not examiner selection #review-strategy
```

Why this is good:

- Each observation adds NEW information
- No duplication of frontmatter
- Specific details about people, constraints, process
- Semantic tags for discoverability

### Observation Categories

**Common categories**:

- `[fact]` - Objective information about people, systems, processes
- `[decision]` - Choices made with reasoning
- `[technique]` - Methods and approaches used
- `[requirement]` - Constraints and must-haves
- `[insight]` - Key realizations and understanding
- `[problem]` - Issues identified
- `[solution]` - Resolutions and fixes
- `[question]` - Open questions needing answers
- `[idea]` - Thoughts and concepts for future

### Don't Repeat Yourself (DRY)

**Metadata ALREADY in frontmatter should NOT appear in observations**:

```yaml
---
due: "2025-11-15"         # ← Due date here
priority: 1               # ← Priority here
type: task                # ← Type here
status: inbox             # ← Status here
project: research         # ← Project here
---
```

**DON'T create observations like**:

- ❌ `[requirement] Due date: 2025-11-15`
- ❌ `[fact] Priority: 1`
- ❌ `[fact] Type: task`
- ❌ `[fact] Status: inbox`

**DO create observations that ADD context**:

- ✅ `[insight] Deadline chosen to align with conference submission #strategic-timing`
- ✅ `[decision] Prioritized high because blocks other work #dependencies`
- ✅ `[fact] Research involves 50 participants across 3 universities #scope #collaboration`

### Task-Specific Guidance

For task entities (`type: task`), observations should capture:

**People and relationships**:

```markdown
- [fact] Working with Dr. Sarah Johnson on methodology #collaborator-sarah-johnson
- [fact] Student Maria Garcia needs feedback by Friday #student-maria-garcia
- [requirement] Must coordinate with Prof. Lee before proceeding #stakeholder-approval
```

**Work type and method**:

```markdown
- [decision] Will use qualitative coding for analysis #methodology #review
- [technique] Reviewing in 2-hour focused blocks #time-management
- [insight] This type of review requires domain expertise in platform law #specialization
```

**Strategic context**:

```markdown
- [insight] Supervision work contributes to Academic Profile goal #strategic-alignment
- [fact] This is 3rd thesis in platform governance specialization #expertise-building
- [decision] Declined naming examiners to avoid conflict of interest #ethics
```

**Constraints and requirements**:

```markdown
- [requirement] Cannot name examiners in student-visible comments #compliance #privacy
- [requirement] Must complete via QUT My Tasks system #process #workflow
- [constraint] Limited to 3 working days due to university policy #deadline-reason
```

**NOT tasks themselves**:

```markdown
❌ [task] Review thesis # This IS the task, don't observe it ❌ [action] Complete by Nov 7 # Due date already in frontmatter ❌ [fact] This is a todo # Meaningless type
```

### Meaningful Tags

**Use specific, semantic tags**:

**Work type** (not "todo"):

- `#review` - Reviewing work
- `#writing` - Writing content
- `#research` - Research tasks
- `#teaching` - Teaching/presentation
- `#admin` - Administrative work
- `#supervision` - Student supervision
- `#meeting` - Meeting tasks

**People**:

- `#student-firstname-lastname`
- `#collaborator-firstname-lastname`
- `#stakeholder-role`

**Subject matter**:

- `#thesis` `#research` `#teaching`
- `#platform-governance` `#copyright` (domain-specific)

**Process/method**:

- `#review-strategy` `#methodology` `#compliance`

**Avoid**:

- ❌ `#status-inbox` (already in frontmatter)
- ❌ `#priority-p1` (already in frontmatter)
- ❌ `#type-todo` (meaningless and redundant)

### Converting Prose to Observations

Extract atomic facts that ADD information:

```markdown
# Document body says:

"Review student thesis. Focus on methodology chapter."

# DON'T observe:

- [task] Review student thesis ← Just repeats body

# DO observe:

- [decision] Will prioritize methodology chapter due to student's concerns #review-strategy
- [insight] Methodology needs strengthening based on preliminary read #quality-issue
```

## Link Syntax Enforcement

### Entity References

Replace all informal references with explicit links:

```markdown
# Before

See the authentication system documentation for details. Related to platform governance research.

# After

See [[Authentication System]] for details. Related to [[Platform Governance Research]].
```

### Relation Syntax

When file has clear relationships, add `## Relations` section:

```markdown
## Relations

- relation_type [[Target Entity]]
```

**Common relations**:

- `relates_to` - General connection
- `implements` - Implementation of spec
- `requires` - Dependency
- `extends` - Extension/enhancement
- `part_of` - Hierarchical membership
- `caused_by` - Causal relationship
- `leads_to` - Sequential relationship

### Forward References

**It's OK to reference entities that don't exist yet**:

```markdown
## Relations

- implements [[Future Specification]]
- requires [[Planned Component]]
```

Basic Memory creates placeholders and resolves when entities are created.

## File Exclusions

**DO NOT enforce Basic Memory syntax** on:

- `.github/workflows/*.yml` - GitHub Actions
- `.claude/settings.json` - Configuration
- `.gitignore`, `.gitattributes` - Git config
- `package.json`, `pyproject.toml` - Package manifests
- `LICENSE`, `COPYRIGHT` - Legal files
- Files with `<!-- NO_BMEM -->` comment at top

**All other `.md` files** in knowledge base repos should be converted.

## Workflow: Creating New Files

1. **Use template** (`@assets/bmem-template.md`):
   ```markdown
   ---
   title: Entity Title
   permalink: entity-title-slug
   tags: [relevant, tags]
   type: note
   ---

   # Entity Title

   ## Context

   Brief 1-3 sentence overview.

   ## Observations

   - [category] Content #tags

   ## Relations

   - relation_type [[Entity]]
   ```

2. **Fill frontmatter**:
   - Descriptive title
   - URL-friendly permalink
   - Appropriate type
   - Relevant tags

3. **Add context**: 1-3 sentence summary

4. **Extract observations**: Break content into atomic categorized facts

5. **Add relations**: Link to related entities

6. **Save** in appropriate directory

## Workflow: Converting Existing Files

1. **Read current file** completely

2. **Check frontmatter**:
   - Missing → Add using conversion strategy
   - Incomplete → Fill required fields
   - Malformed → Fix syntax

3. **Scan for observations**:
   - Factual content? → Add observations section
   - Pure procedural? → Skip observations
   - Extract facts from prose

4. **Identify entity references**:
   - Look for mentions of other concepts
   - Convert to `[[Entity Title]]` syntax
   - Add to Relations section if significant

5. **Preserve existing content**: Don't delete, only enhance

6. **Validate**:
   - Frontmatter has required fields
   - Observations use `[category]` syntax
   - Relations use `relation [[Entity]]` syntax
   - Links use double brackets

## Workflow: Batch Conversion

When converting multiple files in a directory:

1. **Identify scope**: Which directory/files?

2. **Check exclusions**: Skip config files

3. **Process one file at a time**:
   - Read
   - Convert
   - Write
   - Validate

4. **Report progress**: How many converted, any errors

5. **Don't batch commits**: One file per commit (or small logical groups)

## Validation Rules

### Frontmatter

✅ Valid:

```yaml
---
title: My Note
permalink: my-note
type: note
---
```

❌ Invalid (missing required):

```yaml
---
title: My Note
---
```

❌ Invalid (bad permalink):

```yaml
---
title: My Note
permalink: My Note With Spaces
type: note
---
```

### Observations

✅ Valid:

```markdown
- [fact] Content here #tag1 #tag2
```

❌ Invalid (missing category):

```markdown
- Content without category #tag1
```

❌ Invalid (wrong bracket type):

```markdown
- (fact) Content with wrong brackets
```

### Relations

✅ Valid:

```markdown
- implements [[Target Entity]]
```

❌ Invalid (missing double brackets):

```markdown
- implements [Target Entity]
```

❌ Invalid (no relation type):

```markdown
- [[Target Entity]]
```

## Integration with Other Skills

**context-search** uses bmem-ops for:

- Validating entity titles before search
- Checking relation syntax

**tasks** uses bmem-ops for:

- Creating task files in BM format
- Updating task frontmatter
- Adding task observations

**scribe** orchestrates bmem-ops for:

- All knowledge base file operations
- Ensuring semantic structure
- Maintaining consistent format

## Critical Rules

**NEVER**:

- Skip frontmatter validation
- Create files without `title`/`permalink`/`type`
- Use single brackets for entity references
- Add observations without categories
- Modify excluded config files
- Batch convert without checking each file
- Delete existing content during conversion

**ALWAYS**:

- Validate frontmatter completeness
- Use template for new files
- Preserve existing content when converting
- Check file against exclusion list
- Use `[[Entity Title]]` syntax for references
- Categorize observations with `[category]`
- Add tags for discoverability
- One commit per file or small logical group

## Quick Reference

**Frontmatter template**:

```yaml
---
title: Title Here
permalink: title-here
tags: [tag1, tag2]
type: note
---
```

**Observation syntax**: `- [category] content #tags`

**Relation syntax**: `- relation_type [[Entity]]`

**Link syntax**: `[[Entity Title]]` (double brackets)

**File structure**:

```markdown
# Title

## Context

One-liner summary.

## Observations

- [category] Facts #tags

## Relations

- relation_type [[Entity]]
```

**Common operations**:

| Task                | Action                              |
| ------------------- | ----------------------------------- |
| New file            | Use @assets/bmem-template.md        |
| Missing frontmatter | Add with conversion strategy        |
| Prose content       | Extract observations                |
| Entity mentions     | Convert to [[Entity]] links         |
| No observations     | Skip if purely procedural           |
| Config file         | Check exclusion list, skip if match |
