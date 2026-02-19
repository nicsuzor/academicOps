---
id: decompose
category: planning
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
   - **Explicit override** → only assign to `human` when user explicitly requests it

## Key Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Pattern References

For detailed guidance on decomposition patterns, see the [[planning]] skill:

- [[spike-patterns]] - When to investigate vs commit; spike completion checklist
- [[dependency-types]] - Hard vs soft dependency decisions; human handoff patterns
- [[knowledge-flow]] - Propagating findings between siblings; confirmed vs TBD tables

## Quick Reference

### Spike vs Placeholder

| Situation                              | Use Spike            | Use Placeholder   |
| -------------------------------------- | -------------------- | ----------------- |
| "We don't know if X is possible"       | Investigate first    |                   |
| "We know X is needed, details TBD"     |                      | Capture intent    |
| "Implementation approach is unclear"   | Prototype/probe      |                   |

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

## Anti-Patterns

- Expanding everything at once (premature detail)
- Blocking on ambiguity (create placeholder tasks instead)
- Hidden assumptions (planning as if everything is known)
- **Isolated spikes**: Completing investigation without propagating findings to parent
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
- **Missing project anchors**: Creating goals/tasks with `project: X` but no `X.md` project file exists
- **Reflexive task creation**: Creating tasks without knowing the action path
- **Prose instead of structure**: Writing relationships as prose when they should be graph edges
