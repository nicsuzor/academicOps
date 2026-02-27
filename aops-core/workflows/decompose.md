---
id: decompose
category: planning
description: Break goals into actionable work under uncertainty, surface assumptions, and route tasks
triggers:
  - "plan the project"
  - "break down"
  - "decompose"
  - "write a paper"
  - "build X"
  - "multi-month"
  - "epic"
bases: [base-task-tracking, base-handover]
---

# Decompose

Break goals into actionable work under genuine uncertainty.

## Routing Signals

- Multi-month projects (dissertations, books, grants)
- "What does X actually require?"
- Vague deliverable, unclear dependencies
- Path forward is unknown

## NOT This Workflow

- Known tasks, clear steps → [[design]]
- Pure information request → [[simple-question]]

## Unique Steps

1. Articulate the goal clearly
2. Surface assumptions (what must be true?)
3. Find affordable probes (cheapest way to validate?)
4. Create coarse components (don't over-decompose)
5. Ensure at least one task is actionable NOW
6. Route task assignments:
   - **Mechanical work** (create, implement, fix, update, refactor) → `assignee: polecat`
   - **Judgment-call tasks** (review, evaluate, decide, design choices) → `assignee: null` (unassigned backlog)
   - **Explicit override** → only assign to `nic` when user explicitly requests it

## Key Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Pattern References

For detailed guidance on decomposition patterns, see the [[planning]] skill:

- [[spike-patterns]] - When to investigate vs commit; spike completion checklist
- [[dependency-types]] - Hard vs soft dependency decisions; human handoff patterns
- [[knowledge-flow]] - Propagating findings between siblings; confirmed vs TBD tables

## Quick Reference

### Spike vs Placeholder

| Situation                            | Use Spike         | Use Placeholder |
| ------------------------------------ | ----------------- | --------------- |
| "We don't know if X is possible"     | Investigate first |                 |
| "We know X is needed, details TBD"   |                   | Capture intent  |
| "Implementation approach is unclear" | Prototype/probe   |                 |

### Dependency Selection

**Ask: "What happens if the dependency never completes?"**

- **Impossible or wrong output** → `depends_on` (hard)
- **Still valid but less informed** → `soft_depends_on` (soft)

## Project Structure

Tasks cluster in visualizations based on their parent chain reaching a canonical project file.

**Checklist:**

1. **Project file exists**: `$ACA_DATA/{project}/{project}.md` with `type: project`
2. **Root goals link to project**: Goals have `parent: {project-id}`
3. **Tasks link to goals**: Every task has `parent:` pointing up the chain
4. **Project field matches**: `project: {slug}` matches the project file's `id:`

## Completion Loop (MANDATORY)

When decomposing work into subtasks, ALWAYS create a **verify-parent** task:

1. Create all subtasks as normal
2. Create one additional task: `"Verify: [parent goal] fully resolved"`
3. Set `depends_on:` to ALL the subtasks just created
4. Set `assignee: null` (requires human judgment)
5. This task's body should restate the original problem and acceptance criteria

**Purpose**: Subtasks getting completed does not mean the parent's goal was met. The verify-parent task forces a return to the original problem to confirm it's fully solved or to iterate again.

**Example**:

```
Parent: "Fix task graph quality issues"
  ├── Subtask 1: "Update priority semantics doc"
  ├── Subtask 2: "Implement parent requirement rules"
  ├── Subtask 3: "Design nightly maintenance system"
  └── Verify: "Confirm task graph quality issues are resolved"
       depends_on: [subtask-1, subtask-2, subtask-3]
       body: "Return to the original problem. Are task graph quality
              issues actually resolved? Check: ..."
```

**Relationship to P#71**: P#71 says "complete the parent immediately" when decomposing. The completion loop does not contradict this — the decomposition work IS complete. The verify task is a NEW task that checks whether the original goal was achieved after all implementation is done.

## Post-Decomposition Self-Checks (MANDATORY)

After creating subtasks, run these checks before finalizing:

### Check 1: Decision tasks have information prerequisites

For every task that requires a human **decision** (evaluate, choose, decide, select, classify, determine scope):

> "What information does the user need to make this decision?"

If no upstream prep task supplies that information, create one:
- Prep task: agent gathers data, documents current state (no human judgment needed)
- Set the decision task's `depends_on` to include the prep task
- Prep tasks should have `assignee: polecat` (mechanical data gathering)

### Check 2: Execution tasks are gated on relevant decisions

For every **execution** task (run, implement, write, build, create):

> "Is this task conditional on a decision that hasn't been made yet?"

If the task only makes sense given a specific decision outcome, it **must** depend on that decision task. Do not leave conditional work unblocked in the ready queue.

### Check 3: Writing tasks are blocked on their data

For every **writing** task (write, draft, document, report):

> "What analysis or data needs to be final before this can be written?"

If the writing depends on analysis results, block it on the analysis task.

### Check 4: Academic output methodology layer

When decomposing work that produces **academic output** (papers, reports, benchmarks, analyses, reviews), always include these methodology tasks in addition to the deliverable tasks:

- **Justify every methodological choice**: model/sample selection criteria, coding schemes, categorisations (prep task)
- **Define validation approach**: inter-rater reliability, construct validity, external review — how will claims be tested? (decision task, blocked on justification)
- **Systematic claim-evidence audit**: every claim cross-referenced to data, unsupported claims flagged (audit task, blocked on writing)
- **Limitations completeness**: every known limitation stated (audit task, blocked on writing)

**Axiom**: Nothing goes out to the public before it's perfect. All academic output must be triple-checked and presented to the user for explicit approval with full receipts (verification logs, QA checklists, evidence) before release.

## Academic Output Layer Structure

For academic outputs, enforce this ordering:

| Layer | Purpose | Assignee | Blocked on |
|-------|---------|----------|------------|
| 1. Prep | Agent gathers data, documents current state | polecat | — |
| 2. Decision support | Agent synthesises prep into decision-ready briefings | polecat | Layer 1 |
| 3. Decisions | Human makes informed choices | null | Layers 1-2 |
| 4. Writing/Execution | Implement decisions | polecat | Layer 3 |
| 5. Integration | Reconcile parallel tracks | polecat | Layer 4 |
| 6. Audit/QA | Verify everything, present receipts | null | All above |

**Note**: Not every academic decomposition needs all six layers. Use judgment — but every academic decomposition needs at least Prep → Decision → Writing → Audit.

## Anti-Patterns

- Expanding everything at once (premature detail)
- Blocking on ambiguity (create placeholder tasks instead)
- Hidden assumptions (planning as if everything is known)
- **Isolated spikes**: Completing investigation without propagating findings to parent
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
- **Missing project anchors**: Creating goals/tasks with `project: X` but no `X.md` project file exists
- **Reflexive task creation**: Creating tasks without knowing the action path
- **Prose instead of structure**: Writing relationships as prose when they should be graph edges
- **Fire-and-forget decomposition**: Creating subtasks without a verify-parent task to close the loop
- **Decisions without prep**: Decision tasks with no upstream data-gathering task
- **Unblocked conditional work**: Execution tasks sitting in "ready" when they depend on an unmade decision
- **Missing methodology layer**: Academic output decomposed at project-management level only, without justification/validation/audit tasks
- **PM-only decomposition**: Creating "run notebook, write section, ship" without methodology tasks
- **Investigating instead of tasking**: Don't go look at code/data — work with PKB knowledge, create tasks for unknowns
