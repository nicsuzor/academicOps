---
id: task-to-bd-migration
category: operations
---

# Task-to-BD Migration Workflow

## Overview

Convert markdown tasks from the legacy `data/tasks/inbox/` format to bd issues. This workflow handles the field mapping, issue creation, and optional cleanup of source files.

## When to Use

- Migrating legacy markdown tasks to bd
- Bulk importing tasks from external sources
- Converting captured tasks to actionable bd issues

## When NOT to Use

- Tasks already exist in bd (check first with `bd search`)
- Quick captures (use `bd q` directly instead)
- Tasks that don't require tracking

## Source Format

Markdown tasks have this structure:

```yaml
---
title: Task title
priority: 3          # 1-4 (1=highest)
project: aops
status: inbox
tags:
- framework
- tools
classification: Enhancement  # Research, Enhancement, Bug, etc.
---
# Task title

## Context
Description of the task...

## Observations
- [task] ... #status-inbox #priority-p3

## Checklist
- [ ] Subtask item
```

## Field Mapping

| Markdown Field    | BD Field     | Transformation                          |
|-------------------|--------------|------------------------------------------|
| `title`           | title        | Direct copy                              |
| `priority`        | `-p`         | 1→P1, 2→P2, 3→P3, 4→P4                   |
| `tags`            | `-l`         | Comma-separated labels                   |
| `classification`  | `-t` or `-l` | Enhancement→feature, Bug→bug, else label |
| Context section   | `-d`         | Description body                         |
| Checklist items   | Description  | Include in description or create subtasks|

## Steps

### 1. Check for duplicates ([[bd-workflow]])

Before creating, search for existing issues:

```bash
bd search "keyword from title"
bd list | grep -i "partial title"
```

If issue exists, skip or update instead of creating duplicate.

### 2. Read and parse markdown task

Read the source file and extract:
- YAML frontmatter fields
- Context section content
- Any checklist items

**Example extraction:**
```
File: 20251218-glob-grep-venv-exclusion.md
Title: Exclude .venv from Glob/Grep by default
Priority: 3 → P3
Tags: framework, tools, search, performance
Classification: Enhancement → type: feature
Context: Framework improvement: Exclude .venv directories...
```

### 3. Create bd issue

Use `bd create` with mapped fields:

```bash
bd create "Title from markdown" \
  -p P3 \
  -t feature \
  -l "tag1,tag2,tag3" \
  -d "Description from Context section.

Checklist:
- [ ] Item from original checklist"
```

**Classification mapping:**
- Enhancement → `-t feature`
- Bug → `-t bug`
- Research → `-t task -l research`
- Chore → `-t chore`
- Default → `-t task`

### 4. Verify creation

Confirm issue was created successfully:

```bash
bd show <issue-id>
```

Verify:
- Title matches
- Priority is correct
- Labels are present
- Description contains context

### 5. Archive or delete source file (optional)

After successful migration:

**Option A: Move to archived**
```bash
mv data/tasks/inbox/filename.md data/tasks/archived/
```

**Option B: Delete if bd is source of truth**
```bash
rm data/tasks/inbox/filename.md
```

**Option C: Leave in place** (for audit trail during transition)

## Batch Processing

For bulk migration, use [[batch-processing]] workflow:

1. List all inbox tasks: `ls data/tasks/inbox/`
2. Create bd issues in parallel (4-8 concurrent)
3. Verify all created: `bd list --limit 0 | wc -l`
4. Archive source files in batch

**Script pattern:**
```bash
for f in data/tasks/inbox/*.md; do
  # Parse and create issue
  # Log results
done
```

## Quality Gates

- [ ] No duplicate issues created
- [ ] All required fields mapped correctly
- [ ] Priority preserved (P1-P4)
- [ ] Labels/tags transferred
- [ ] Description includes context
- [ ] Source file handled (archived/deleted/flagged)

## Success Metrics

- All inbox tasks have corresponding bd issues
- No data loss (title, description, priority preserved)
- Source files properly handled
- bd state synced: `bd sync`

## Related Workflows

- [[bd-workflow]] - Standard bd issue tracking
- [[batch-processing]] - For bulk migrations
