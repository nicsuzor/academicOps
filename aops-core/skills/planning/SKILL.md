---
name: planning
type: skill
category: instruction
description: Patterns for decomposing work under uncertainty - spikes, dependencies, and knowledge flow
triggers:
  - "decomposition patterns"
  - "spike tasks"
  - "dependency types"
modifies_files: false
needs_task: true
mode: conversational
domain:
  - operations
allowed-tools: mcp__pkb__create_task,mcp__pkb__update_task,mcp__pkb__create_task,mcp__pkb__get_task,Read
version: 1.0.0
permalink: skills-planning
---

# /planning Skill

> **Taxonomy note**: This skill provides domain expertise (HOW) for decomposing work under uncertainty. It is the primary skill for the [[decompose]] workflow. See [[TAXONOMY.md]] for the skill/workflow distinction.

Patterns for decomposing work under genuine uncertainty.

## Purpose

Provides guidance for breaking down complex goals when the path forward is unknown. Use when standard decomposition feels premature or when you need to discover what you don't know.

## Coordination with Workflows

This skill is the HOW for the [[decompose]] workflow's steps. When decomposing an epic that has an assigned workflow, use the workflow's steps as the decomposition skeleton — then apply the patterns below to handle uncertainty within each step. See [[decomposition-patterns]] for workflow-step mapping examples.

## When to Use

- Multi-month projects with unclear dependencies
- "What does X actually require?" questions
- Creating task hierarchies that handle uncertainty
- Deciding between spike tasks vs placeholder tasks
- Structuring knowledge flow between related tasks

## Key Patterns

See reference documents for detailed guidance:

- [[spike-patterns]] - When to investigate vs commit to implementation
- [[dependency-types]] - Hard vs soft dependency decisions
- [[knowledge-flow]] - Propagating findings between sibling tasks

## Core Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Quick Reference

### Spike vs Placeholder

| Situation                          | Use Spike         | Use Placeholder |
| ---------------------------------- | ----------------- | --------------- |
| "We don't know if X is possible"   | Investigate first |                 |
| "We know X is needed, details TBD" |                   | Capture intent  |
| "Implementation approach unclear"  | Prototype/probe   |                 |

### Dependency Type Selection

**Decision heuristic**: "What happens if the dependency never completes?"

- **Impossible or wrong output** → Hard dependency (`depends_on`)
- **Still valid but less informed** → Soft dependency (`soft_depends_on`)

## Related

- [[decompose]] workflow - Overall decomposition process
- [[base-task-tracking]] - Task lifecycle management
