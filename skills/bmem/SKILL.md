# bmem: Obsidian-Compatible Knowledge Graph Maintenance

## Authoritative Domain Knowledge

**Data Format**: Markdown entities with YAML frontmatter (Obsidian-compatible)
**Storage Location**: `data/` hierarchy in each repository
**Entity Structure**: `data/{entity-type}/{entity-slug}.md`
**Entity Types**: note, project, person, event, concept, relation
**Required Fields**: title, permalink, type
**Optional Fields**: tags, related, created, modified, status
**Linking**: WikiLinks `[[entity-slug]]` for cross-references
**Relations**: Expressed via frontmatter fields (related:, part-of:, etc.) and WikiLinks in content
**Write Access**: bmem skill ONLY - agents must not write data/ files directly
**Cross-Repo**: Each repository has independent data/ hierarchy

---

## Overview

Silently extracts information from sessions and maintains knowledge graph in Obsidian-compatible Basic Memory format. Operates continuously in background without user prompting.

**Core principle**: If user says "can you save that?", you've already failed.

**Key capabilities**:

- Write/edit Obsidian-compatible bmem files
- Silent session mining and information extraction
- Knowledge graph maintenance (relations, WikiLinks)
- Observation quality enforcement (additive, no duplicates)
- Integration with task skill for task operations

## Format Guide

**@bots/BMEM-OBSIDIAN-GUIDE.md**

Quick template:

```markdown
---
title: Entity Title
permalink: entity-title-slug
type: note
tags:
  - tag1
  - tag2
---

# Entity Title

## Context

Brief 1-3 sentence overview.

## Observations

- [category] Specific atomic fact #inline-tag1 #inline-tag2

## Relations

- relation_type [[Related Entity Title]]
```

## When to Use This Skill

**Invoke automatically when**:

- Creating/editing markdown files in `data/` directory
- User mentions project updates, decisions, insights
- Extracting strategic context from conversations
- User mentions completed work (delegate to task skill for archiving)
- Building knowledge graph connections

**Integration**:

- **task skill**: Delegate all task operations (create, update, archive)
- **bmem skill** (this): Focus on bmem files and session mining

## Critical Rules: Observation Quality

**See [[references/observation-quality-guide.md]] for detailed rules and examples.**

## Session Mining (Silent Background Capture)

**Mine conversations deeply throughout EVERY session:**

### What to Extract

- **Tasks**: Todos, commitments, follow-ups → **Invoke task skill**
- **Projects**: Updates, milestones, deliverables → Update `data/projects/<project>.md` or `data/<project-slug>/`
- **Goals**: Objectives, assessments, priorities → Update goal files in `data/goals/`
- **Context**: People, dates, resources, decisions → Update context files in `data/context/`
- **Completed work**: Mentioned completion → **Invoke task skill** to archive + update task file

### Extraction Patterns

**Deep mining, not keyword matching**:

- "I'll need to prepare for the keynote" → Invoke task skill to create task
- "That process is too bureaucratic" → Strategic context to `data/projects/<project>.md`
- "I'm not sure if we're eligible" → Risk/dependency to project file
- "30% of Sasha's time" → Resource allocation to project file
- "Need to finish X before Y" → Task dependencies → Invoke task skill

**From email processing**:

1. Read email using MCP tool (outlook)
2. Extract action items → Invoke task skill
3. Extract project mentions → Update `data/projects/<project>.md` or `data/<project-slug>/`
4. Extract people/contacts → Update project files
5. Extract deadlines → Pass to task skill
6. Extract strategic importance → Update context files

**From conversations**:

1. Implicit commitments → Invoke task skill
2. Strategic assessments → Update context files
3. Project updates → Update `data/projects/<project>.md` or `data/<project-slug>/`
4. Completed work → Invoke task skill to archive + document extensively in task file
5. Decisions made → Update project/goal files with observations
6. Ruled-out ideas → Document in `data/projects/<project>.md` (why not)

**NEVER**:

- Interrupt user flow to ask clarification
- Wait until conversation end to capture
- Announce that you're capturing information
- Archive/delete/reply to emails (other tools handle that)

### Detail Level: What to Capture Where

**See [[references/detail-level-guide.md]] for comprehensive guidelines on detail levels for task files, project files, and what to capture where.**

## File Operations

### Creating New Files

1. **Check for duplicates** first (search by title/permalink)
2. **Use bmem template** from BMEM-OBSIDIAN-GUIDE.md
3. **Fill frontmatter**: title, permalink, type, tags
4. **Add Context**: 1-3 sentence summary
5. **Extract observations**: Categorized facts with inline tags
6. **Add relations**: Link to related entities (forward references OK)
7. **Save** in appropriate `data/` subdirectory

### Editing Existing Files

1. **Read current file** completely
2. **Preserve existing content**: Don't delete, only enhance
3. **Add new observations**: Append to Observations section
4. **Add new relations**: Append to Relations section
5. **Update frontmatter** if needed (tags, updated timestamp)
6. **Validate**: Ensure no duplication, proper syntax

