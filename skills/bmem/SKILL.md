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

### What Observations ARE

**Observations ADD new information beyond document body and frontmatter.**

✅ **GOOD observations**:

- Specific, concrete facts
- Atomic (one fact per observation)
- Additive (new information not in frontmatter/body)
- Contextual (enough detail to understand)
- Semantic (enable knowledge graph queries)

❌ **BAD observations**:

- Repeat document body verbatim
- Duplicate frontmatter metadata (due dates, status, type)
- State the obvious ("This is a task")
- Add no new information

### Examples

**❌ BAD** (duplicates frontmatter):

```markdown
---
due: 2025-11-07
type: task
status: inbox
---

## Context

Review student thesis by Nov 7.

## Observations

- [task] Review student thesis by Nov 7 #inbox
- [requirement] Due date: 2025-11-07 #deadline
- [fact] Type: task #type-task
```

**✅ GOOD** (adds new information):

```markdown
---
due: 2025-11-07
type: task
status: inbox
---

## Context

Review Rhyle Simcock's PhD thesis lodgement. Do NOT name examiners in comments.

## Observations

- [fact] Rhyle Simcock is PhD candidate in platform governance #student-rhyle-simcock
- [requirement] Cannot name examiners in comments as student will see them #compliance
- [insight] This is thesis examination stage requiring supervisor approval #phd-process
- [decision] Will focus review on methodology and structure #review-strategy
```

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

**Match detail level to file type and importance:**

#### Task Files (Detailed Documentation)

**When task is completed, document extensively in task file:**

- Technical implementation details
- Design decisions and rationale
- Problems encountered and solutions
- Code/configuration changes made
- Full context for future resumption

**Example (GOOD for task file)**:

```markdown
## Observations

- [solution] Fixed async fixture issue by adding @pytest_asyncio.fixture decorator #pytest #async
- [decision] Chose to use real data instead of mocks for better integration coverage #testing-strategy
- [problem] Initial approach with sync fixtures caused event loop conflicts #technical-debt
- [technique] Used conftest.py for shared fixtures across test modules #test-organization
```

#### Project Files (Strategic Updates Only)

**Location strategy:**

- **High-level metadata**: `data/projects/<project>.md` - Overview, milestones, strategic decisions
- **Detailed content**: `data/<project-slug>/` - Specifications, detailed notes, multi-file projects

**Keep `data/projects/<project>.md` at "weekly standup" level - what you'd say in 30-second verbal update:**

✅ **GOOD for `data/projects/<project>.md`** (strategic/resumption context):

- "Completed TJA scorer validation - strong success (88.9% accuracy)"
- "Framework maintenance (scribe skill, hooks)"
- "Strategic decision: Pivoting from X to Y approach due to Z constraint"
- "Milestone reached: Database migration complete, ready for testing"

❌ **TOO MUCH for `data/projects/<project>.md`** (belongs in task files, `data/<project-slug>/`, or git):

- "Fixed test_batch_cli.py: Reduced from 132 lines to 52 lines, eliminated ALL mocking..."
- "Updated config.json lines 45-67 to add new hook timeout values..."
- "Refactored authentication module to use async/await pattern..."

**Two tests before writing to `data/projects/<project>.md`:**

1. Would this appear in weekly report to supervisor? If NO → omit or put in `data/<project-slug>/` or task file
2. Would I mention this in 30-second standup? If NO → omit or put in `data/<project-slug>/` or task file

#### What NOT to Capture in `data/projects/<project>.md`

**DO NOT capture in high-level project file** (documented in git log, task files, or `data/<project-slug>/`):

- Infrastructure changes → git log or `data/<project-slug>/infrastructure.md`
- Bug fixes → git log or task files
- Code refactoring → git log
- Configuration updates → git log or `data/<project-slug>/config-notes.md`
- Framework improvements → git log
- Routine meetings → omit (unless strategic decision made)
- Minor task updates → task system tracks these
- Implementation details → task files or `data/<project-slug>/`

**DO capture in `data/projects/<project>.md`**:

- Major milestones reached
- Strategic decisions affecting direction
- Resource allocation changes
- Risk assessments and mitigations
- Ruled-out approaches (with reasoning)
- External dependencies and blockers
- Resumption context for long-running work

**Use `data/<project-slug>/` when**:

- Need multiple files for project-specific content
- Detailed specifications, analysis, or documentation
- Technical details beyond "standup level"
- Link back to high-level project file: `[[../projects/<project>]]`

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

### Tags

**Use hyphens in tags** (Obsidian-compatible):

```yaml
tags:
  - academic-writing
  - research-methods
  - platform-governance
```

**Inline tags**:

```markdown
- [insight] 2FA adoption increased security by 40% #security-metrics
```

**Allowed characters**: Letters, numbers, hyphens, underscores, forward slash **NOT allowed**: Spaces, periods, starting with numbers

### WikiLinks

Use `[[Entity Title]]` syntax for all entity references:

```markdown
See [[Platform Governance Research]] for background.

## Relations

- part_of [[Research Program]]
- supports [[World-Class Academic Profile]]
```

**Aliases** (in frontmatter):

```yaml
aliases:
  - Short Name
  - Alternative Name
```

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
