# AI Assistant Guide for Basic Memory

**Source**: https://docs.basicmemory.com/guides/ai-assistant-guide/ (Retrieved 2025-11-18)
**Version**: 0.16.1

## Overview

Basic Memory is a semantic knowledge graph system built on plain-text markdown files stored locally. It enables AI assistants to help users "build structured knowledge that outlasts any particular AI model or session."

## Core Architecture

The system comprises:
- **Plain-text markdown** as the source of truth
- **SQLite indexing** for fast search capabilities
- **MCP integration** for AI interaction
- **Semantic graph** connecting observations and relations

## Essential Workflow

### Project Discovery

Always begin conversations by discovering available projects:

```python
projects = await list_memory_projects()
```

**Critical**: Store the user's project choice for the entire session and pass it explicitly to all tool calls—**no implicit context is maintained between calls**.

### Knowledge Graph Structure

**Entities** (markdown files) contain three core elements:

#### 1. Observations

Categorized facts using syntax: `- [category] content #tag`

**Common categories**:
- `[fact]` - Established information
- `[idea]` - Concepts or proposals
- `[decision]` - Choices made
- `[technique]` - Methods or approaches
- `[requirement]` - Constraints or needs
- `[problem]` - Issues identified
- `[solution]` - Resolutions or fixes
- `[insight]` - Key learnings or realizations

#### 2. Relations

Directional links using syntax: `- relation_type [[Target Entity]]`

**Common relation types**:
- `implements` - This entity implements the target
- `requires` - This entity needs the target
- `extends` - This entity builds upon the target
- `part_of` - This entity belongs to the target
- `contrasts_with` - This entity differs from the target
- `leads_to` - This entity causes or enables the target
- `caused_by` - This entity results from the target
- `relates_to` - Generic connection (use sparingly)

#### 3. Forward References

Relations to entities not yet created automatically resolve when target entities are created. This allows building knowledge graphs incrementally.

## Critical Best Practices

### 1. Search Before Creating

**Always** check for existing notes to avoid duplicates before writing new content.

```python
# Search first
results = await search_notes(query="topic", project=project)
# Only create if not found
if not results:
    await write_note(...)
```

### 2. Permission-Based Recording

**Always ask before recording** conversations or capturing information.

**Pattern**:
- Explain what will be saved
- Describe how it helps future discussions
- Get explicit permission before writing

**Why**: Users need control over what enters their knowledge base.

### 3. Rich Knowledge Graphs

Each note should include:
- **Clear, descriptive title**
- **3-5+ observations minimum** (categorized facts)
- **2-3+ relations minimum** (connections to other entities)
- **Appropriate categories and tags**

**Avoid**: Sparse notes with single observations or no relations—these don't contribute to the knowledge graph's value.

### 4. Exact Entity Titles

**Use exact titles when creating relations** by searching first to ensure proper linking.

**Pattern**:
```python
# Find exact title
results = await search_notes(query="project name", project=project)
exact_title = results[0]['title']  # Use this in relations

# Create relation with exact title
await write_note(
    content=f"- implements [[{exact_title}]]",
    ...
)
```

**Why**: Incorrect titles break the knowledge graph by creating unresolved relations.

### 5. Semantic Precision

Use **specific relation types** and **observation categories** rather than generic connections.

❌ **Poor**:
```markdown
- [note] Something happened
- relates_to [[Other Thing]]
```

✅ **Good**:
```markdown
- [decision] Chose PostgreSQL for persistence layer
- requires [[Database Migration Strategy]]
- caused_by [[Performance Requirements]]
```

### 6. Progressive Elaboration

Build knowledge incrementally across sessions, adding details and connections over time.

**Pattern**:
- Initial capture: Core facts and immediate relations
- Later sessions: Add observations, refine categories, connect to new entities
- Continuous: Update as understanding evolves

### 7. Consistent Organization

Maintain folder structures and descriptive file naming.

**Recommended structure**:
- `specs/` - Specifications and requirements
- `decisions/` - Decision records
- `meetings/` - Meeting notes
- `conversations/` - Discussion summaries
- `implementations/` - Implementation details
- `docs/` - Documentation
- `projects/` - Project overviews
- `people/` - Contact information
- `concepts/` - Abstract ideas and principles

**File naming**: Use descriptive, hyphen-separated names: `api-authentication-spec.md`, not `doc1.md`

## Core Tools

### Writing
- `write_note()` - Create or update notes
- `edit_note()` - Modify existing notes incrementally
- `move_note()` - Reorganize and rename

### Reading
- `read_note()` - Retrieve note with context
- `search_notes()` - Find notes by content
- `build_context()` - Navigate knowledge graph relationships

### Navigation
- `list_directory()` - Browse folder structures
- `recent_activity()` - View recent changes

### Project Management
- `list_memory_projects()` - Discover available projects
- `create_memory_project()` - Initialize new project

### Visualization
- `canvas()` - Create Obsidian canvas diagrams

## Recording Conversations

Capture discussions as **decision records** or **conversation summaries** with observations and relations.

**Pattern for conversation summaries**:

```markdown
# Meeting: Project Kickoff (2025-01-15)

- [decision] Chose microservices architecture
- [requirement] Must support 10k concurrent users
- [problem] Current monolith can't scale horizontally
- [solution] Decompose into user service, auth service, data service

- implements [[System Architecture]]
- requires [[Container Orchestration]]
- part_of [[Q1 2025 Migration Plan]]
```

**Reference previous discussions**:
1. Use `build_context()` to find related conversations
2. Link new notes to establish continuity
3. Build conversation threads over time

## Anti-Patterns to Avoid

❌ **Creating duplicate entities** - Always search first

❌ **Sparse knowledge graphs** - Add multiple observations and relations

❌ **Generic relations** - Use specific relation types

❌ **Recording without permission** - Always ask first

❌ **Incorrect entity titles in relations** - Search for exact titles

❌ **Flat organization** - Use folder structures

❌ **Vague titles** - Be descriptive and specific

## Session Management Pattern

**Start of session**:
```python
# 1. Discover projects
projects = await list_memory_projects()

# 2. Ask user which project
selected_project = user_selects_project(projects)

# 3. Store for session (mental note, not persisted)
# 4. Use explicitly in all tool calls
```

**During session**:
- Pass `project=selected_project` to every tool call
- User can switch: "switch to [project]"
- No implicit context—always explicit

## Building Knowledge Over Time

**Session 1**: Initial capture
- Create project entity
- Add core observations
- Link to immediate dependencies

**Session 2**: Elaboration
- Add implementation details
- Connect to related concepts
- Create decision records

**Session 3**: Refinement
- Update observations with new learnings
- Add cross-references to other projects
- Build out concept hierarchy

**Result**: Rich, interconnected knowledge graph that grows smarter over time.

## Quality Markers

**High-quality notes**:
- Descriptive titles
- 5+ categorized observations
- 3+ typed relations
- Proper folder organization
- Specific categories and relation types
- Connected to broader knowledge graph

**Low-quality notes**:
- Generic titles ("Notes", "Misc")
- Single observation
- No relations
- Root directory placement
- Generic categories (`[note]`)
- Generic relations (`relates_to`)
- Isolated from knowledge graph
