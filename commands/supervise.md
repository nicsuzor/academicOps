---
name: supervise
description: Generic supervisor loading workflow templates for orchestrated multi-agent tasks
permalink: aops/commands/supervise
tools:
  - Task
---

# /supervise - Hypervisor Orchestration Command

Spawn the [[agents/hypervisor|Hypervisor agent]] for multi-step workflow orchestration:

```
Task(subagent_type="hypervisor", model="opus", prompt="$ARGUMENTS")
```

## Usage

```
/supervise {workflow} {task description}
```

## Workflow Templates (Future)

When workflow loading is implemented, these templates will be available:

| Workflow | Description |
|----------|-------------|
| `tdd` | Test-first development with pytest validation |
| `batch-review` | Parallel batch processing with quality gates |
| `skill-audit` | Review skills for content separation |

For now, describe the workflow approach in your prompt directly.

## Examples

```bash
# Multi-step feature implementation
/supervise Implement user authentication: plan first, then implement with tests, verify before completing

# Code review with quality gates
/supervise Review and refactor the dashboard component: check for issues, propose fixes, get approval

# Batch processing task
/supervise Process all markdown files in docs/: validate frontmatter, fix formatting, commit each file
```

## What the Hypervisor Does

1. **Phase 0: Planning** - Creates plan via Plan agent, gets critic review, defines acceptance criteria
2. **Enforces supervisor contract** - orchestrates via subagents, no direct implementation (no Read/Edit/Bash)
3. **Applies quality gates** - acceptance criteria lock, QA verification before completion
4. **Tracks progress** - TodoWrite integration throughout all phases
5. **Handles failures** - iterates on errors (max 3 attempts), detects scope drift (>20%) and thrashing
6. **Phase 5: Completion** - Mandatory QA verification, documents via tasks skill

## Workflow Templates (Planned)

Domain-specific workflow loading is planned but not yet implemented. See ROADMAP.md "Hypervisor Workflow Loading".

Currently, include workflow-specific instructions directly in your prompt:
```
/supervise Implement login feature using TDD: write failing test first, then implement, then verify
```
