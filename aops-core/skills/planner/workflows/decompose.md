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

1. **Understand the Target** — What are we decomposing? A goal (needs projects/epics first), an epic (needs tasks), or a task (needs actions)? Clarify the primary objective and constraints. **Property Check**: Examine the parent's `scope`, `uncertainty`, and `criticality`.
   - **High Uncertainty**: Priority is to reduce uncertainty. The decomposition should lean heavily into evidence gathering, audits, or probes (Step 3).
   - **Low Uncertainty + High Scope**: Parent is well-understood but large. The decomposition should focus on creating independent, parallelizable execution tasks.

2. **Search for Context** (P52) — Query PKB for existing related work, prior decompositions of similar scope, and established patterns. Use `pkb_context(id, hops=2)` to understand the neighbourhood.

3. **Map Unknowns** — Before planning execution, identify what you _don't_ know. Classify each as: **researchable** (others may have solved it → evidence-gathering task), **internal** (we have unanalysed data → audit/survey task), or **probeable** (unknown-unknown → time-boxed spike). High parent `uncertainty` means most subtasks should start here.

4. **Cross-cutting Impact & Prerequisites** — Ask two questions: (a) "What other projects consume or depend on what's changing?" Search PKB for affected tasks/epics; create sibling tasks in THOSE projects with `depends_on` pointing back here. (b) "What must be true for this change to work?" For each unmet prerequisite, create a prep task that implementation `depends_on`. Both often live in different projects.

5. **Select Workflow** — If the target is an epic, identify which workflow will achieve it (e.g., `feature-dev`, `peer-review`, `experiment-design`). The workflow's steps become the decomposition skeleton. If no existing workflow fits, the epic may need a custom step sequence.

6. **Derive the Epic Shape** — Every epic needs phases, but the phases depend on the type of work:

   **For academic/research outputs** (papers, reports, methodology):
   - **Evidence gathering** (first): web research, literature review, internal audit, data survey — run in parallel
   - **Decision support** (blocked on evidence): synthesise findings into decision-ready briefings
   - **Decisions** (human judgment): user makes informed choices, blocked on decision support
   - **Execution** (blocked on decisions): implement the decisions
   - **Integration** (blocked on execution): reconcile parallel tracks
   - **Verification** (terminal): dogfood, QA, audit with receipts

   **For framework/engineering work:**
   - **Planning tasks** (before): acceptance criteria, approach design
   - **Execution tasks** (during): the actual work, one task per workflow step
   - **Verification tasks** (after): QA, testing, cross-referencing, review

   **Self-check rules** (apply after creating any task):
   - After creating a **decision** task: "What information does the user need to make this decision?" → Create a prep task and block the decision on it.
   - After creating an **execution** task: "Is this conditional on a decision that hasn't been made?" → If yes, add dependency on the decision task.
   - After creating a **writing** task: "What analysis/data needs to be final before this can be written?" → Block on the data task.

   Map workflow steps to tasks. Each step becomes one or more tasks. See [[decomposition-patterns]] for temporal, functional, and complexity patterns.

7. **Define Deliverables** — For each task, specify the concrete output. A task without a clear deliverable isn't actionable.

8. **Identify Dependencies** — Which tasks must complete before others can start? Use the [[planning]] skill's dependency-type heuristic: "What happens if the dependency never completes?" If impossible → hard dependency. If less informed → soft dependency.

9. **Estimate Effort** — Assign rough duration (0.5d, 1d, 1w). Tasks over 0.5d probably need further decomposition. Single-session tasks (1–4 hours) are the right duration.

10. **Extract Structured Metadata** — Extract `due` and `consequence` for subtasks if mentioned or implied by the parent task.

11. **Create in PKB** — Use `mcp__pkb__decompose_task(parent_id, subtasks)` for batch creation under the epic. Include dependencies, effort, due, consequence, and deliverable descriptions as explicit fields.

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
- **Link to related tasks**: Use explicit task ID wikilinks (e.g., [[task-id]]), not "the other task" or "as discussed."
- **Record design decisions and constraints**: If the user made a choice (e.g., "filters are dishonest — show everything"), capture it in the task as a design constraint with rationale.
- **Name terminology**: If new terms were coined (e.g., "unlockers" for soft dependencies), define them in the task body so the next agent uses them correctly.

## Critical Rules

- **Completeness & Actionability**: All tasks together must achieve the original epic; every task must be completable in a single session.
- **Verification**: Every epic must include at least one QA/review task.
- **Conservative expansion**: If a task can be done in one sitting, don't decompose further.
- **Graph placement**: Every created task must be connected to the graph — parented under a live (not done) epic, with dependencies to related work. A task with zero downstream weight and a completed parent is effectively invisible to prioritisation. Check: is the parent epic still active? Do any other tasks depend on this work?
- **Scope drift tracking**: When a PR or decision changes the scope of existing tasks, update the affected task bodies. Decomposition is not fire-and-forget — if upstream work narrows or shifts the problem, downstream tasks must be refreshed or they become stale.
