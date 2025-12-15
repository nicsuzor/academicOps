---
title: Obsidian-Compatible BMEM Format Guide
type: guide
permalink: obsidian-bmem-guide
description: Guide for using BMEM format with Obsidian vault features
tags:
  - bmem
  - obsidian
  - guide
---

# Obsidian-Compatible Basic Memory Format Guide

## Overview

This guide defines the Obsidian-compatible Basic Memory (bmem) format for markdown files in this repository. The format combines Basic Memory's semantic structure with Obsidian's native features for maximum compatibility.

**Key benefits**:

- Semantic knowledge graph with typed relations
- Full Obsidian compatibility (tags, links, graph view)
- AI-friendly structured format
- Human-readable plain markdown
- Git-friendly version control
- Portable across tools

## Quick Start Template

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

Brief 1-3 sentence overview explaining purpose and scope.

## Observations

- [category] Specific atomic fact or insight #inline-tag1 #inline-tag2
- [category] Another observation #inline-tag3

## Relations

- relation_type [[Related Entity Title]]
- relation_type [[Another Entity]]
```

## YAML Frontmatter

### Required Fields

All knowledge base files MUST include:

```yaml
---
title: Entity Title
permalink: entity-title-slug
type: note
---
```

**Field specifications**:

| Field       | Required | Format | Purpose                                             |
| ----------- | -------- | ------ | --------------------------------------------------- |
| `title`     | Yes      | String | Human-readable name, used in `[[references]]`       |
| `permalink` | Yes      | Slug   | URL-safe unique identifier (lowercase-with-hyphens) |
| `type`      | Yes      | String | Entity classification (see types below)             |

### Optional Standard Fields

```yaml
---
title: Entity Title
permalink: entity-title-slug
type: note
tags:
  - tag1
  - tag2
aliases:
  - Alternative Name
created: 2025-01-15T14:30:00Z
updated: 2025-01-15T16:45:00Z
---
```

**Obsidian-native fields**:

- `tags` / `tag`: Tags (Obsidian indexes these)
- `aliases` / `alias`: Alternative names for linking
- `cssclass` / `cssclasses`: Custom styling

**Basic Memory fields**:

- `created`: ISO 8601 timestamp (auto-generated if missing)
- `updated`: ISO 8601 timestamp (auto-updated)
- `type`: Entity classification

**Custom fields**: Add any custom fields for your use (status, priority, due, project, etc.)

### Tag Format

**Frontmatter tags** (YAML list format):

```yaml
tags:
  - research
  - academic-writing
  - content-moderation
```

**Or array format**:

```yaml
tags: [research, academic-writing, content-moderation]
```

**Allowed characters**:

- Letters (A-Z, a-z)
- Numbers (0-9, must include letters: #a2023 not #2023)
- Hyphens (`-`)
- Underscores (`_`)
- Forward slash (`/`) for nested tags
- Unicode (non-English, emoji)

**NOT allowed**:

- Spaces (use hyphens or underscores)
- Colons (`:`)
- Periods (`.`)
- Other special punctuation (ampersands, etc.)
- Starting with numbers

**Case sensitivity**:

- Obsidian: case-insensitive (#Research = #research)
- Basic Memory: case-sensitive for consistency
- **Best practice**: Use lowercase throughout

### Entity Types

Set `type:` in frontmatter:

| Type       | Usage                       | Common Fields                   |
| ---------- | --------------------------- | ------------------------------- |
| `note`     | General knowledge (default) | tags                            |
| `project`  | Projects and initiatives    | status, priority, deadline      |
| `task`     | Action items                | status, priority, due, assignee |
| `goal`     | Objectives and targets      | deadline, theory_of_change      |
| `person`   | People and contacts         | email, organization, role       |
| `meeting`  | Meeting notes               | date, attendees                 |
| `decision` | Documented decisions        | date, rationale                 |
| `spec`     | Technical specifications    | version, status                 |
| `playbook` | Reusable workflows          | category                        |

## Content Structure

### Title Heading (Required)

```markdown
# Entity Title
```

Must exactly match `title` field in frontmatter (case-sensitive).

### Context Section (Recommended)

```markdown
## Context

Brief 1-3 sentence overview of entity purpose, scope, and background.
```

Provides quick understanding without diving into details. Think "elevator pitch."

### Observations Section (Required)

The core semantic content. Each observation is a categorized, atomic fact.

```markdown
## Observations

