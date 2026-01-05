---
name: log
description: Log framework component failures to GitHub Issues (per AXIOMS #28)
allowed-tools: Skill
permalink: commands/log
---

**IMMEDIATELY** invoke the `[[skills/learning-log/SKILL.md|learning-log]]` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging observations to GitHub Issues, where patterns can accumulate and synthesize to HEURISTICS.md.

## Key Principle: Root Cause Abstraction

**We don't control agents** - they're probabilistic. Log **framework component failures**, not agent mistakes.

| Wrong (Proximate) | Right (Root Cause) |
|-------------------|-------------------|
| "Agent skipped skill" | "Router didn't explain WHY skill needed for THIS task" → Clarity Failure |
| "Agent didn't verify" | "Guardrail instruction too generic" → Clarity Failure |
| "Agent used mocks" | "No PreToolUse hook blocks mock imports" → Gap |

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

## Usage

**User provides**: Brief description of what went wrong

**Example**: `/log Router suggested framework skill but agent ignored it - instruction wasn't task-specific`

The skill will trace to root cause category and responsible component.
