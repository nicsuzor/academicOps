---
title: Log Observation in Background
type: instruction
category: instruction
permalink: workflow-log-observation
description: Process an observation asynchronously without blocking the agent
---

# Workflow: Log Observation in Background

**Purpose**: Accept a framework observation, acknowledge immediately, and process asynchronously.

**Execution pattern**: Two-phase (response + background work)

## Phase 1: Immediate Acknowledgment

Return to user immediately with confirmation:

```
Logging observation in background. Continue working.
```

Do NOT wait for framework agent to complete.

## Phase 2: Background Processing

Spawn framework agent asynchronously:

```javascript
Task(
  subagent_type="aops-core:framework",
  model="sonnet",
  description="Log: [brief summary from user observation]",
  prompt="Process this observation and create a task if warranted: [USER'S OBSERVATION]",
  run_in_background=true
)
```

**CRITICAL**: The `run_in_background=true` parameter is **mandatory**. This ensures:
- Framework agent spawns asynchronously
- User gets immediate control back
- No blocking of main workflow
- Results are logged to task system for later review

## Framework Agent Behavior

The spawned framework agent will:

1. **Categorize** the observation by root cause component
2. **Generate** a structured reflection
3. **Create a task** if the observation indicates a framework problem
4. **Return** the reflection and task ID (if created)

The framework agent references the [[workflow-learning-log]] pattern for how to handle observations.

## Key Requirements

| Requirement | Must Have |
|-------------|-----------|
| Immediate response | YES |
| Block user? | NO |
| Run in background | YES |
| Pass observation to agent | YES |
| Use sonnet model | YES |
| Use framework agent | YES |
| Create task if needed | YES (agent responsibility) |

## Root Cause Focus

Log **framework component failures**, not agent mistakes:

| Proximate (Wrong) | Root Cause (Right) |
|-------------------|-------------------|
| "Agent skipped skill" | "Router didn't explain WHY skill needed" |
| "Agent didn't verify" | "Guardrail instruction too generic" |
| "Agent used mocks" | "No PreToolUse hook blocks mock imports" |

See [[enforcement.md]] for the full component responsibility model.

## Related Documentation

- [[log.md]] - /log command specification
- [[SKILL.md]] - This skill's definition
- [[workflow-learning-log.md]] - Framework agent's observation processing pattern
- [[enforcement.md]] - Component responsibility model
