# Basic Memory Markdown Syntax Specification

This document defines the complete syntax for Basic Memory markdown files.

## Overview

Basic Memory uses structured markdown files to build a semantic knowledge graph. Each file represents an **entity** with:

- **YAML frontmatter** (metadata)
- **Content sections** (Context, Observations, Relations)
- **Semantic markup** (categories, tags, entity references)

## YAML Frontmatter (Required)

All Basic Memory files MUST start with YAML frontmatter delimited by `---`.

### Required Fields

```yaml
---
title: Entity Title
permalink: entity-title-slug
type: note
---
```

**Field specifications**:

- **title** (string, required): Human-readable entity name
  - Used in `[[Entity Title]]` references
  - Can include spaces, punctuation
  - Example: `"Authentication System v2"`

- **permalink** (string, required): Unique URL-friendly identifier
  - Lowercase with hyphens
  - No spaces, special characters except hyphens/underscores
  - Example: `"authentication-system-v2"`

- **type** (string, required): Entity classification
  - `note`: General knowledge (default)
  - `person`: People and contacts
  - `project`: Projects and initiatives
  - `meeting`: Meeting notes
  - `decision`: Documented decisions
  - `spec`: Technical specifications

### Optional Fields

```yaml
---
title: Entity Title
permalink: entity-title-slug
tags: [tag1, tag2, tag3]
type: note
created: 2025-01-10T14:30:00Z
updated: 2025-01-15T09:15:00Z
---
```

- **tags** (array, optional): Categorization tags
  - YAML array format: `[tag1, tag2, tag3]`
  - Lowercase with hyphens preferred
  - Example: `[security, auth, api]`

- **created** (ISO 8601 datetime, optional): Creation timestamp
  - Format: `YYYY-MM-DDTHH:MM:SSZ`
  - Auto-generated if omitted

- **updated** (ISO 8601 datetime, optional): Last modification timestamp
  - Format: `YYYY-MM-DDTHH:MM:SSZ`
  - Auto-updated on edits

### Complete Frontmatter Example

```yaml
---
title: Authentication System
permalink: authentication-system
tags: [security, auth, api, backend]
type: spec
created: 2025-01-10T14:30:00Z
updated: 2025-01-15T09:15:00Z
---
```

## Content Structure

After frontmatter, structure content using these standard sections:

### Title (Required)

```markdown
# Entity Title
```

Must match `title` field in frontmatter.

### Context (Recommended)

```markdown
## Context

Brief 1-3 sentence overview of the entity.
```

Provides quick understanding without diving into details.

### Observations (Core Feature)

```markdown
## Observations

- [category] Observation content #tag1 #tag2
- [category] Another observation #tag3
```

**Observations are categorized facts with optional tags.**

#### Observation Syntax

```
- [category] content #tag1 #tag2 #tag3
```

**Components**:

- `-` (required): Markdown list item
- `[category]` (required): Classification in square brackets
- `content` (required): The actual observation text
- `#tag` (optional): Zero or more tags for filtering

#### Common Categories

| Category        | Purpose                | Example                                                     |
| --------------- | ---------------------- | ----------------------------------------------------------- |
| `[fact]`        | Objective information  | `[fact] API uses REST architecture #api`                    |
| `[idea]`        | Thoughts and concepts  | `[idea] Consider GraphQL for complex queries #future`       |
| `[decision]`    | Choices made           | `[decision] Use JWT tokens for auth #security`              |
| `[technique]`   | Methods and approaches | `[technique] Hash passwords with bcrypt #best-practice`     |
| `[requirement]` | Needs and constraints  | `[requirement] Support OAuth 2.0 providers #auth`           |
| `[question]`    | Open questions         | `[question] Should we cache user sessions? #performance`    |
| `[insight]`     | Key realizations       | `[insight] 2FA adoption increased security by 40% #metrics` |
| `[problem]`     | Issues identified      | `[problem] Password reset emails delayed #bug`              |
| `[solution]`    | Resolutions            | `[solution] Implemented retry queue for emails #fix`        |

#### Observation Examples

```markdown
## Observations

- [decision] Use JWT tokens for authentication #security #api
- [technique] Hash passwords with bcrypt before storage #best-practice
- [requirement] Support OAuth 2.0 providers (Google, GitHub) #auth
- [fact] Session timeout set to 24 hours #configuration
- [problem] Password reset emails sometimes delayed #bug
- [solution] Implemented retry queue for email delivery #fix
- [insight] 2FA adoption increased security by 40% #metrics
- [question] Should we implement refresh tokens? #future
```

### Relations (Core Feature)

```markdown
## Relations

- relation_type [[Target Entity]]
- relation_type [[Another Entity]]
```

**Relations are directional links between entities using double brackets.**

#### Relation Syntax

```
- relation_type [[Target Entity Title]]
```

**Components**:

- `-` (required): Markdown list item
- `relation_type` (required): Describes the relationship
- `[[Target Entity Title]]` (required): Double-bracketed entity reference
  - Must exactly match target entity's `title` field
  - Case-sensitive
  - Can include spaces and punctuation

#### Common Relation Types

