# bmem: Basic Memory Knowledge Graph Integration

## Authoritative Domain Knowledge

**System**: Basic Memory 0.16.1 (MCP-enabled semantic knowledge graph)
**Data Format**: Markdown entities with YAML frontmatter (Obsidian-compatible)
**Storage Location**: `data/` hierarchy in each repository
**Entity Structure**: `data/{entity-type}/{entity-slug}.md`
**Entity Types**: note, project, person, event, concept, relation
**Required Fields**: title, permalink, type
**Optional Fields**: tags, related, created, modified, status
**Linking**: WikiLinks `[[entity-slug]]` for cross-references
**Relations**: Expressed via frontmatter fields (related:, part-of:, etc.) and WikiLinks in content
**Write Access**: bmem MCP tools ONLY - agents must not write data/ files directly
**Cross-Repo**: Each repository has independent data/ hierarchy
**MCP Integration**: Access via `mcp__bmem__*` tools for all operations

## Technical References (Load Just-in-Time)

**Basic Memory System Documentation**:
- [[../../framework/references/basic-memory-sync-guide.md]] - Database sync, file management, handling deletions
- [[../../framework/references/basic-memory-mcp-tools.md]] - Complete MCP tools reference
- [[../../framework/references/basic-memory-ai-guide.md]] - AI assistant best practices

**bmem Skill-Specific Guides**:
- [[references/obsidian-format-spec.md]] - Full Obsidian format specification
- [[references/observation-quality-guide.md]] - Observation quality rules
- [[references/detail-level-guide.md]] - Detail level guidelines (tasks vs projects)
- [[references/obsidian-compatibility.md]] - Obsidian-specific formatting

**Load references when needed for**:
- MCP tool usage questions → basic-memory-mcp-tools.md
- Sync/database issues → basic-memory-sync-guide.md
- Best practices/patterns → basic-memory-ai-guide.md
- Format questions → obsidian-format-spec.md
- Quality issues → observation-quality-guide.md

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

**See [[references/obsidian-format-spec.md]] for complete format specification.**

**Quick reference**:
- YAML frontmatter: title, permalink, type, tags
- H1 heading matches title
- Context section (1-3 sentences)
- Observations with categories: `- [category] fact #tag`
- Relations with types: `- relation_type [[Target]]`

## When to Use This Skill

**Invoke automatically when**:

- Creating/editing markdown files in `data/` directory
- User mentions project updates, decisions, insights
- Extracting strategic context from conversations
- User mentions completed work (delegate to task skill for archiving)
- Building knowledge graph connections

**Integration**:

- **task skill**: Delegate all task operations (create, update, archive)
- **bmem skill** (this): Focus on bmem files and session mining via MCP tools

## MCP Tools Usage

**CRITICAL**: All bmem operations use MCP tools (`mcp__bmem__*`). Never write data/ files directly.

**Project management**:
- Start every session with `mcp__bmem__list_memory_projects()` to discover projects
- Store user's project choice for entire session
- Pass `project` parameter explicitly to all tool calls

**Core operations**:
- `mcp__bmem__write_note()` - Create/update notes
- `mcp__bmem__edit_note()` - Incremental edits (append, prepend, find_replace)
- `mcp__bmem__read_note()` - Read with context
- `mcp__bmem__search_notes()` - Full-text search
- `mcp__bmem__build_context()` - Navigate knowledge graph

**See [[../../framework/references/basic-memory-mcp-tools.md]] for complete tool reference.**

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

## Database Sync

**Basic Memory handles sync automatically** via real-time file watching.

**Check sync status**: `mcp__bmem__sync_status()` - No parameters needed

**See [[../../framework/references/basic-memory-sync-guide.md]] for**:
- How sync works
- Handling deleted files
- Database reset procedures
- .gitignore support

## Quick Reference

**Session start**:

- [ ] Call `mcp__bmem__list_memory_projects()` to discover projects
- [ ] Ask user which project to use
- [ ] Store project choice for session

**Before writing**:

- [ ] Search for duplicates with `mcp__bmem__search_notes()`
- [ ] Choose appropriate folder
- [ ] Use bmem template structure (see [[references/obsidian-format-spec.md]])

**While writing** (via `mcp__bmem__write_note()`):

- [ ] Required parameters: title, content, folder, project
- [ ] Required frontmatter: title, permalink, type
- [ ] H1 heading matches title exactly
- [ ] Context section (1-3 sentences)
- [ ] 3-5+ observations with categories and inline tags
- [ ] Observations ADD new information (not duplicating frontmatter/body)
- [ ] 2-3+ relations with specific types
- [ ] Use hyphens in tags (Obsidian-compatible)
- [ ] Use `[[WikiLinks]]` for entity references

**For incremental edits**:

- [ ] Use `mcp__bmem__edit_note()` with operation: append, prepend, find_replace, or replace_section
- [ ] More efficient than rewriting entire note

**For task operations**:

- [ ] Always invoke task skill
- [ ] Never use bmem MCP tools for tasks
- [ ] Extract task info from session, pass to task skill

## Success Criteria

This skill succeeds when:

1. **Zero friction** - User never asks "can you save that?"
2. **Automatic capture** - Information extracted silently as mentioned
3. **Quality observations** - No self-referential or duplicate observations (see [[references/observation-quality-guide.md]])
4. **Knowledge graph maintained** - Semantic links kept current via relations
5. **Obsidian-compatible** - Files work perfectly in Obsidian
6. **Tasks delegated** - Task skill invoked for all task operations
7. **MCP tools used correctly** - All operations via `mcp__bmem__*` tools with explicit project parameter
8. **User feels supported** - "Ideas are magically organized"

## Best Practices from Basic Memory

**See [[../../framework/references/basic-memory-ai-guide.md]] for complete guide.**

**Key principles**:
- Always search before creating (avoid duplicates)
- Ask permission before recording conversations
- Build rich knowledge graphs (3-5+ observations, 2-3+ relations)
- Use exact entity titles in relations (search first)
- Use semantic precision (specific relation types, not generic)
- Progressive elaboration (build knowledge incrementally)
- Consistent organization (maintain folder structures)