- [category] Specific, atomic statement #tag1 #tag2
- [category] Another observation #tag3
```

#### Observation Syntax

```
- [category] content #tag1 #tag2
```

**Components**:

- `-`: Markdown list item (required)
- `[category]`: Classification in square brackets (required)
- `content`: The observation text (required)
- `#tag`: Zero or more inline tags (optional)

#### Observation Categories

| Category        | Purpose                     | Example                                                          |
| --------------- | --------------------------- | ---------------------------------------------------------------- |
| `[fact]`        | Objective information       | `[fact] Uses PostgreSQL 14.5 database #infrastructure`           |
| `[decision]`    | Choices made with rationale | `[decision] Use JWT for auth due to statelessness #architecture` |
| `[goal]`        | Objectives and targets      | `[goal] Achieve 99.9% uptime by Q2 #reliability`                 |
| `[strategy]`    | High-level approaches       | `[strategy] Phased rollout minimizes risk #deployment`           |
| `[insight]`     | Key realizations            | `[insight] 2FA adoption increased security 40% #metrics`         |
| `[requirement]` | Needs and constraints       | `[requirement] Must support OAuth 2.0 #auth`                     |
| `[technique]`   | Methods and approaches      | `[technique] Use bcrypt for password hashing #security`          |
| `[challenge]`   | Difficulties and obstacles  | `[challenge] Legacy schema requires refactoring #technical-debt` |
| `[problem]`     | Issues identified           | `[problem] Email delivery sometimes delayed #bug`                |
| `[solution]`    | Resolutions and fixes       | `[solution] Implemented retry queue #fix`                        |
| `[action]`      | Tasks to complete           | `[action] Review with team before deployment #process`           |
| `[idea]`        | Thoughts and concepts       | `[idea] Consider GraphQL for complex queries #future`            |
| `[question]`    | Open questions              | `[question] Should we cache user sessions? #performance`         |

#### What Observations ARE

**Observations are NEW, categorized facts that ADD information beyond the document body and frontmatter.**

Observations should be:

- **Specific**: Concrete facts, not vague statements
- **Atomic**: One fact per observation
- **Additive**: New information not in body/frontmatter
- **Contextual**: Enough detail to understand
- **Semantic**: Enable knowledge graph queries

#### What Observations Are NOT

**NEVER create observations that**:

- Repeat the document body (self-referential)
- Duplicate frontmatter metadata (due dates, types, status)
- State the obvious ("This is a task")
- Add no new information

#### Bad vs Good Examples

**❌ BAD** (self-referential, duplicates metadata):

```markdown
---
due: 2025-11-07
type: task
status: inbox
---

## Context

Review student thesis by Nov 7.

## Observations

- [task] Review student thesis by Nov 7 #status-inbox
- [requirement] Due date: 2025-11-07 #deadline
- [fact] Task type: todo #type-todo
```

**Problems**: Observations repeat context/frontmatter verbatim. No new information.

**✅ GOOD** (adds new information, specific, semantic):

```markdown
---
due: 2025-11-07
type: task
status: inbox
project: phd-supervision
---

## Context

Review Rhyle Simcock's PhD thesis lodgement. Do NOT name examiners in comments.

## Observations

- [fact] Rhyle Simcock is PhD candidate in platform governance #student-rhyle-simcock
- [requirement] Cannot name examiners in comments as student will see them #compliance #privacy
- [insight] This is thesis examination stage requiring supervisor approval #phd-process
- [decision] Will focus review on methodology and structure #review-strategy
```

**Why this is good**: Each observation adds NEW information. Specific details about people, constraints, process. Semantic tags.

### Relations Section (Required)

Typed, directional links between entities create the knowledge graph.

```markdown
## Relations

- relation_type [[Target Entity Title]]
- relation_type [[Another Entity]]
```

#### Relation Syntax

```
- relation_type [[Target Entity Title]]
```

**Components**:

- `-`: Markdown list item (required)
- `relation_type`: Describes the relationship (required)
- `[[Target Entity Title]]`: WikiLink to target (required)
  - Must match target's `title` field exactly
  - Case-sensitive
  - Spaces and punctuation allowed

#### Common Relation Types

