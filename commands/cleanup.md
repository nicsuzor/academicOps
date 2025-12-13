---
name: cleanup
description: Aggressively clean knowledge base directory - delete junk, extract facts before deletion, keep substantive notes.
permalink: aops/commands/cleanup
tools:
  - Task
  - Bash
  - TodoWrite
  - AskUserQuestion
  - Read
  - Edit
  - Glob
  - Grep
  - mcp__bmem__write_note
  - mcp__bmem__edit_note
  - mcp__bmem__search_notes
  - mcp__bmem__read_note
---

# Knowledge Base Cleanup

**Invoke skill first**: `Skill(skill="bmem-cleanup")` to load classification criteria.

## Input

User provides: `$ARGUMENTS` (directory path or pattern, e.g., `data/archive/` or `data/contacts/*.md`)

## Workflow

### 1. Discovery

```bash
find <path> -name "*.md" -type f | wc -l
```

Show user the count and sample files.

### 2. Process in Batches

Spawn 4-8 parallel Task agents with subagent_type="general-purpose".

Each agent classifies files as DELETE, EXTRACT_DELETE, or KEEP per skill criteria.

### 3. Collect Questions

For EXTRACT_DELETE files with unclear targets, batch questions to user (max 4 per AskUserQuestion call).

### 4. Execute

- DELETE: `git rm "<file>"`
- EXTRACT_DELETE: Append facts to target via `mcp__bmem__edit_note()`, then `git rm`
- KEEP: Skip

### 5. Commit

```bash
git add -A && git commit -m "cleanup(kb): remove N files, extract M facts"
```

### 6. Report

Summary of actions taken.
