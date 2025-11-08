---
name: scribe
description: |
  Silently extracts information from session history, mines it for inclusion into
  $ACA/data database, uses smarts to select information, finds links with existing
  context, and intelligently maintains the knowledge graph. Deep understanding of
  Basic Memory (bmem) concepts and file writing. Invokes tasks skill for task
  creation/management.
permalink: aops/skills/scribe/skill
---

# Scribe: Session Mining & Knowledge Graph Maintenance

## Overview

Like a scribe who continuously records important information, this skill operates silently to extract information from conversations, maintain the knowledge graph in Basic Memory format, and ensure semantic structure across all markdown files.

**Core principle**: If the user says "can you save that?", you've already failed.

**Key capabilities**:
- Session mining and information extraction
- Basic Memory file writing and conversion
- Knowledge graph maintenance
- Observation quality enforcement
- Strategic context capture
- Invokes tasks skill for task management

## When to Use This Skill

**Invoke automatically when**:
- Creating or editing markdown files in knowledge base
- Mining session history for information
- Converting regular markdown to Basic Memory format
- Extracting strategic context from conversations
- User mentions completed work (for accomplishments)
- Building/maintaining knowledge graph connections

**Integration**:
- **tasks skill**: Invoke for task creation, updates, archiving
- **scribe skill** (this): Focus on bmem files and session mining

## Basic Memory Syntax

@references/bmem-syntax.md

Quick reference:

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

- [category] New information not in body/frontmatter #tags

## Relations

- relation_type [[Entity Title]]
```

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

### Conversion Strategy

When file lacks frontmatter:

1. Extract title from first `# Heading` or filename
2. Generate permalink from title (lowercase, spaces → hyphens)
3. Infer type from directory:
   - `data/tasks/` → task
   - `data/projects/` → project
   - `data/goals/` → goal
   - `docs/` → spec
   - Default → note
4. Preserve existing tags if present
5. Add created timestamp (current time)

## Observation Writing (CRITICAL)

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

**Problems**: First observation repeats context verbatim. Due date already in frontmatter. Type already in frontmatter. "todo" is meaningless.

**✅ GOOD** (adds new information, specific, semantic):

```markdown
---
due: "2025-11-07"
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

**Why this is good**: Each observation adds NEW information. No duplication of frontmatter. Specific details about people, constraints, process. Semantic tags.

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
- ✅ `[fact] Research involves 50 participants across 3 universities #scope`

## Link Syntax Enforcement

### Entity References

Replace all informal references with explicit links:

```markdown
# Before
See the authentication system documentation for details.

# After
See [[Authentication System]] for details.
```

### Relation Syntax

When file has clear relationships, add `## Relations` section:

```markdown
## Relations

- relation_type [[Target Entity]]
```

**Common relations**: relates_to, implements, requires, extends, part_of, caused_by, leads_to

**Forward references are OK**: You can reference entities that don't exist yet. Basic Memory creates placeholders.

## Session Mining Techniques

### Automatic Background Capture

**Mine conversations deeply** throughout EVERY session:

**What to extract**:
- **Tasks**: Explicit todos, implicit future actions, commitments, follow-ups → Invoke tasks skill
- **Projects**: Updates, new ideas, milestones, deliverables → Update project files
- **Goals**: Objectives, assessments, priorities, theories of change → Update goal files
- **Context**: People, dates, resources, risks, decisions, ruled-out options → Update context files
- **Completed work**: Mentioned completion → Invoke tasks skill to archive + update accomplishments

**Deep mining, not keyword matching**:
- "I'll need to prepare for the keynote next month" → Invoke tasks skill to create task
- "That process is too bureaucratic" → Strategic context to project file
- "I'm not sure if we're eligible" → Risk/dependency to project file
- "30% of Sasha's time" → Resource allocation to project file
- "Need to finish X before Y" → Task dependencies → Invoke tasks skill

### Extraction Patterns

**From email processing**:
1. Read email using MCP tool (outlook)
2. Extract action items → Invoke tasks skill
3. Extract project mentions → Update project files
4. Extract people/contacts → Update project files
5. Extract deadlines → Pass to tasks skill
6. Extract strategic importance → Update context files

**From conversations**:
1. Implicit commitments → tasks skill
2. Strategic assessments → context files
3. Project updates → project files
4. Completed work → tasks skill to archive + accomplishments
5. Decisions made → project/goal files with observations
6. Ruled-out ideas → project files (document why not)

**NEVER**:
- Interrupt user flow to ask for clarification
- Wait until conversation end to capture information
- Announce that you're capturing information
- Archive/delete/reply to emails (other skills handle that)

## Knowledge Graph Maintenance

### Identifying Connections

**While mining sessions**, actively look for:
- References to existing entities
- New entities that should be linked
- Relationships between concepts
- Project → goal alignment
- Task → project membership
- People → project associations

### Creating Links

**Add `[[Entity Title]]` syntax** when references detected:

```markdown
# Before mining
Working on the content moderation project.

# After mining
Working on [[Content Moderation Research Project]].

## Relations
- part_of [[Platform Governance Research]]
- relates_to [[Automated Moderation Systems]]
```

### Maintaining Consistency

**Ensure**:
- Entity titles are consistent across references
- Forward references created when needed
- Bidirectional relations added where appropriate
- Tags are semantic and discoverable
- Observations don't duplicate metadata

