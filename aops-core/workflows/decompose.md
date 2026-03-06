---
id: decompose
name: decompose-workflow
category: planning
bases: [base-task-tracking, base-handover]
description: Break down goals and epics into structured task trees using workflow steps
permalink: workflows/decompose
tags: [workflow, planning, decomposition, tasks, epics]
version: 2.0.0
---

# Decompose Workflow

**Purpose**: Break down a goal or epic into a structured task tree. When the epic has an assigned workflow, derive tasks from the workflow's steps.

**When to invoke**: User says "plan X", "break this down", "what steps are needed?", or an epic is ready for concrete work after [[strategic-intake]].

**Skill**: [[planning]] for decomposition patterns (spikes, dependency types, knowledge flow).

## Core Process

1. **Understand the Target** — What are we decomposing? A goal (needs projects/epics first), an epic (needs tasks), or a task (needs actions)? Clarify the primary objective and constraints.

2. **Search for Context** (P52) — Query PKB for existing related work, prior decompositions of similar scope, and established patterns. Use `pkb_context(id, hops=2)` to understand the neighbourhood.

3. **Select Workflow** — If the target is an epic, identify which workflow will achieve it (e.g., `feature-dev`, `peer-review`, `experiment-design`). The workflow's steps become the decomposition skeleton. If no existing workflow fits, the epic may need a custom step sequence.

4. **Derive the Epic Shape** — Every epic needs three phases:

   - **Planning tasks** (before): acceptance criteria, methodology, approach design
   - **Execution tasks** (during): the actual work, one task per workflow step
   - **Verification tasks** (after): QA, testing, cross-referencing, review

   Map workflow steps to tasks. Each step becomes one or more tasks. See [[decomposition-patterns]] for temporal, functional, and complexity patterns.

5. **Define Deliverables** — For each task, specify the concrete output. A task without a clear deliverable isn't actionable.

6. **Identify Dependencies** — Which tasks must complete before others can start? Use the [[planning]] skill's dependency-type heuristic: "What happens if the dependency never completes?" If impossible → hard dependency. If less informed → soft dependency.

7. **Estimate Effort** — Assign rough complexity (XS, S, M, L). Tasks over M probably need further decomposition. Single-session tasks (1–4 hours) are the right granularity.

8. **Create in PKB** — Use `mcp__pkb__decompose_task(parent_id, subtasks)` for batch creation under the epic. Include dependencies, complexity, and deliverable descriptions.

## Hierarchy and Depth

- **Prefer depth over breadth**: If decomposition produces >7 tasks, group into sub-epics.
- **Target structure**: `Project → Epic → Task → Action` (see [[TAXONOMY.md]])
- **Avoid the star pattern**: A flat list of sibling tasks is a failure of decomposition.
- **Every task belongs to an epic**: No orphans. If a task exists, its epic gives it purpose.

## Workflow-Step Mapping Example

Epic: "Add user authentication" using `feature-dev` workflow:

| Workflow Step              | Task(s)                                      |
| -------------------------- | -------------------------------------------- |
| 1. Understand Requirements | Write auth acceptance criteria (planning)    |
| 2. Propose Plan            | Design auth architecture doc (planning)      |
| 3. Draft Tests             | Write auth unit tests (execution)            |
| 4. Implement               | Implement auth middleware (execution)        |
| 5. Verify Feature          | Run integration tests, review (verification) |
| 6. Submit PR               | Create PR, address review (verification)     |

## Task Handoff Quality (P#120)

Tasks created during decomposition will often be picked up by a **different agent or session** than the one that created them. The creating agent has rich context from the conversation — the picking-up agent has only what's in the task body.

- **Self-contained context**: Each task must include enough background that someone with no session context can understand _why_ this task exists and _what decisions led to it_.
- **Include data findings**: If the decomposition session discovered relevant data (node counts, edge distributions, performance characteristics), record these in the task body — not just "we found the hierarchy is flat" but the actual numbers.
- **Link to related tasks**: Use explicit task IDs, not "the other task" or "as discussed."
- **Record design decisions and constraints**: If the user made a choice (e.g., "filters are dishonest — show everything"), capture it in the task as a design constraint with rationale.
- **Name terminology**: If new terms were coined (e.g., "unlockers" for soft dependencies), define them in the task body so the next agent uses them correctly.

## Critical Rules

- **Completeness**: All tasks together must achieve the original epic.
- **Actionability**: Every task must be completable in a single session.
- **Verification**: Every epic must include at least one QA/review task.
- **Conservative expansion**: If a task can be done in one sitting, don't decompose further.
