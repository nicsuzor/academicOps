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
- **Terse prompt**: Pass directly to the task-hydrator agent (it will search for or create a task)

### Step 2: Spawn Task Hydrator

Invoke the task-hydrator agent:

```
Agent(subagent_type='aops-core:task-hydrator', prompt='
## Hydration Request

**Input**: {user input — task ID or terse prompt}

**Framework paths**:
- WORKFLOWS.md: aops-core/WORKFLOWS.md
- AXIOMS.md: aops-core/AXIOMS.md
- HEURISTICS.md: aops-core/HEURISTICS.md
- Workflow files: aops-core/workflows/

**Instructions**: Enrich this task with execution context per your agent definition. Output the enriched task ID when complete.
')
```

### Step 3: Report Result

After the task-hydrator completes, report:

- The enriched task ID
- A 1-sentence summary of what context was added
- Whether `needs_decomposition` was flagged