### File Locations

**Use bmem format in**:

- `data/context/` - Contextual information
- `data/goals/` - Goals and objectives
- `data/projects/` - High-level project metadata (single file per project)
- `data/<project-slug>/` - Project-specific data (multiple files per project)
- `data/playbooks/` - Reusable workflows

**Project data organization**:

- **High-level metadata**: `data/projects/<project>.md` (overview, milestones, strategic context)
- **Project-specific files**: `data/<project-slug>/` (detailed notes, specifications, analysis)

**When creating project-specific subdirectory**:

1. Use project permalink/slug as directory name (e.g., `data/tja/` for TJA Analysis)
2. If `data/projects/<project>.md` exists, keep it for high-level metadata
3. Create project subdirectory for detailed/multi-file content
4. Link between files using WikiLinks: `[[../projects/tja]]` or `[[tja-analysis]]`

**Do NOT use bmem format in**:

- `papers/`, `reviews/`, `talks/` - Academic content
- `templates/` - Templates
- `README.md` files
- `bots/` - Bot instructions (optional bmem)

**Tasks**: Delegate to task skill, never create task files directly.

## Knowledge Graph Maintenance

### Identifying Connections

While mining sessions, actively look for:

- References to existing entities
- New entities that should be linked
- Relationships between concepts
- Project → goal alignment
- People → project associations

### Creating WikiLinks

Add `[[Entity Title]]` syntax when references detected:

```markdown
# Before mining

Working on the content moderation project.

# After mining

Working on [[Content Moderation Research Project]].

## Relations

- part_of [[Platform Governance Research]]
- relates_to [[Automated Moderation Systems]]
```

### Forward References

**Link to entities that don't exist yet - it's OK:**

```markdown
## Relations

- implements [[API Specification]]
- requires [[Database Models]]
```

Even if targets don't exist:

1. Forward reference creates placeholder
2. When target created, relation resolves
3. Graph traversal works bidirectionally

## Integration with Task Skill

**bmem extracts information, task skill manages tasks.**

### When to Invoke Task Skill

**Invoke task skill for**:

- Creating new tasks
- Updating task priority/status
- Archiving completed tasks
- Viewing/displaying task lists

**Example invocation**:

```
# When user mentions action item:
Invoke task skill with:
  operation: create
  title: "Prepare keynote slides"
  priority: 2
  project: "academic-profile"
  due: "2025-11-15"
```

### What bmem Does NOT Do

**NEVER directly**:

- Create task files (task skill does this)
- Update task files (task skill does this)
- Archive tasks (task skill does this)

**bmem ONLY**:

- Extracts task information from sessions
- Invokes task skill with extracted information
- Updates non-task files (projects, goals, context)

## Obsidian Compatibility

**See [[references/obsidian-compatibility.md]] for Obsidian-specific formatting rules (tags, WikiLinks, aliases).**

## Commit and Push

**After creating/editing files, MUST commit and push:**

1. **Check for uncommitted changes**:
   ```bash
   git status
   ```

2. **If changes exist, commit them**:
   ```bash
   git add data/ && git commit -m "update(bmem): [brief summary]

   Captured: [what was added/updated]
   - Projects: [which projects]
   - Goals: [which goals]
   - Context: [which context files]

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

3. **Push to remote**:
   ```bash
   git push
   ```

**If commit/push fails**: Report error to user. DO NOT complete silently with uncommitted changes.

## Quick Reference

**Before writing**:

- [ ] Search for duplicates
- [ ] Choose appropriate `data/` subdirectory
- [ ] Use bmem template structure

**While writing**:

- [ ] Required frontmatter: title, permalink, type
- [ ] H1 heading matches title exactly
- [ ] Context section (1-3 sentences)
- [ ] 3-5+ observations with categories and inline tags
- [ ] Observations ADD new information (not duplicating frontmatter/body)
- [ ] 2-3+ relations with specific types
- [ ] Use hyphens in tags (Obsidian-compatible)
- [ ] Use `[[WikiLinks]]` for entity references

**After writing**:

- [ ] Validate no duplication
- [ ] Verify proper syntax
- [ ] Commit and push changes

**For task operations**:

- [ ] Always invoke task skill
- [ ] Never create task files directly
- [ ] Extract task info from session, pass to task skill

## Success Criteria

This skill succeeds when:

1. **Zero friction** - User never asks "can you save that?"
2. **Automatic capture** - Information extracted silently as mentioned
3. **Quality observations** - No self-referential or duplicate observations
4. **Knowledge graph maintained** - Semantic links kept current
5. **Obsidian-compatible** - Files work perfectly in Obsidian
6. **Tasks delegated** - Task skill invoked for all task operations
7. **Changes persisted** - All data committed and pushed
8. **User feels supported** - "Ideas are magically organized"
