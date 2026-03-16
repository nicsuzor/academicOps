---
name: active-loop
type: command
category: instruction
description: Iterative improvement protocol — declare a measurable target, run cycles via /loop, and accumulate work in a DRAFT PR.
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
permalink: commands/active-loop
---

# /active-loop — Iterative Improvement Protocol

**Purpose**: Declare a measurable optimization target, run repeated improvement cycles, and accumulate all work in a DRAFT PR with a cycle log.

## Usage

```
/active-loop <task-id>         # Resume or start an active loop for a task
/loop 30m /active-loop <id>   # Schedule recurring cycles
```

## Protocol

### Before Starting (MANDATORY)

Declare in measurable terms:

```
Optimization target: [what we're improving]
Metric: [how we measure it]
Baseline: [current value]
Tool: [command/tool that produces the metric]
```

Confirm with the user. Do not proceed until acknowledged.

### Initialize (first cycle only)

1. Take baseline measurement
2. Create branch: `active-loop/<target-slug>`
3. Open DRAFT PR with target and baseline in body

### Each Cycle

```
MEASURE → DECIDE → DO → MEASURE → LOG → PUSH → UPDATE PR
```

- **Measure** current state before and after each cycle
- **Decide** based on last cycle's learnings — rotate strategies, don't repeat failures
- **Do** bounded effort (e.g. 10 tasks, 20 minutes)
- **Log**: what was tried, delta, learnings, what to try next
- **Update** the DRAFT PR body with the cycle entry

On resume, read the PR body to recover state and the last "Next" field.

### Completion

When target is met: final measurement, summary of all cycles, mark PR ready for review, complete task.

## Anti-patterns

- Starting without a declared target
- Skipping measurements (before AND after)
- Repeating approaches that didn't work
- Skipping the "learnings" field — this is the whole point
- Changing the target without user confirmation
