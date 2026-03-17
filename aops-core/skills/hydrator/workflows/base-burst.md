---
id: base-burst
category: base
---

# Base: Burst (Iterative Batch Lifecycle)

The `base-burst` pattern manages long-running, iterative batch operations that require multiple agent sessions. It is a stateful alternative to `base-batch`.

## When to Use

- Batch tasks that take more than one session (e.g., auditing 100+ files).
- Tasks where each item needs evaluation before dispatching the next.
- Workflows that need to persist progress and resume exactly where they left off.

## Pattern Steps

1. **Initialization (`init`)**:
   - Define workflow configuration (Queue Source, Worker Instructions, Evaluation Criteria).
   - Populate the queue by scanning the source (e.g., `ls specs/*.md`).
   - Create a Tracking Task in PKB with the initial queue and state.
2. **Burst Loop (`run`)**:
   - **Load**: Retrieve the state from the tracking task.
   - **Evaluate**: Check previous dispatches. Compare worker output to criteria. Update queue item statuses using the canonical `burst-supervisor` states (`pending`, `in_progress`, `done`, `failed`) — marking items as `done` or `failed`, and returning items that need another attempt to `pending` for retry.
   - **Dispatch**: Select pending items up to `items_per_burst`. Create new worker tasks.
3. **Persistence (`persist`)**:
   - Update frontmatter counters (`plan.completed`, etc.).
   - Append activity log to the task body.
   - Halt and report progress.
4. **Resumption (`resume`)**:
   - Start at Step 2 using the tracking task ID.

## Skills Required

- `burst-supervisor`: The core engine that implements this lifecycle logic.

## Composition Example: spec-audit

```markdown
# spec-audit

## Bases

- [[base-burst]]
- [[base-task-tracking]]

## Steps

1. /burst-supervisor init spec-audit
2. ... (supervisor continues in bursts)
```
