---
name: active-loop
type: skill
category: operations
description: "Iterative improvement protocol — declare a measurable target, run cycles via /loop, experiment, measure, learn, and accumulate work in a DRAFT PR."
triggers:
  - "active loop"
  - "iterative improvement"
  - "improvement loop"
  - "optimize loop"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
  - knowledge-management
version: 0.1.0
tags:
  - iterative
  - loop
  - improvement
  - protocol
---

# Active Loop

An iterative improvement protocol for agents. The agent declares a measurable optimization target, runs repeated cycles via `/loop`, experiments with different approaches, measures outcomes, and accumulates all work in a DRAFT PR with a learning log.

## When to Use

When a task requires repeated, incremental improvement over multiple cycles rather than a single execution pass. Examples:

- Task graph densification and maintenance
- Code quality improvement across a large codebase
- Data cleanup or migration in batches
- Any work where "try, measure, learn, repeat" beats "plan everything upfront"

## Protocol

### Step 0: Declare Optimization Target (MANDATORY)

Before any work begins, the agent MUST:

1. **State the target** in measurable terms (e.g., "reduce flat tasks from 226 to <100")
2. **Define the measurement** — which tool/command produces the metric
3. **Confirm with the user** — do not proceed until the target is acknowledged

If the target is unclear, ask the user. Do not guess.

```
Optimization target: [what we're improving]
Metric: [how we measure it]
Baseline: [current value]
Tool: [command/tool that produces the metric]
```

### Step 1: Initialize (First Cycle Only)

1. **Take baseline measurement** using the declared tool
2. **Create a working branch**: `active-loop/<target-slug>`
3. **Open a DRAFT PR** with the optimization target and baseline in the body
4. **Record state** in the PR body (see PR Body Format below)

### Step 2: Each Cycle

Every cycle follows this sequence:

```
MEASURE → DECIDE → DO → MEASURE → LOG → PUSH
```

1. **Measure current state** — run the metric tool, compare to last cycle
2. **Decide approach** — based on what we learned last cycle, pick what to try this time. Rotate strategies. Don't repeat what didn't work.
3. **Do the work** — bounded effort per cycle (e.g., 10 tasks, 20 minutes, one batch)
4. **Measure again** — same tool, capture delta
5. **Log learnings** — what we tried, what changed, what surprised us, what to try next
6. **Commit and push** — descriptive commit message referencing the cycle number
7. **Update DRAFT PR body** — append cycle log entry

### Step 3: Re-confirm Target

After each cycle, check:

- Is the target still the right target?
- Are we making progress?
- Should we adjust the approach or the target itself?

If running via `/loop`, output a brief status line so the user can see progress without interrupting.

### Step 4: Completion

When the target is met (or the user decides to stop):

1. Final measurement
2. Summary of all cycles and total improvement
3. Mark PR as ready for review (remove DRAFT)
4. Complete the tracking task

## PR Body Format

```markdown
## Optimization Target

**Target**: [what]
**Metric**: [how measured]
**Baseline**: [starting value]
**Goal**: [target value or "continuous improvement"]

## Cycle Log

### Cycle 1 — [date]

- **Approach**: [what was tried]
- **Before**: [metric value]
- **After**: [metric value]
- **Delta**: [change]
- **Learnings**: [what we discovered]
- **Next**: [what to try next cycle]

### Cycle 2 — [date]

...
```

## Integration with /loop

To run an active loop on a schedule:

```
/loop 30m /active-loop <task-id>
```

The agent reads the PR body to recover state, runs one cycle, updates the PR, and exits. The `/loop` command handles re-invocation.

When resuming from a previous cycle:

1. Find the DRAFT PR for the branch `active-loop/<slug>`
2. Read the cycle log from the PR body
3. Parse the last cycle's "Next" field to inform this cycle's approach
4. Continue from Step 2

## Anti-patterns

- Starting work without declaring the optimization target
- Running cycles without measuring before AND after
- Repeating the same approach when it didn't produce results
- Making the PR body so long it becomes unreadable (summarize older cycles)
- Skipping the "learnings" field — this is the whole point
- Changing the optimization target without user confirmation

## Composability

Active-loop is a protocol, not a domain skill. It composes with domain skills:

| Domain               | Compose with                                            |
| -------------------- | ------------------------------------------------------- |
| Task graph health    | [[planner]] (maintain mode), graph_stats                |
| Code quality         | linters, test coverage tools                            |
| Knowledge base       | [[planner]] (maintain mode), PKB search quality metrics |
| Framework governance | [[audit]], compliance metrics                           |
