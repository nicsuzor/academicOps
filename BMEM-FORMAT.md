---
title: BMEM Format Specification
type: spec
permalink: bmem-format-spec
description: Complete specification for basic-memory markdown format
tags:
  - bmem
  - specification
  - format
---

# Basic Memory (bmem) Format Specification

## Overview

All markdown files in this repository MUST follow the basic-memory (bmem) format - a restricted grammar providing structured, semantic knowledge representation.

## Required Structure

### 1. YAML Frontmatter

Every markdown file MUST begin with YAML frontmatter:

```yaml
---
title: Clear Descriptive Title
permalink: url-safe-slug
type: note|person|project|meeting|decision|spec|task
tags:
  - tag1
  - tag2
created: YYYY-MM-DDTHH:MM:SSZ  # Optional, auto-generated if missing
updated: YYYY-MM-DDTHH:MM:SSZ  # Optional, auto-generated if missing
---
```

**Required fields:**

- `title`: Human-readable title
- `permalink`: URL-safe slug (auto-generated from title if missing)
- `type`: Entity type (default: note)
- `tags`: List of tags (minimum 1 recommended)

**Optional fields:**

- `created`: ISO 8601 timestamp
- `updated`: ISO 8601 timestamp
- Custom fields as needed for specific types

### 2. Title Heading

After frontmatter, the top-level H1 heading MUST match the title:

```markdown
# Clear Descriptive Title
```

### 3. Context Section (Optional but Recommended)

```markdown
## Context

Brief background explaining the purpose and scope of this document.
```

### 4. Observations Section

The core semantic content. Each observation MUST follow this syntax:

```markdown
## Observations

- [category] Specific, atomic statement #tag1 #tag2
```

**Observation categories:**

- `[fact]`: Objective information
- `[idea]`: Thoughts and concepts
- `[decision]`: Choices made with rationale
- `[technique]`: Methods and approaches
- `[requirement]`: Needs and constraints
- `[question]`: Open questions
- `[insight]`: Key realizations
- `[problem]`: Issues identified
- `[solution]`: Resolutions
- `[action]`: Tasks to complete
- `[goal]`: Objectives and targets
- `[strategy]`: High-level approaches
- `[challenge]`: Difficulties and obstacles

**Rules:**

- One fact per observation (atomic)
- Specific, not vague
- Include relevant inline tags
- Minimum 3 observations recommended

### 5. Relations Section

Typed, directional links between entities:

```markdown
## Relations

- relation_type [[Target Entity Title]]
```

**Common relation types:**

- `relates_to`: General connection
- `implements`: Implementation of spec/design
- `requires`: Dependency relationship
- `extends`: Extension or enhancement
- `part_of`: Hierarchical membership
- `supports`: Supporting relationship
- `contrasts_with`: Opposite or alternative
- `caused_by`: Causal relationship
- `leads_to`: Sequential relationship
- `similar_to`: Similarity relationship
- `incorporates_lessons_from`: Learning transfer
- `underpins`: Foundational support
- `defines_allocation_for`: Resource allocation

**Rules:**

- Use exact entity titles in `[[brackets]]`
- Be specific with relation types (avoid overusing `relates_to`)
- Forward references are allowed (target can be created later)
- Minimum 2 relations recommended

## File Organization

### Allowed Locations

bmem-formatted files should be in:

- `data/` - Personal data and state (PRIVATE)
  - `data/context/` - Contextual information
  - `data/goals/` - Goals and objectives
  - `data/projects/` - Project metadata
  - `data/playbooks/` - Reusable workflows
  - `data/tasks/` - Task management
- `bots/` - Bot instructions (can use bmem format but not required)

### Exemptions

The following locations do NOT require bmem format:

- `papers/` - Academic manuscripts
- `reviews/` - Review work
- `talks/` - Presentations
- `templates/` - Document templates
- `README.md` files
- Files in `bots/` (optional bmem usage)

## Entity Types

### `note` (default)

General knowledge and information

### `person`

People and contacts

- Additional fields: `email`, `organization`, `role`

### `project`

Projects and initiatives

- Additional fields: `status`, `priority`, `deadline`

### `meeting`

Meeting notes

- Additional fields: `date`, `attendees`

### `decision`

Documented decisions

- Should include: Context, Decision, Rationale, Consequences

### `spec`

Technical specifications

- Should include: Requirements, Technical Details

### `task`

Tasks and action items

- Additional fields: `status`, `priority`, `deadline`, `assignee`

## Validation Rules

1. **Frontmatter is required** - Files without frontmatter are invalid
2. **Title consistency** - H1 heading must match frontmatter title
3. **Observations section required** - At least for files in `data/`
4. **Relations section required** - At least for files in `data/`
5. **Valid observation syntax** - `- [category] content #tags`
6. **Valid relation syntax** - `- relation_type [[Target]]`
7. **No duplicate permalinks** - Each permalink must be unique

## Examples

### Minimal Valid File

```markdown
---
title: Simple Note
permalink: simple-note
type: note
tags:
  - example
---

# Simple Note

## Context

Brief description.

## Observations

- [fact] This is a fact about the note #example
- [idea] This is an idea #brainstorming
- [decision] We decided to use bmem format #standards

## Relations

- relates_to [[Other Note]]
- part_of [[Parent Project]]
```

### Project File

```markdown
---
title: Research Project
permalink: research-project
type: project
status: in-progress
priority: high
tags:
  - research
  - academic
---

# Research Project

## Context

Investigating X in the context of Y.

## Observations

- [goal] Complete literature review by end of month #milestone
- [requirement] Need access to database X #resources
- [insight] Pattern Y emerges from preliminary analysis #findings
- [challenge] Limited time for data collection #constraints

## Relations

- part_of [[Computational Legal Studies]]
- requires [[Literature Review]]
- supports [[World-Class Academic Profile]]
```

## Conversion Guidelines

When converting existing markdown to bmem:

1. **Add frontmatter** with appropriate metadata
2. **Identify observations** - Extract key facts, decisions, insights
3. **Add relation types** - Convert simple links to typed relations
4. **Add inline tags** - Tag observations appropriately
5. **Preserve original content** - Keep additional sections as needed
6. **Use Context section** - Move introduction/background text

## Benefits

- **Semantic structure**: Clear categorization of information
- **Knowledge graph**: Typed relations enable graph traversal
- **AI-friendly**: Structured format for agent processing
- **Human-readable**: Plain markdown, version control friendly
- **Searchable**: Tags and categories enable precise queries
- **Persistent**: Plain text survives beyond any tool

## References

- Based on [[basic-memory|https://github.com/basicmachines-co/basic-memory]] format
- Extended specification in [[ai-assistant-guide-extended.md]]
