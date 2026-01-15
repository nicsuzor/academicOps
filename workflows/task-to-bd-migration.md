---
id: task-to-bd-migration
category: operations
---

# Task-to-BD Migration Workflow

## Overview

Convert markdown tasks from the legacy `data/tasks/inbox/` format to bd issues. This workflow handles the field mapping, issue creation, and optional cleanup of source files.

**CRITICAL: Data Preservation Rule**

"Convert" means SAFE transfer - ALL information from the source must be preserved in the destination. This is non-negotiable:

- **Every field must be mapped** - title, priority, tags, AND description/context
- **No data loss** - if the source has a Context section, it MUST appear in the bd issue description
- **Checklist items preserved** - include in description or create as subtasks

Skipping descriptions creates issues without context, requiring rework. Always capture the full source content.

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

## Establishing Hierarchies

**Every task belongs somewhere.** Before creating tasks, identify or create the parent epic they belong to. Good hierarchies make work discoverable and show progress at a glance.

### Hierarchy Principle

```
Epic (project/initiative)
├── Task (workstream 1)
│   └── Task (subtask)
├── Task (workstream 2)
└── Task (workstream 3)
```

- **Epics** group related work toward a goal (e.g., "Write TJA paper", "v1.0 Release")
- **Tasks** are actionable items that belong to an epic
- Use `--parent` when creating or `bd update --parent` to assign later

### Creating Hierarchies

```bash
# Create epic first (or find existing one)
bd create "Project Name" -t epic -p P1 -d "Goal description"

# Create tasks under the epic
bd create "Task title" -t task --parent <epic-id>

# Or assign parent to existing tasks
bd update <task-id> --parent <epic-id>

# Bulk assign multiple tasks to an epic
for id in task-1 task-2 task-3; do
  bd update "$id" --parent <epic-id>
done
```

### Finding the Right Parent

Before creating orphan tasks, check for existing epics:

```bash
# List all epics
bd list -t epic

# Search for related work
bd search "project keyword"

# Check if similar tasks already have a parent
bd show <similar-task-id>
```

If no epic exists and you're creating 3+ related tasks, **create an epic first**.

## Setting Up Dependencies

When creating related tasks, **always add dependencies** to show execution order. This enables `bd graph` to visualize the work and helps agents understand what's blocked vs ready.

### Dependency Commands

```bash
# Add dependency: child depends on parent (parent blocks child)
bd dep add <child-id> <parent-id>

# View dependencies for an issue
bd dep list <issue-id>

# Visualize dependency graph
bd graph <issue-id> --compact    # Tree format, one line per issue
bd graph <issue-id> --box        # ASCII boxes (default)
bd graph --all                   # All open issues
```

### When to Add Dependencies

1. **Sequential tasks**: If task B can't start until task A completes
   ```bash
   bd dep add task-B task-A
   ```

2. **Workstream chains**: Link tasks in execution order
   ```bash
   # Validation chain: test → full run → compare → metrics → document
   bd dep add full-run sanity-test
   bd dep add compare full-run
   bd dep add metrics compare
   bd dep add document metrics
   ```

3. **Cross-workstream links**: When one workstream feeds into another
   ```bash
   # Paper depends on validation results
   bd dep add write-results compute-metrics
   # Dashboard depends on tool being ready
   bd dep add build-dataset build-tool
   ```

### Dependency Patterns

| Pattern | Example | Command |
|---------|---------|---------|
| Sequential | A → B → C | `bd dep add B A && bd dep add C B` |
| Convergent | A,B → C | `bd dep add C A && bd dep add C B` |
| Divergent | A → B,C | `bd dep add B A && bd dep add C A` |

### Graph Interpretation

```
LAYER 0 (ready)     ← No dependencies, can start now
LAYER 1             ← Depends on layer 0
LAYER 2             ← Depends on layer 1
...
```

- Issues in the same layer can run in parallel
- Higher layers are blocked until lower layers complete
- Use `bd graph <start-issue>` to see the full chain from any starting point

## Quality Gates

- [ ] No duplicate issues created
- [ ] All required fields mapped correctly
- [ ] Priority preserved (P1-P4)
- [ ] Labels/tags transferred
- [ ] Description includes context
- [ ] Source file handled (archived/deleted/flagged)
- [ ] Dependencies added for related tasks

## Success Metrics

- All inbox tasks have corresponding bd issues
- No data loss (title, description, priority preserved)
- Source files properly handled
- bd state synced: `bd sync`

## Related Workflows

- [[bd-workflow]] - Standard bd issue tracking
- [[batch-processing]] - For bulk migrations
