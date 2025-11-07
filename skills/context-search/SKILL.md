---
name: context-search
description: Semantic search and context retrieval via Basic Memory MCP. Searches tasks, projects, goals by content/tags/relations and builds context from memory URIs. Used by other skills for discovery.
license: Apache 2.0
permalink: aops/skills/context-search/skill
---

# Context Search

## Framework Context

@resources/AXIOMS.md

## Overview

Provides semantic search interface to Basic Memory knowledge base. Other skills invoke this to discover existing tasks, find related projects/goals, and build context before operations.

**Core principle**: Semantic search > manual Glob/Grep. Let BM's graph understand relationships.

## When to Use This Skill

Invoke context-search when you need to:

- **Find existing tasks** before creating duplicates
- **Search by semantic meaning** not just keywords
- **Discover related entities** via BM relations
- **Build context** from memory:// URIs
- **Check project/goal linkages** for alignment

**Do NOT use for**:

- Writing files (use bmem-ops)
- Task operations (use tasks)
- Direct file operations (use Read/Write/Edit)

## Core Operations

### 1. Search Tasks

**Find tasks by content, tags, or relations:**

```bash
# Use BM MCP search_notes with type filter
mcp__bm__search_notes(
  query="keynote preparation",
  types=["task"],
  project="academic-profile"
)
```

**Returns**: Task IDs, titles, status, priority for matching results.

### 2. Build Context from Memory URI

**Load context for a memory:// path:**

```bash
# Get full context including relations
mcp__bm__build_context(
  url="memory://projects/academic-profile",
  depth=1,
  timeframe="7d"
)
```

**Returns**: Entity content + related entities within depth/timeframe.

### 3. Find Related Entities

**Discover connections via BM relations:**

```bash
# Find all tasks for a project
mcp__bm__search_notes(
  query="part_of [[Academic Profile]]",
  types=["task"]
)
```

**Returns**: All tasks with relation to target project.

### 4. Check for Duplicates

**Before creating new task, search for existing:**

```bash
# Search by semantic similarity
mcp__bm__search_notes(
  query="prepare slides conference",
  types=["task"],
  search_type="text"  # Semantic search
)
```

**Returns**: Similar existing tasks to avoid duplication.

## Query Patterns

### By Status/Priority

```bash
# Find high-priority inbox tasks
mcp__bm__search_notes(
  query="priority-p1 status-inbox",
  types=["task"]
)
```

### By Project

```bash
# All tasks for specific project
mcp__bm__search_notes(
  query="project:automod-demo",
  types=["task"]
)
```

### By Due Date

```bash
# Tasks with upcoming deadlines
mcp__bm__search_notes(
  query="deadline",
  types=["task"],
  after_date="2025-11-01"
)
```

### By Relations

```bash
# Tasks linked to specific goal
mcp__bm__search_notes(
  query="part_of [[Accountability]]",
  types=["task"]
)
```

## Return Format

All searches return structured data for consumption by other skills:

```json
{
  "results": [
    {
      "id": "task-id",
      "title": "Task title",
      "permalink": "tasks/task-id",
      "status": "inbox",
      "priority": 2,
      "project": "project-slug",
      "excerpt": "Matched content..."
    }
  ],
  "count": 10
}
```

## Integration with Other Skills

**tasks** uses context-search to:

- Find duplicates before creation
- Discover related tasks
- Check project alignment

**scribe** (subagent) uses context-search to:

- Load strategic context
- Find existing entities
- Verify relationships

**bmem-ops** may use context-search to:

- Find forward references
- Validate entity titles
- Check relation targets

## BM MCP Tools Reference

Core tools from Basic Memory MCP:

- `search_notes()` - Semantic search across knowledge base
- `build_context()` - Load entity with relations
- `read_note()` - Get specific entity by identifier
- `list_directory()` - Browse folder structure
- `get_similar_documents()` - Find related by similarity

See `~/.config/Claude/mcp_settings.json` for complete BM MCP tool list.

## Best Practices

**Search Strategy**:

1. Try semantic search first (`search_type="text"`)
2. Fall back to exact match if needed
3. Use type filters to narrow results
4. Combine tags and content queries

**Performance**:

- Limit results with `page_size` parameter
- Use `timeframe` to scope recent activity
- Set appropriate `depth` for relation traversal
- Cache results when repeating queries

**Result Handling**:

- Always check for empty results
- Present matches to calling skill
- Let calling skill decide on actions
- Don't modify entities directly

## Critical Rules

**NEVER**:

- Write or modify files directly
- Make decisions about task operations
- Create tasks (delegate to tasks)
- Bypass BM MCP (don't use Glob/Grep for BM data)

**ALWAYS**:

- Use BM MCP tools for search
- Return structured results
- Let calling skill interpret results
- Respect type filters and scoping

## Quick Reference

**Find existing tasks**:

```bash
mcp__bm__search_notes(query="keywords", types=["task"])
```

**Check duplicates**:

```bash
mcp__bm__search_notes(query="title text", types=["task"], search_type="text")
```

**Get project context**:

```bash
mcp__bm__build_context(url="memory://projects/name", depth=1)
```

**Find by relation**:

```bash
mcp__bm__search_notes(query="part_of [[Project]]", types=["task"])
```
