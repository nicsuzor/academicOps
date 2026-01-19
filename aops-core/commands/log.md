---
name: log
category: instruction
description: Log framework observations to tasks for continuous improvement
allowed-tools: Task
permalink: aops/commands/log
tags:
  - reflection
  - learning
---

# /log Command

Log framework observations to tasks. Runs in background so you can continue working.

## Usage

```
/log [observation]
```

**Example**: `/log Router suggested framework skill but agent ignored it - instruction wasn't task-specific`

## Execution

Spawn the framework agent in background to process the observation:

```javascript
Task(subagent_type="aops-core:framework", model="sonnet",
     description="Log: [brief summary]",
     prompt="Process this observation and create a task if warranted: [USER'S OBSERVATION]",
     run_in_background=true)
```

Report to user: "Logging observation in background. Continue working."

## What Gets Logged

The framework agent will:

1. Categorize the observation by root cause component
2. Generate a structured reflection
3. Create a task if the observation indicates a framework problem
4. Return the reflection and task ID (if created)

## Root Cause Focus

Log **framework component failures**, not agent mistakes:

| Wrong (Proximate)     | Right (Root Cause)                       |
| --------------------- | ---------------------------------------- |
| "Agent skipped skill" | "Router didn't explain WHY skill needed" |
| "Agent didn't verify" | "Guardrail instruction too generic"      |
| "Agent used mocks"    | "No PreToolUse hook blocks mock imports" |

See aops-core/specs/enforcement.md for the full component responsibility model.
