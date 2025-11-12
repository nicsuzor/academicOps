# Claude Guide: Writing bmem Format

## Overview

When creating or editing markdown files in this repository, you MUST use the basic-memory (bmem) format for files in the `data/` directory. This provides structured, semantic knowledge representation.

## Quick Reference

### Template

```markdown
---
title: Clear Descriptive Title
permalink: url-safe-slug
type: note
tags:
  - tag1
  - tag2
---

# Clear Descriptive Title

## Context

Brief background and purpose of this document.

## Observations

- [category] Specific atomic fact or insight #tag1 #tag2
- [category] Another observation #tag3

## Relations

- relation_type [[Related Entity Title]]
- relation_type [[Another Entity]]
```

## When to Use bmem Format

### Required Locations

- `data/context/` - Contextual information
- `data/goals/` - Goals and objectives
- `data/projects/` - Project files
- `data/playbooks/` - Workflows
- `data/tasks/inbox/` - Active tasks
- `data/tasks/completed/` - Completed tasks

### Exempt Locations

- `papers/`, `reviews/`, `talks/` - Academic content (use standard markdown)
- `templates/` - Templates
- `README.md` files
- `bots/` - Optional bmem usage
- `data/tasks/archived/` - Old archived tasks

## Observation Categories

Choose the most specific category:

- `[fact]` - Objective, verifiable information
- `[decision]` - Choices made with rationale
- `[goal]` - Objectives and targets
- `[strategy]` - High-level approaches
- `[insight]` - Key realizations and discoveries
- `[requirement]` - Needs and constraints
- `[technique]` - Methods and approaches
- `[challenge]` - Difficulties and obstacles
- `[problem]` - Issues identified
- `[solution]` - Resolutions and fixes
- `[action]` - Tasks and action items
- `[idea]` - Thoughts and concepts
- `[question]` - Open questions

### Observation Best Practices

✓ **Good observations:**

```markdown
- [decision] Use PostgreSQL for better JSON support over MySQL #database #architecture
- [insight] 2FA adoption increased security by 40% based on Q3 metrics #security #metrics
- [requirement] Must support OAuth 2.0 for Google and GitHub #auth #integration
```

✗ **Poor observations:**

```markdown
- [fact] We use a database
- [idea] Security is important
- [decision] Made some changes
```

**Rules:**

- One fact per observation (atomic)
- Be specific and concrete
- Include inline tags for searchability
- Minimum 3-5 observations per file

## Relation Types

Use specific relation types to create meaningful knowledge graphs:

### Common Relations

- `part_of` - This is part of a larger entity
- `supports` - This supports/enables another entity
- `requires` - This depends on another entity
- `implements` - This implements a specification
- `extends` - This extends/enhances another entity
- `relates_to` - General connection (use sparingly!)

### Specialized Relations

- `defines_allocation_for` - Resource allocation relationship
- `incorporates_lessons_from` - Learning transfer
- `underpins` - Foundational support
- `contrasts_with` - Alternative or opposite
- `caused_by` - Causal relationship
- `leads_to` - Sequential relationship

### Relation Best Practices

✓ **Good relations:**

```markdown
## Relations

- part_of [[Computational Legal Studies]]
- requires [[Database Infrastructure]]
- supports [[World-Class Academic Profile]]
- implements [[API Specification v2]]
```

✗ **Poor relations:**

```markdown
## Relations

- relates_to [[Some Project]]
- relates_to [[Another Thing]]
```

**Rules:**

- Be specific with relation types
- Use exact entity titles (case-sensitive)
- Forward references are OK (entity can be created later)
- Minimum 2-3 relations per file

## Entity Types

Set `type:` in frontmatter:

- `note` - General knowledge (default)
- `project` - Projects and initiatives
- `goal` - Goals and objectives
- `task` - Action items
- `person` - People and contacts
- `meeting` - Meeting notes
- `decision` - Documented decisions
- `spec` - Technical specifications
- `playbook` - Reusable workflows

### Type-Specific Fields

**Projects:**

```yaml
type: project
status: in-progress | planned | completed
priority: high | medium | low
```

**Tasks:**

```yaml
type: task
status: inbox | in-progress | completed
priority: p1 | p2 | p3
deadline: YYYY-MM-DD
```

## Creating New Files

### Process

1. **Search first** - Check if entity already exists
   ```bash
   uv run python bmem_tools.py validate data/
   ```

2. **Use template** - Start with bmem structure

