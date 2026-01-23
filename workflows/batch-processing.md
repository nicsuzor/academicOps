---
id: batch-processing
category: operations
bases: [base-task-tracking]
---

# Batch Processing

Multiple similar items processed in parallel.

## Routing Signals

- "Process all X", "batch update"
- Multiple independent tasks
- Items don't share mutable state

## NOT This Workflow

- Items have dependencies → process sequentially
- Shared state → conflicts likely
- Single item → [[minor-edit]] or [[design]]

## Unique Steps

1. Validate task independence (no file conflicts)
2. Spawn workers: hypervisor (5+) or direct (2-4)
3. Workers commit locally, supervisor pushes

## Key Principle

**Smart subagent, dumb supervisor.** Supervisor writes ONE smart prompt; worker discovers, processes, reports.
