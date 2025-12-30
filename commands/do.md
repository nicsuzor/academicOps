---
name: do
description: Execute work with full context enrichment and guardrails via hypervisor
allowed-tools: Task
permalink: commands/do
---

# /do - Execute With Full Pipeline

**Single entry point for all work.** Spawns the hypervisor agent to orchestrate the full pipeline.

## Usage

```
/do [your task description]
```

## What Happens

The `/do` command spawns the hypervisor agent, which:

1. **Gathers context** - Knowledge base, project files, prior decisions
2. **Classifies task** - Identifies task type and required workflow
3. **Invokes planning skill** - Creates TodoWrite with work steps AND QA checkpoints
4. **Orchestrates execution** - Delegates to specialist skills, doesn't do work directly
5. **Verifies completion** - QA checkpoints baked into todo ensure verification
6. **Cleanup** - Commit, push, update memory, archive task

## Execution

Spawn the hypervisor with the user's prompt:

```
Task(
  subagent_type="hypervisor",
  model="opus",
  description="Orchestrate: [first 3 words]",
  prompt="$ARGUMENTS"
)
```

That's it. The hypervisor handles everything else.

## Why Hypervisor?

The hypervisor:
- **Orchestrates but doesn't execute** - Delegates all work to subagents/skills
- **Controls the plan** - Planning skills create TodoWrite with QA checkpoints
- **Enforces quality gates** - QA steps are todo items that can't be skipped
- **Handles failures** - Iterates on errors, detects scope drift and thrashing

## Examples

```bash
# Feature development
/do implement dark mode toggle in settings

# Debug
/do fix the dashboard session panel not loading

# Framework changes
/do add a new skill for handling email tasks

# Research
/do investigate why the memory server isn't returning results
```

All of these go through the same pipeline. The hypervisor classifies the task and invokes appropriate planning skills.
