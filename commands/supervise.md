---
name: supervise
description: Generic supervisor loading workflow templates for orchestrated multi-agent tasks
permalink: aops/commands/supervise
tools:
  - Skill
---

# /supervise - Generic Supervisor Command

Invoke the supervisor skill with the specified workflow:

```
Skill(skill="supervisor", args="$ARGUMENTS")
```

## Usage

```
/supervise {workflow} {task description}
```

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `tdd` | Test-first development with pytest validation |
| `batch-review` | Parallel batch processing with quality gates |
| `skill-audit` | Review skills for content separation |

## Examples

```bash
# Test-driven development
/supervise tdd Fix the authentication bug in user login

# Batch processing with quality control
/supervise batch-review Review all tasks in data/tasks/inbox/ and ensure valid frontmatter

# Skill content audit
/supervise skill-audit Review all skills and ensure SKILL.md contains only actionable instructions
```

## What the Supervisor Does

1. **Loads workflow template** from `skills/supervisor/workflows/{name}.md`
2. **Enforces supervisor contract** - orchestrates via subagents, no direct implementation
3. **Applies quality gates** - critic review, acceptance criteria lock, QA verification
4. **Tracks progress** - TodoWrite integration throughout
5. **Handles failures** - iterates on errors, detects scope drift and thrashing

## Adding New Workflows

Create a new file in `skills/supervisor/workflows/{name}.md` with:
- YAML frontmatter: `name`, `description`, `required-skills`, `scope`
- Sections: ITERATION UNIT, QUALITY GATE, workflow-specific steps
- SUBAGENT PROMPTS for delegation

The supervisor will automatically discover and load new workflows.