| Relation                    | Meaning                            | Example                                          |
| --------------------------- | ---------------------------------- | ------------------------------------------------ |
| `part_of`                   | Hierarchical membership            | `part_of [[Research Program]]`                   |
| `supports`                  | Supporting relationship            | `supports [[Strategic Goal]]`                    |
| `requires`                  | Dependency                         | `requires [[Database Setup]]`                    |
| `implements`                | Implementation of spec             | `implements [[API Spec v2]]`                     |
| `extends`                   | Extension/enhancement              | `extends [[Base Framework]]`                     |
| `relates_to`                | General connection (use sparingly) | `relates_to [[Related Topic]]`                   |
| `contrasts_with`            | Opposite/alternative               | `contrasts_with [[Old Approach]]`                |
| `caused_by`                 | Causal relationship                | `caused_by [[Security Audit]]`                   |
| `leads_to`                  | Sequential relationship            | `leads_to [[Next Phase]]`                        |
| `similar_to`                | Similarity                         | `similar_to [[Reference Implementation]]`        |
| `incorporates_lessons_from` | Learning transfer                  | `incorporates_lessons_from [[Previous Project]]` |
| `underpins`                 | Foundational support               | `underpins [[Core Strategy]]`                    |
| `defines_allocation_for`    | Resource allocation                | `defines_allocation_for [[Team Budget]]`         |

#### Forward References

**You can link to entities that don't exist yet:**

```markdown
## Relations

- implements [[API Specification]]
- requires [[Database Models]]
```

Even if targets don't exist:

1. Forward reference creates placeholder in knowledge graph
2. When target created, relation automatically resolves
3. Graph traversal works bidirectionally
4. No manual linking required

This enables top-down planning and incremental development.

## WikiLinks

### Basic Syntax

```markdown
See [[Related Note]] for more information. [[Note Title|Display Text]] for custom text. [[folder/subfolder/Note]] for specific paths.
```

**Link features**:

- Auto-complete in Obsidian
- Backlinks automatically tracked
- Works even if target doesn't exist (forward references)
- Can link to headings: `[[Note#Heading]]`
- Can link to blocks: `[[Note#^block-id]]`

### Aliases

Define alternative names for easier linking:

```yaml
---
aliases:
  - Alt Name
  - Another Name
---
```

Now `[[Alt Name]]` links to this note in Obsidian.

## Inline Tags

Tags can appear anywhere in document body:

```markdown
This note discusses #research and #academic-writing.
```

**Combined with frontmatter tags**:

```yaml
---
tags: [research, academic]
---

This note discusses #writing and #editing.
```

