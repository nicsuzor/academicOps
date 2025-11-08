---
name: context
description: Search our personal knowledge graph and be the user's second brain. Activate this skill FREQUENTLY and PROACTIVELY; it is your ONLY way to access your memories.
license: Apache 2.0
permalink: skills/context
---

## Core Operations

Use the 'Basic Memory' (bmem) MCP tool to access memories and understand the context for your work.

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
