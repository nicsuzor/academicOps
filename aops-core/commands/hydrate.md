---
name: hydrate
type: command
category: instruction
description: Enrich a PKB task with execution context (memories, workflow steps, AC, guardrails) so any worker can execute it
triggers:
  - "hydrate task"
  - "enrich task"
  - "prepare task for execution"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Agent, mcp__pkb__get_task, mcp__pkb__task_search, Read
permalink: commands/hydrate
---

# /hydrate - Enrich a Task with Execution Context

**Purpose**: Hydration is something done TO tasks. Given a terse prompt or task ID, enrich the task with everything a worker needs to execute it: relevant memories, workflow steps, acceptance criteria, and guardrails.

## Usage

- `/hydrate <task-id>` — Enrich an existing task
- `/hydrate <terse prompt>` — Create/find a task and enrich it

## Workflow

### Step 1: Resolve Input

Determine whether the input is a task ID or a terse prompt:

- **Task ID** (matches `aops-*` or `academicops-*` pattern): Load the task with `mcp__pkb__get_task`
- **Terse prompt**: Pass directly to the hydrator agent (it will search for or create a task)

### Step 2: Invoke Hydrator Skill

```
Skill(skill='aops-core:hydrator')
```

The hydrator skill runs in the current session and knows where to find framework workflows. Pass the user input as context — the skill reads the current prompt directly.

### Step 3: Report Result

After the hydrator completes, report:

- The enriched task ID
- A 1-sentence summary of what context was added
- Whether `needs_decomposition` was flagged