All four tags (#research, #academic, #writing, #editing) are indexed.

**Nested tags**:

```markdown
#research/methods/qualitative #projects/academic/publications
```

## File Organization

### Where to Use bmem Format

**Required locations** (must use bmem):

- `data/context/` - Contextual information
- `data/goals/` - Goals and objectives
- `data/projects/` - Project metadata
- `data/playbooks/` - Reusable workflows
- `data/tasks/inbox/` - Active tasks
- `data/tasks/completed/` - Completed tasks

**Exempt locations** (standard markdown):

- `papers/` - Academic manuscripts
- `reviews/` - Review work
- `talks/` - Presentations
- `templates/` - Document templates
- `README.md` files
- `bots/` - Bot instructions (optional bmem)
- `data/tasks/archived/` - Old archived tasks

### File Naming

- Use descriptive names
- Spaces allowed but hyphens preferred
- Use `.md` extension
- Keep names consistent with `title` field

## Obsidian Integration

### Graph View

Relations create connections in Obsidian's graph view:

- `[[WikiLinks]]` in Relations section → graph edges
- Entity types → node colors (with CSS)
- Tags → filtering and grouping

### Dataview Queries

Query bmem files with Dataview plugin:

```dataview
TABLE type, status, tags
FROM "data/projects"
WHERE type = "project" AND status = "in-progress"
SORT priority DESC
```

Custom frontmatter fields enable powerful queries.

### Templates

Create Obsidian templates with bmem structure:

```markdown
---
title: { { title } }
permalink: { { permalink } }
type: note
tags: []
created: { { date:YYYY-MM-DDTHH:mm:ssZ } }
---

# {{title}}

## Context

## Observations

## Relations
```

## Validation

### Pre-commit Hook

Files are validated automatically. Run manually:

```bash
uv run python bmem_tools.py validate data/
```

### Common Errors

**Missing frontmatter**:

```
ERROR: data/projects/example.md:1 Missing YAML frontmatter
```

Fix: Add frontmatter at top

**Title mismatch**:

```
ERROR: data/projects/example.md:8 H1 doesn't match frontmatter title
```

Fix: Ensure `# Heading` matches `title:`

**Invalid observation syntax**:

```
ERROR: data/projects/example.md:15 Invalid observation syntax
```

Fix: Use `- [category] content #tags` format

**Unknown category**:

```
WARNING: data/projects/example.md:16 Unknown category: [note]
```

Fix: Use valid category from list above

## Best Practices

### Frontmatter

1. Keep frontmatter at top (no content before `---`)
2. Use consistent field names across notes
3. Use list format for multi-value fields
4. Add custom fields as needed for queries

### Tags

1. Use lowercase for consistency
2. Use hyphens for multi-word tags (not underscores)
3. Create hierarchies with nested tags (`parent/child`)
4. Don't over-tag (3-5 tags usually sufficient)
5. Use inline tags in observations for granularity
6. Use frontmatter tags for file-level categorization

### Observations

1. One fact per observation (atomic)
2. Add NEW information (not duplicating frontmatter/body)
3. Be specific and concrete
4. Choose appropriate category
5. Include inline tags for searchability
6. Write 3-5+ observations per file

### Relations

1. Use specific relation types (avoid overusing `relates_to`)
2. Create bidirectional links when appropriate
3. Use forward references liberally
4. Include 2-3+ relations per file
5. Think about knowledge graph traversal

### WikiLinks

1. Use descriptive note titles
2. Add aliases for common alternative names
3. Link liberally (forward references are fine)
4. Use heading/block links for specificity

## Complete Examples

### Project File

```markdown
---
title: Platform Modernization Initiative
permalink: platform-modernization-initiative
type: project
status: in-progress
priority: high
tags:
  - platform
  - infrastructure
  - modernization
aliases:
  - Platform Modernization
  - Mod Initiative
created: 2025-01-10T14:30:00Z
updated: 2025-01-15T16:45:00Z
---

# Platform Modernization Initiative

## Context

Initiative to modernize core platform infrastructure to support scaling to 100K users. Phased approach over 6 months with focus on Kubernetes migration, database optimization, and observability.

## Observations

- [goal] Achieve 99.9% uptime SLA by end of Q2 #reliability #sla
- [requirement] Must support horizontal scaling across 3 regions #scalability #architecture
- [strategy] Phased migration approach minimizes risk and enables rollback #risk-management #deployment
- [challenge] Legacy database schema requires significant refactoring #technical-debt #database
- [decision] Use Kubernetes for container orchestration based on team expertise #infrastructure #technology
- [insight] Current monolithic architecture creates deployment bottlenecks #analysis
- [fact] Infrastructure budget allocated at $120K for 6 months #resources #budget
- [technique] Blue-green deployment strategy for zero-downtime migrations #best-practice

## Relations

- part_of [[Technical Roadmap 2025]]
- requires [[Database Migration Plan]]
- requires [[Kubernetes Training Program]]
- supports [[Product Growth Goals]]
- contrasts_with [[Previous Monolithic Architecture]]
- incorporates_lessons_from [[Payment Service Migration]]
```

### Task File

```markdown
---
title: Review Rhyle's Thesis Lodgement
permalink: review-rhyle-thesis-lodgement
type: task
status: inbox
priority: p1
due: 2025-11-07
project: phd-supervision
tags:
  - phd
  - supervision
  - thesis-review
created: 2025-11-05T09:15:00Z
---

# Review Rhyle's Thesis Lodgement

## Context

Review Rhyle Simcock's PhD thesis lodgement package for submission. Final supervisor approval required before examination. CRITICAL: Do NOT name examiners in comments as student will see them.

## Observations

- [fact] Rhyle Simcock is PhD candidate researching platform governance and content moderation #student-rhyle-simcock
- [requirement] Cannot name potential examiners in comments due to student visibility #compliance #privacy
- [insight] This is formal thesis examination stage requiring supervisor sign-off before examiner appointment #phd-process
- [decision] Will focus review on methodology chapter and theoretical framework #review-strategy
- [technique] Use track changes for minor corrections, comments for substantive feedback #review-process
- [fact] Thesis is approximately 80,000 words across 7 chapters #scope

## Relations

- part_of [[PhD Supervision Activities]]
- requires [[Examiner Nomination Form]]
- supports [[Rhyle Simcock PhD Journey]]
- relates_to [[Platform Governance Research]]
```

### Goal File

```markdown
---
title: World-Class Academic Profile
permalink: world-class-academic-profile
type: goal
status: active
priority: high
tags:
  - career
  - academic-profile
  - strategy
created: 2025-01-01T00:00:00Z
updated: 2025-01-15T14:30:00Z
---

# World-Class Academic Profile

## Context

Strategic goal to build internationally recognized academic profile in platform governance and digital constitutionalism. Focus on high-impact publications, speaking engagements, and thought leadership.

## Observations

- [strategy] Prioritize quality over quantity in publications #publication-strategy
- [goal] Publish 2-3 articles in top-tier journals per year (A*/A) #metrics #publications
- [goal] Maintain strong citation metrics (h-index growth) #impact #metrics
- [requirement] Balance research with teaching and service commitments #workload
- [insight] International visibility requires consistent conference presence and social media engagement #visibility #engagement
- [decision] Focus research agenda on 2-3 core themes for coherence #focus #research-agenda
- [technique] Use preprints and working papers to establish priority and get feedback #research-practice

## Relations

- underpins [[Research Program]]
- supports [[Career Development Plan]]
- requires [[Publication Pipeline]]
- requires [[Conference Speaking Program]]
- relates_to [[Platform Governance Research]]
- defines_allocation_for [[Time Budget]]
```

## Conversion from Regular Markdown

To convert existing markdown to bmem format:

1. **Add frontmatter** with required fields
2. **Ensure H1 matches title**
3. **Add Context section** with 1-3 sentence overview
4. **Extract observations** from prose
   - Identify key facts
   - Categorize each observation
   - Add inline tags
5. **Add Relations section**
   - Identify references to other entities
   - Convert to `[[WikiLinks]]`
   - Add relation types
6. **Preserve original content** as needed
7. **Validate** using bmem_tools.py

### Conversion Example

**Before**:

```markdown
# Research Notes

I'm analyzing platform governance challenges. The key issues are scale, context, and accountability. Automated systems often fail to understand nuance.
```

**After**:

```markdown
---
title: Platform Governance Research Notes
permalink: platform-governance-research-notes
type: note
tags:
  - research
  - platform-governance
  - content-moderation
created: 2025-01-15T14:30:00Z
---

# Platform Governance Research Notes

## Context

Research analyzing key challenges in platform governance including scale, context awareness, and accountability mechanisms.

## Observations

- [challenge] Platform governance faces fundamental issues of scale and context #scalability #context-awareness
- [problem] Automated moderation systems frequently fail to understand nuance #automation #limitations
- [insight] Accountability mechanisms remain underdeveloped in current platform governance models #accountability #governance-gap
- [fact] Research focuses on intersection of automated systems and human oversight #research-scope

## Relations

- part_of [[Platform Governance Research]]
- relates_to [[Content Moderation Systems]]
- supports [[World-Class Academic Profile]]
```

## Quick Check Before Committing

- [ ] Frontmatter with title, permalink, type, tags
- [ ] H1 heading matches title exactly
- [ ] Context section explains purpose (1-3 sentences)
- [ ] 3-5+ observations with categories and inline tags
- [ ] Observations add NEW information (not duplicating frontmatter/body)
- [ ] 2-3+ relations with specific types
- [ ] All `[[WikiLinks]]` use exact entity titles
- [ ] No validation errors (`uv run python bmem_tools.py validate data/`)

## References

- **Obsidian Format**: [[obsidian-format-spec.md]]
- **Basic Memory**: [[https://github.com/basicmachines-co/basic-memory]]
- **Extended bmem Guide**: [[ai-assistant-guide-extended.md]]

## Benefits

**For humans**:

- Plain markdown, readable anywhere
- Git-friendly version control
- Works in Obsidian for rich features
- Portable across tools

**For AI assistants**:

- Structured format enables precise extraction
- Semantic categories improve understanding
- Knowledge graph enables traversal and discovery
- Consistent format reduces parsing errors

**For knowledge management**:

- Typed relations create rich connections
- Forward references enable top-down planning
- Tags enable powerful filtering
- Observations make tacit knowledge explicit
