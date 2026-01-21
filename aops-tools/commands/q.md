---
name: q
category: instruction
description: Queue a task for later execution by creating task(s) - expands prompt to identify discrete tasks
allowed-tools: Task, Bash, Read, Grep
permalink: commands/q
---

# /q - Queue for Later

**Purpose**: Capture work for later execution as task(s). One prompt may result in multiple tasks.

## Workflow

### Step 1: Hydrate the Prompt

Invoke the hydrator agent to expand and analyze the user's request:

```
Task(
  subagent_type="aops-core:prompt-hydrator",
  model="haiku",
  description="Hydrate queue request",
  prompt="Analyze this request for queueing (NOT immediate execution). Identify:\n1. Discrete tasks that should be separate issues\n2. Dependencies between tasks\n3. Appropriate priority and type for each\n4. Context needed for future execution\n\nUser request: <the user's prompt>"
)
```

### Step 2: Check for Existing Tasks

Search for related open tasks to avoid duplicates:

```
mcp__plugin_aops-core_tasks__search_tasks(query="keyword")
mcp__plugin_aops-core_tasks__get_task(id="<task-id>")  # View details of specific task
```

### Step 2.5: Place in Hierarchy (BEFORE creating)

**MUST determine parent BEFORE calling create_task.** Tasks without parents are orphans - they break graph connectivity.

**If you override hydrator guidance** (simplify multiple tasks to one, change decomposition), you STILL must complete this step for your simplified version.

1. **List existing goals/projects**: `mcp__plugin_aops-core_tasks__list_tasks(type="goal")` or `list_tasks(type="project")`
2. **Find the parent** - Every task supports some goal or project. Find it.
3. **If no obvious parent exists** - Create an epic/project first, then create tasks under it
4. **Check for blocking relationships** - If this work depends on other tasks, note `depends_on=[...]`

**No orphans**: `depends_on` links are NOT a substitute for `parent`. A task can have both.

### Step 3: Create Tasks (with placement)

For each discrete task identified by the hydrator, include parent/depends_on determined in Step 2.5:

```
mcp__plugin_aops-core_tasks__create_task(
  title="<task title>",
  type="task",  # or "bug", "action", "project", "goal"
  project="aops",
  parent="<goal-or-project-id>",  # From Step 2.5
  depends_on=["<blocking-task-id>"],  # If applicable
  priority=2,  # 0-4
  body="<context for future execution>"
)
```

If tasks have dependencies:
```
mcp__plugin_aops-core_tasks__create_task(
  title="<dependent task>",
  depends_on=["<blocking-task-id>"],
  ...
)
```

## Priority Levels

| Priority | Meaning                    |
| -------- | -------------------------- |
| 0 / P0   | Critical (urgent/blocking) |
| 1 / P1   | High (important, soon)     |
| 2 / P2   | Medium (default)           |
| 3 / P3   | Low (nice to have)         |
| 4 / P4   | Backlog (someday/maybe)    |

## Task Types

- `action` - Small, discrete work item (default for leaf tasks)
- `task` - General work item
- `project` - Collection of related tasks
- `goal` - High-level objective

## Key Rules

- **Always hydrate first** - The prompt may contain multiple tasks
- **Check for duplicates** - Search existing tasks before creating
- **Place in hierarchy** - Connect to goals/projects; no floating orphans
- **Capture context** - Include enough detail for future execution without current session
- **Set dependencies** - If tasks must be done in order, use `depends_on`
- **DO NOT execute** - Only queue; execution happens later via `/pull` or manual claim

## Examples

**Single task**:
```
/q fix the typo in README.md
```
→ Creates 1 task

**Multiple tasks in one prompt**:
```
/q refactor the auth module and add unit tests for it
```
→ Hydrator identifies 2 tasks: (1) refactor auth, (2) add tests (depends on #1)
→ Creates 2 tasks with dependency
