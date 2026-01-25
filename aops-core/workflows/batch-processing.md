# Batch Processing Workflow

Multiple similar items processed in parallel.

Extends: base-task-tracking

## When to Use

Use this workflow when:
- "Process all X" or "batch update" requests
- Multiple independent tasks exist
- Items don't share mutable state

Do NOT use for:
- Items that have dependencies (process sequentially instead)
- Shared state exists (conflicts are likely)
- Single item (use design)

## Constraints

### Preconditions

- Task independence must be validated before spawning workers
- No file conflicts can exist (no two tasks modify the same file)

### Processing Rules

- Workers commit locally; supervisor pushes after all complete
- Follow the "smart subagent, dumb supervisor" principle: supervisor writes ONE smart prompt, worker discovers and processes autonomously

### Worker Selection

- If 5 or more items → use hypervisor
- If 2-4 items → use direct spawn

### Never Do

- Never parallel process tasks that have dependencies
- Never parallel modify shared state

## Triggers

- When batch request arrives → validate task independence
- When independence is confirmed → spawn workers
- When all workers complete → supervisor pushes

## How to Check

- Task independence validated: all items can be processed without affecting each other
- No file conflicts: no two tasks modify the same file
- Workers commit locally: each worker commits its own changes
- Supervisor pushes: supervisor aggregates and pushes after workers complete
- Smart subagent, dumb supervisor: supervisor writes ONE smart prompt; worker discovers, processes, and reports autonomously
- Item count >= 5: batch contains 5 or more items
- Item count 2-4: batch contains 2-4 items
