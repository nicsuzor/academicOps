---
name: bmem
description: Knowledge base operations - capture, validate, prune. Routes to workflows for specific tasks.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,mcp__bmem__*
version: 2.0.0
permalink: skills-bmem-skill
---

# bmem Knowledge Base Skill

## When to Invoke

| User wants to... | Workflow |
|------------------|----------|
| Save info, mine session, create notes | [[workflows/capture.md]] |
| Fix format, check compliance, repair links | [[workflows/validate.md]] |
| Delete low-value files, declutter | [[workflows/prune.md]] |

## Core Rules

1. **MCP tools only**: All bmem operations use `mcp__bmem__*` tools. Never write `data/` files directly.
2. **Project parameter**: ALWAYS use `project="main"` in all bmem MCP calls.
3. **Approved categories only**: See [[references/approved-categories-relations.md]] before writing.

## Mental Model

**bmem memories ARE markdown files. One thing, not two.**

- `mcp__bmem__write_note()` creates a markdown file in `data/`
- Database is an INDEX for search, not separate storage
- Editing markdown = editing knowledge base

## Quick Reference

### MCP Tools

| Tool | Purpose |
|------|---------|
| `write_note` | Create/update note |
| `edit_note` | Incremental edits (append, prepend, find_replace) |
| `read_note` | Read with context |
| `search_notes` | Semantic search |
| `build_context` | Navigate knowledge graph |

### File Locations

| Content | Location |
|---------|----------|
| General notes | `data/context/` |
| Goals | `data/goals/` |
| Project metadata | `data/projects/<name>.md` |
| Project details | `data/projects/<name>/` |
| Tasks | Delegate to task skill |

**DO NOT create arbitrary directories** (e.g., `tech/`, `dev/`, `tools/`). Project-related notes go in `projects/<project-name>/`.

## References (Load When Needed)

- [[references/approved-categories-relations.md]] - **MANDATORY before writing**
- [[references/obsidian-format-spec.md]] - Full format specification
- [[references/observation-quality-guide.md]] - Quality rules
- [[references/detail-level-guide.md]] - What to capture where

## Workflows

### Capture (Default)

Session mining, note creation, knowledge extraction.

**Invoke**: Automatically during sessions, or when user mentions saving/capturing.

**Details**: [[workflows/capture.md]]

### Validate

Format compliance, link fixing, location checking.

**Invoke**: "fix bmem", "validate files", "check compliance"

**Details**: [[workflows/validate.md]]

### Prune

Value-based cleanup - delete low-value files, extract facts first.

**Invoke**: "clean up", "declutter", "prune knowledge base"

**Details**: [[workflows/prune.md]]
