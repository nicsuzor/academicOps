---
name: log
category: instruction
description: Log framework component failures to bd issues (per AXIOMS #28)
allowed-tools: Task
permalink: commands/log
---

**Run in background** - spawn the learning-log workflow asynchronously so the user can continue working:

```
Task(subagent_type="general-purpose", model="haiku",
     description="Log observation to bd",
     prompt="Invoke Skill(skill='framework') and follow workflow 07-learning-log.md with this observation: [USER'S OBSERVATION]",
     run_in_background=true)
```

Report to user: "Logging observation in background. Continue working."

**Purpose**: Build institutional knowledge by logging observations to bd issues, where patterns can accumulate and synthesize to HEURISTICS.md.

## Key Principle: Root Cause Abstraction

**We don't control agents** - they're probabilistic. Log **framework component failures**, not agent mistakes.

| Wrong (Proximate)     | Right (Root Cause)                                                       |
| --------------------- | ------------------------------------------------------------------------ |
| "Agent skipped skill" | "Router didn't explain WHY skill needed for THIS task" → Clarity Failure |
| "Agent didn't verify" | "Guardrail instruction too generic" → Clarity Failure                    |
| "Agent used mocks"    | "No PreToolUse hook blocks mock imports" → Gap                           |

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

## Usage

**User provides**: Brief description of what went wrong

**Example**: `/log Router suggested framework skill but agent ignored it - instruction wasn't task-specific`

The workflow will categorize and create/update a bd issue. Root cause analysis is deferred to `/qa [issue-id]`.