| Relation         | Meaning                 | Example                                     |
| ---------------- | ----------------------- | ------------------------------------------- |
| `relates_to`     | General connection      | `relates_to [[API Documentation]]`          |
| `implements`     | Implementation of spec  | `implements [[Authentication Spec v2]]`     |
| `requires`       | Dependency              | `requires [[User Database Schema]]`         |
| `extends`        | Extension/enhancement   | `extends [[Base Security Model]]`           |
| `part_of`        | Hierarchical membership | `part_of [[API Backend Services]]`          |
| `contrasts_with` | Opposite/alternative    | `contrasts_with [[API Key Authentication]]` |
| `caused_by`      | Causal relationship     | `caused_by [[Security Audit Findings]]`     |
| `leads_to`       | Sequential relationship | `leads_to [[Session Management]]`           |
| `similar_to`     | Similarity              | `similar_to [[OAuth Implementation]]`       |

#### Bidirectional Relations

Relations can be bidirectional by creating explicit links in both entities:

```markdown
# In "Login Flow" note

## Relations

- part_of [[Authentication System]]

# In "Authentication System" note

## Relations

- includes [[Login Flow]]
```

#### Forward References

**You can reference entities that don't exist yet:**

```markdown
# In "API Implementation" note

## Relations

- implements [[API Specification]]
- requires [[Database Models]]
```

Even if "API Specification" and "Database Models" don't exist yet:

1. Forward reference creates placeholder in knowledge graph
2. When target entity is created, relation automatically resolves
3. Graph traversal works in both directions
4. No manual linking required

#### Relation Examples

```markdown
## Relations

- implements [[Authentication Spec v2]]
- requires [[User Database Schema]]
- requires [[Email Service]]
- extends [[Base Security Model]]
- part_of [[API Backend Services]]
- contrasts_with [[API Key Authentication]]
- leads_to [[Session Management]]
- caused_by [[Security Audit 2025-01]]
- similar_to [[OAuth2 Reference Implementation]]
```

## Complete Example

```markdown
---
title: Authentication System
permalink: authentication-system
tags: [security, auth, api, backend]
type: spec
created: 2025-01-10T14:30:00Z
updated: 2025-01-15T09:15:00Z
---

# Authentication System

## Context

JWT-based authentication system for the API backend. Supports OAuth 2.0 providers (Google, GitHub) and includes 2FA support.

## Observations

- [decision] Use JWT tokens for authentication #security #api
- [technique] Hash passwords with bcrypt (cost factor 12) #best-practice
- [requirement] Support OAuth 2.0 providers (Google, GitHub) #auth
- [fact] Session timeout set to 24 hours #configuration
- [fact] Refresh tokens valid for 30 days #configuration
- [problem] Password reset emails sometimes delayed #bug #known-issue
- [solution] Implemented retry queue for email delivery #fix
- [insight] 2FA adoption increased security by 40% #metrics #success
- [question] Should we add biometric authentication? #future

## Relations

- implements [[Authentication Spec v2]]
- requires [[User Database Schema]]
- requires [[Email Service]]
- extends [[Base Security Model]]
- part_of [[API Backend Services]]
- contrasts_with [[API Key Authentication]]
- leads_to [[Session Management]]
- caused_by [[Security Audit 2025-01]]
```

## Validation Rules

### Frontmatter Validation

✅ **Valid**:

```yaml
---
title: My Note
permalink: my-note
type: note
---
```

❌ **Invalid** (missing required fields):

```yaml
---
title: My Note
---
```

❌ **Invalid** (bad permalink format):

```yaml
---
title: My Note
permalink: My Note With Spaces
type: note
---
```

### Observation Validation

✅ **Valid**:

```markdown
- [fact] Content here #tag1 #tag2
```

❌ **Invalid** (missing category):

```markdown
- Content without category #tag1
```

❌ **Invalid** (wrong bracket type):

```markdown
- (fact) Content with wrong brackets
```

### Relation Validation

✅ **Valid**:

```markdown
- implements [[Target Entity]]
```

❌ **Invalid** (missing double brackets):

```markdown
- implements [Target Entity]
```

❌ **Invalid** (no relation type):

```markdown
- [[Target Entity]]
```

## Conversion from Regular Markdown

To convert regular markdown to Basic Memory format:

1. **Add frontmatter**:
   ```yaml
   ---
   title: Your Title
   permalink: your-title-slug
   type: note
   tags: [relevant, tags]
   ---
   ```

2. **Add title heading**: `# Your Title`

3. **Add Context section**: Summarize in 1-3 sentences

4. **Convert prose to Observations**:
   - Extract atomic facts
   - Categorize each observation
   - Add relevant tags

5. **Extract Relations**:
   - Identify references to other concepts/documents
   - Make explicit with `[[Entity Title]]` syntax
   - Add appropriate relation type

### Conversion Example

**Before** (regular markdown):

```markdown
# My Research Notes

I'm working on analyzing social media content moderation. The key challenges are scale and context. Platforms use automated systems but they often fail.
```

**After** (Basic Memory):

```yaml
---
title: Social Media Content Moderation Research
permalink: social-media-content-moderation-research
tags: [research, content-moderation, social-media]
type: note
---

# Social Media Content Moderation Research

## Context
Research analyzing challenges in social media content moderation systems.

## Observations
- [challenge] Content moderation faces issues of scale and context #scalability #context-awareness
- [technique] Platforms primarily use automated moderation systems #automation #platforms
- [problem] Automated moderation systems frequently fail to capture context #limitations #accuracy

## Relations
- relates_to [[Platform Governance]]
- part_of [[Research Projects]]
```

## Best Practices

1. **Atomic observations**: One fact per observation line
2. **Consistent categories**: Use standard categories across your knowledge base
3. **Meaningful tags**: Tag for discoverability, not exhaustively
4. **Explicit relations**: Make all important connections explicit
5. **Forward references**: Don't wait to create all entities before linking
6. **Regular updates**: Keep observations current as knowledge evolves