3. **Fill in metadata:**
   - Title: Clear, descriptive
   - Permalink: Auto-generated from title (lowercase, hyphens)
   - Type: Choose appropriate entity type
   - Tags: 3-5 relevant tags

4. **Add Context:** Brief background explaining purpose

5. **Write Observations:** 3-5 minimum, categorized and tagged

6. **Add Relations:** 2-3 minimum, typed connections

### Example Workflow

```python
# For a new project file:
---
title: Platform Modernization
permalink: platform-modernization
type: project
status: in-progress
priority: high
tags:
  - platform
  - infrastructure
  - modernization
---

# Platform Modernization

## Context

Initiative to modernize core platform infrastructure to support scaling to 100K users.

## Observations

- [goal] Achieve 99.9% uptime SLA by end of Q2 #reliability #sla
- [requirement] Must support horizontal scaling across regions #scalability #architecture
- [strategy] Phased migration approach minimizes risk #risk-management #deployment
- [challenge] Legacy database schema requires significant refactoring #technical-debt #database
- [decision] Use Kubernetes for container orchestration #infrastructure #technology

## Relations

- part_of [[Technical Roadmap 2025]]
- requires [[Database Migration Plan]]
- supports [[Product Growth Goals]]
- contrasts_with [[Previous Monolithic Architecture]]
```

## Editing Existing Files

When updating bmem files:

1. **Preserve structure** - Keep all required sections
2. **Add observations** - Append new insights to Observations section
3. **Update relations** - Add new connections as discovered
4. **Update metadata** - Update tags if scope changes
5. **Don't remove** - Keep historical observations (use `updated:` timestamp)

## Converting Existing Markdown

Use the conversion tool:

```bash
# Dry run (preview changes)
uv run python bmem_tools.py convert --dry-run path/to/file.md

# Convert file
uv run python bmem_tools.py convert path/to/file.md
```

Manual conversion steps:

1. Add frontmatter with required fields
2. Ensure H1 matches title
3. Add Context section if missing
4. Identify key facts → convert to observations with categories
5. Identify references → convert to typed relations
6. Add inline tags to observations

## Validation

### Pre-commit Hook

Files are automatically validated on commit. To run manually:

```bash
uv run python bmem_tools.py validate data/
```

### Common Errors

**Missing frontmatter:**

```markdown
ERROR: data/projects/example.md:1 Missing YAML frontmatter
```

Fix: Add frontmatter at top of file

**Title mismatch:**

```markdown
ERROR: data/projects/example.md:8 H1 heading doesn't match frontmatter title
```

Fix: Ensure `# Heading` matches `title:` in frontmatter

**Invalid observation syntax:**

```markdown
ERROR: data/projects/example.md:15 Invalid observation syntax
```

Fix: Use `- [category] content #tags` format

**Unknown category:**

```markdown
WARNING: data/projects/example.md:16 Unknown observation category: [note]
```

Fix: Use valid category from list above

**Missing sections:**

```markdown
WARNING: data/projects/example.md: Missing ## Observations section
```

Fix: Add Observations and Relations sections

## Tips for AI Assistants

1. **Always validate** - Check bmem format when creating/editing data/ files
2. **Be specific** - Use precise observation categories and relation types
3. **Think semantically** - Each observation should be a searchable, atomic fact
4. **Create knowledge graphs** - Relations enable powerful traversal and discovery
5. **Tag strategically** - Tags enable filtering and organization
6. **Forward references OK** - Link to entities that don't exist yet
7. **Preserve history** - Don't delete observations, add new ones
8. **Check existing** - Search before creating to avoid duplicates

## Integration with Other Tools

### Basic Memory MCP

If basic-memory MCP server is configured, bmem files integrate automatically:

- Files are indexed in knowledge graph
- Relations enable graph traversal
- Observations become searchable facts
- Types enable semantic queries

### Obsidian

bmem format is Obsidian-compatible:

- `[[Wiki Links]]` work natively
- Tags are searchable
- Graph view shows relations
- Frontmatter renders correctly

## Quick Check

Before committing, verify:

- [ ] Frontmatter with title, permalink, type, tags
- [ ] H1 heading matches title
- [ ] Context section explains purpose
- [ ] 3-5+ observations with categories and tags
- [ ] 2-3+ relations with specific types
- [ ] Inline tags in observations
- [ ] No validation errors

## Full Specification

See `bots/BMEM-FORMAT.md` for complete specification.
