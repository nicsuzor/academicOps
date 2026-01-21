---
id: batch-processing
category: operations
---

# Batch Processing Workflow

Efficient workflow for processing multiple similar items concurrently using worker-hypervisor architecture.

## Core Principle

**Smart subagent, dumb supervisor.** Supervisor writes ONE smart prompt; subagent discovers, processes, and reports.

## When to Use

- Processing multiple files/items with same operation
- Running tests across multiple modules
- Batch updates or migrations
- Multiple independent tasks ready for parallel work

## When NOT to Use

- Items have dependencies between each other
- Work must be done in specific order
- Shared mutable state would cause conflicts
- Serial processing required

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| "Process all X", "batch update" | Batch processing |
| Multiple independent tasks, no dependencies | Parallel execution possible |
| Items affect same files | NOT batch (conflicts) |

## Architecture

- **Workers**: Autonomous agents, each executes ONE task
- **Hypervisor**: Coordinator managing worker pool (4-8 concurrent)
- **Task system**: Queue that workers pull from

## Key Steps

1. Track parent work
2. Identify scope, validate task independence
3. Spawn hypervisor (5+ tasks) or workers directly (2-4 tasks)
4. Monitor progress
5. Checkpoint: verify all items processed
6. Coordinate push and complete tasks

## Processing Patterns

| Pattern | When to Use |
|---------|-------------|
| **Lazy batching** | Large/unknown counts, coarse batch boundaries |
| **Fixed batches** | Known count, uniform items |
| **Queue-draining** | Workers autonomously find and process items |
| **Pipeline** | Multi-stage processing |

## Quality Gates

- All items identified and scoped
- Task independence validated (no file conflicts)
- All items processed or explicitly deferred
- Results verified for quality
- Single coordinated push (workers commit locally, supervisor pushes)