## Integration with Tasks Skill

**scribe extracts information, tasks manages tasks**:

### When to Invoke Tasks Skill

**Invoke tasks skill for**:
- Creating new tasks (with duplicate check)
- Updating task priority
- Updating task status
- Archiving completed tasks
- Checking task strategic alignment
- Viewing/displaying task lists

**Example invocation pattern**:

```
# When user mentions action item:
Invoke tasks skill with:
  operation: create
  title: "Prepare keynote slides"
  priority: 2
  project: "academic-profile"
  due: "2025-11-15"
  summary: "Create slides for conference X. Focus on accountability frameworks."
```

### What Scribe Does NOT Do

**NEVER directly**:
- Create task files (tasks skill does this)
- Update task files (tasks skill does this)
- Archive tasks (tasks skill does this)
- Run task scripts (tasks skill does this)

**Scribe ONLY**:
- Extracts task information from sessions
- Invokes tasks skill with extracted information
- Updates non-task files (projects, goals, context)

## Accomplishments Writing

### When to Capture

**Capture to accomplishments.md when**:
1. Task completion (invoke tasks skill to archive task, then write to accomplishments)
2. Strategic decisions affecting priorities
3. Non-task work that's significant enough for weekly standup

### Detail Level: "Weekly Standup Report"

Write what you'd say in a 30-second verbal update:

**✅ GOOD examples**:
- "Completed TJA scorer validation - strong success (88.9% accuracy, exceeds targets)"
- "Framework maintenance (scribe skill, hooks) d346cd6 811c407"
- "Ad-hoc student meeting (thesis revision feedback)"

**❌ TOO MUCH** (implementation details belong in git):
- "Fixed test_batch_cli.py: Reduced from 132 lines to 52 lines (60% reduction), eliminated ALL mocking..."

### What NOT to Capture

**DO NOT capture** (documented in git log):
- Infrastructure changes
- Bug fixes
- Code refactoring
- Configuration updates
- Framework improvements
- Routine meetings (unless strategic decision made)
- Minor task updates (task system tracks these)

### Two Tests Before Writing

1. Would this appear in weekly report to supervisor? If NO → omit
2. Would I mention this in 30-second standup? If NO → omit

### Writing Location

**ALWAYS write to** `$AO/data/context/accomplishments.md` (personal repo: @nicsuzor/writing)

**NEVER write to** project repos (buttermilk/data/, bot/data/, etc.)

## File Operations

### Creating New Files

1. **Use template** (`@assets/bmem-template.md`)
2. **Fill frontmatter**: title, permalink, type, tags
3. **Add context**: 1-3 sentence summary
4. **Extract observations**: Categorized facts with tags
5. **Add relations**: Link to related entities
6. **Save** in appropriate directory

### Converting Existing Files

1. **Read current file** completely
2. **Check frontmatter**: Missing → Add. Incomplete → Fill. Malformed → Fix.
3. **Scan for observations**: Extract facts from prose
4. **Identify entity references**: Convert to `[[Entity Title]]` syntax
5. **Preserve existing content**: Don't delete, only enhance
6. **Validate**: Frontmatter, observations, relations syntax

### File Exclusions

**DO NOT enforce Basic Memory syntax** on:
- `.github/workflows/*.yml`
- `.claude/settings.json`
- `.gitignore`, `.gitattributes`
- `package.json`, `pyproject.toml`
- `LICENSE`, `COPYRIGHT`
- Files with `<!-- NO_BMEM -->` comment at top

## Commit and Push (MANDATORY)

**Before finishing, MUST commit and push all changes**:

1. **Check for uncommitted changes**:
   ```bash
   cd $AO && git status
   ```

2. **If changes exist, commit them**:
   ```bash
   cd $AO && git add data/ && git commit -m "update(scribe): [brief summary]

   Captured: [list what was added/updated]
   - Projects: [which projects updated]
   - Goals: [which goals updated]
   - Context: [which context files updated]

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

3. **Push to remote**:
   ```bash
   cd $AO && git push
   ```

**If commit/push fails**: Report error to user. DO NOT complete silently with uncommitted changes.

## Critical Rules

**NEVER**:
- Skip frontmatter validation
- Create files without `title`/`permalink`/`type`
- Add observations without categories
- Add observations that duplicate frontmatter
- Use single brackets for entity references
- Modify excluded config files
- Create/update/archive tasks directly (invoke tasks skill)
- Miss completed work mentions (invoke tasks skill + update accomplishments)
- Write implementation details to accomplishments (keep "standup level")

**ALWAYS**:
- Extract information IMMEDIATELY as mentioned
- Validate frontmatter completeness
- Use `[[Entity Title]]` syntax for references
- Categorize observations with `[category]`
- Ensure observations ADD new information (not duplicate)
- Add tags for discoverability
- Invoke tasks skill for task operations
- Match detail level to file type (accomplishments = standup, projects = resumption context)
- Commit and push all changes before completing

## Success Criteria

This skill succeeds when:
1. **Zero friction** - User never asks "can you save that?"
2. **Automatic capture** - Information extracted silently as mentioned
3. **Quality observations** - No self-referential or duplicate observations
4. **Knowledge graph maintained** - Semantic links kept current
5. **Tasks delegated** - tasks skill invoked for all task operations
6. **Changes persisted** - All data committed and pushed
7. **User feels supported** - "Ideas are magically organized"
