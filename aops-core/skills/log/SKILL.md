---
name: log
category: instruction
description: Log framework observations to tasks for continuous improvement
allowed-tools: Task
version: 1.0.0
permalink: skills-log
---

# /log Command Skill

Log framework observations to tasks in the background without blocking the agent.

## Purpose

The /log skill captures framework observations asynchronously, allowing agents to continue working without waiting for logging to complete. It processes observations, categorizes them by root cause component, and creates tasks for further analysis.

## Usage

```
/log [observation]
```

**Example**: `/log Router suggested framework skill but agent ignored it - instruction wasn't task-specific`

## How It Works

1. **User provides observation**: Brief description of framework behavior worth tracking
2. **Skill spawns background agent**: Framework agent processes observation asynchronously
3. **Framework agent logs the observation**: Creates or updates tasks as needed
4. **User continues working**: No blocking, immediate feedback that logging is in progress

## Execution

Follow the [[workflow-log-observation]] pattern, which operates in two phases:

### Phase 1: Immediate Response (User-Facing)

Report to user immediately:

```
Logging observation in background. Continue working.
```

Return control to user without waiting.

### Phase 2: Background Processing

Spawn a framework agent to process the observation:

```javascript
Task(
  subagent_type="aops-core:framework",
  model="sonnet",
  description="Log: [brief summary from observation]",
  prompt="Process this observation and create a task if warranted: [USER'S OBSERVATION]",
  run_in_background=true
)
```

**CRITICAL**: `run_in_background=true` is mandatory - it ensures non-blocking execution.

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

See [[aops-core/specs/enforcement.md]] for the full component responsibility model.

## Background Execution

The `run_in_background=true` parameter ensures:

- User gets immediate acknowledgment
- Framework agent processes asynchronously
- No blocking of main workflow
- Results logged to task system for later review

## Integration

This skill is invoked via the `/log` command, which is defined in [[aops-core/commands/log.md]].

The skill follows the [[workflow-learning-log]] pattern for observation tracking.
