---
name: q
category: instruction
description: Queue a task for later execution (delayed /do)
allowed-tools: Task, Skill, mcp__memory__store_memory
permalink: commands/q
---

# /q - Queue for Later

**Capture a task for later execution.** Like `/do`, but saves instead of executing immediately.

## Usage

```
/q [task description]
```

## What Happens

1. Captures the task description
2. Stores it as a pending task (via tasks skill)
3. Reports confirmation
4. Does NOT execute - that happens when you run `/do` on the task later

## Execution

```
Skill(skill="tasks", args="create inbox '$ARGUMENTS'")
```

Or if the tasks skill isn't available:

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Queue task",
  prompt="Create a task file in $ACA_DATA/tasks/inbox/ for: $ARGUMENTS

Use this format:
---
title: [extracted title]
status: pending
created: [today's date]
source: /q command
---

# [title]

$ARGUMENTS
"
)
```

## When to Use

- Capture an idea while working on something else
- Note a task you'll do later
- Queue up work for a future session

## Relationship to /do

| Command | Behavior |
|---------|----------|
| `/do [task]` | Execute immediately with full pipeline |
| `/q [task]` | Save for later, don't execute |

When ready to execute a queued task:
1. Review tasks in `$ACA_DATA/tasks/inbox/`
2. Run `/do [task description]` to execute

## Examples

```bash
# Capture for later
/q refactor the session panel to use the new API

# Capture a bug to fix
/q fix: dashboard crashes when no sessions exist

# Capture a feature idea
/q add dark mode toggle to settings
```
