---
name: remember
description: Write knowledge to markdown AND sync to memory server. MUST invoke - do not write markdown directly.
allowed-tools: Read,Write,Edit,mcp__memory__store_memory
version: 1.0.0
---

# Remember Skill

Persist knowledge to the framework's memory system.

## Why You MUST Invoke This Skill

You know how to write markdown. But there's a **sync step you cannot do directly**.

The framework uses a memory server that indexes `$ACA_DATA/`. When you write markdown, you must ALSO add it to the memory server for semantic search to work. This skill handles both steps.

**If you skip this skill**: The markdown file exists but isn't searchable. Future agents won't find it via `mcp__memory__retrieve_memory`.

## When to Use

- Capturing a decision, learning, or observation
- Recording something that should persist across sessions
- Any time you would write to `$ACA_DATA/` for knowledge purposes

## File Locations

| Content | Location |
|---------|----------|
| General notes | `$ACA_DATA/context/` |
| Goals | `$ACA_DATA/goals/` |
| Project metadata | `$ACA_DATA/projects/<name>.md` |
| Project details | `$ACA_DATA/projects/<name>/` |
| Learning/patterns | `$ACA_DATA/projects/aops/learning/` |
| Session notes | `$ACA_DATA/sessions/` |
| Tasks | Delegate to [[tasks]] skill |

**DO NOT create arbitrary directories** (e.g., `tech/`, `dev/`, `tools/`). Project-related notes go in `projects/<project-name>/`.

## Workflow

1. **Search BOTH sources**:
   - Memory server: `mcp__memory__retrieve_memory(query="topic keywords")`
   - Specs directory: `Glob(pattern="$ACA_DATA/projects/*/specs/*.md")` then grep for topic
2. **If match found in EITHER**: AUGMENT existing file (don't create new)
3. **If no match in either**: Create new TOPICAL file (not session/date file)
4. **Write markdown file** with proper frontmatter:
```markdown
---
title: [Descriptive Title]
type: [note|learning|decision]
tags: [relevant, tags]
created: YYYY-MM-DD
---

# Title

Content here.
```

3. **Add to memory server**:
```
mcp__memory__store_memory(
  content="[Full content or key excerpt]",
  metadata={
    "tags": "tag1,tag2",
    "type": "note",
    "source": "[file path]"
  }
)
```

## Arguments

- `content`: What to remember (required)
- `type`: note | learning | decision (default: note)
- `tags`: Comma-separated tags for categorization

## Output

Report:
- File written: `[path]`
- Memory stored: `[hash or confirmation]`

## Workflows

- [[workflows/capture]] - Session mining and silent extraction
- [[workflows/validate]] - Check format compliance
- [[workflows/prune]] - Clean low-value files

## Open Questions

We don't yet know the full sync mechanism between markdown files and the memory server. This skill will be updated as we learn. For now: write markdown, then store in memory.
