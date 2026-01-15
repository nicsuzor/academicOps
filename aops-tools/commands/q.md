---
name: q
category: instruction
description: Queue a task for later execution by creating bd issue(s) - expands prompt to identify discrete tasks
allowed-tools: Task, Bash, Read, Grep
permalink: commands/q
---

# /q - Queue for Later

**Purpose**: Capture work for later execution as bd issue(s). One prompt may result in multiple issues.

## Workflow

### Step 1: Hydrate the Prompt

Invoke the hydrator agent to expand and analyze the user's request:

```
Task(
  subagent_type="aops-core:prompt-hydrator",
  model="haiku",
  description="Hydrate queue request",
  prompt="Analyze this request for queueing (NOT immediate execution). Identify:\n1. Discrete tasks that should be separate bd issues\n2. Dependencies between tasks\n3. Appropriate priority and type for each\n4. Context needed for future execution\n\nUser request: <the user's prompt>"
)
```

### Step 2: Check for Existing Issues

Search for related open issues to avoid duplicates:

```bash
bd list --status=open | grep -i "keyword"
bd show <issue-id>  # View details of specific issue
```

### Step 3: Create bd Issues

For each discrete task identified by the hydrator:

```bash
bd create "<task title>" --type=<type> --priority=<0-4> --description="<context for future execution>"
```

If tasks have dependencies:
```bash
bd dep add <dependent-id> <blocking-id>
```

## Priority Levels

| Priority | Meaning                    |
| -------- | -------------------------- |
| 0 / P0   | Critical (urgent/blocking) |
| 1 / P1   | High (important, soon)     |
| 2 / P2   | Medium (default)           |
| 3 / P3   | Low (nice to have)         |
| 4 / P4   | Backlog (someday/maybe)    |

## Issue Types

- `task` - Default, general work item
- `bug` - Something broken that needs fixing
- `feature` - New functionality
- `epic` - Large initiative (parent for multiple tasks)

## Key Rules

- **Always hydrate first** - The prompt may contain multiple tasks
- **Check for duplicates** - Search existing issues before creating
- **Capture context** - Include enough detail for future execution without current session
- **Set dependencies** - If tasks must be done in order, use `bd dep add`
- **DO NOT execute** - Only queue; execution happens later via `/pull` or manual claim

## Examples

**Single task**:
```
/q fix the typo in README.md
```
→ Creates 1 issue

**Multiple tasks in one prompt**:
```
/q refactor the auth module and add unit tests for it
```
→ Hydrator identifies 2 tasks: (1) refactor auth, (2) add tests (depends on #1)
→ Creates 2 issues with dependency
