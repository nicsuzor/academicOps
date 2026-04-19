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

1. **Understand the Target**: What are we decomposing -- a project, an epic (needs tasks), or a task (needs actions)? Clarify the primary objective and constraints.
   - **Target structure**: `Project → Epic → Task → Action` (see [[TAXONOMY.md]])
   - **Property Check**: Examine the parent's `scope`, `uncertainty`, and `criticality`.
   - **High Uncertainty**: Priority is to reduce uncertainty. The decomposition should lean heavily into evidence gathering, audits, or probes (Step 3).
   - **Low Uncertainty + High Scope**: Parent is well-understood but large. The decomposition should focus on creating independent, parallelizable execution tasks.

2. **Search for Context**: Query PKB for existing related work, prior decompositions of similar scope, and established patterns. Use `pkb_context(id, hops=2)` to understand the neighbourhood.

3. **Map Unknowns**: Before planning execution, identify what you _don't_ know. Classify each as: **researchable** (others may have solved it → evidence-gathering task), **internal** (we have unanalysed data → audit/survey task), or **probeable** (unknown-unknown → time-boxed spike). High parent `uncertainty` means most subtasks should start here.

4. **Cross-cutting Impact & Prerequisites** — Ask two questions: (a) "What other projects consume or depend on what's changing?" Search PKB for affected tasks/epics; create sibling tasks in THOSE projects with `depends_on` pointing back here. (b) "What must be true for this change to work?" For each unmet prerequisite, create a prep task that implementation `depends_on`. Both often live in different projects.

5. **Derive a composite Workflow**:
   - Identify which workflow or combination of workflows are relevant for the particular task.
   - Every epic needs phases, but the phases depend on the type of work.
   - The composite workflow's steps become the decomposition skeleton.

6. **Map workflow steps to tasks**: Each step becomes one or more tasks. See [[decomposition-patterns]] for temporal, functional, and complexity patterns.

7. **Define Deliverables**: For each task, specify the concrete output. A task without a clear deliverable isn't actionable.

8. **Identify Dependencies**: Which tasks must complete before others can start?
   - Use the [[planning]] skill's dependency-type heuristic: "What happens if the dependency never completes?" If impossible → hard dependency. If less informed → soft dependency.

9. **Estimate Effort**: Assign rough duration (0.5d, 1d, 1w). Tasks over 0.5d probably need further decomposition. Single-session tasks (1–4 hours) are the right duration.

10. **Extract Structured Metadata**: Extract `due` and `consequence` for subtasks if mentioned or implied by the parent task.

11. **Create in PKB** — Use `mcp__pkb__decompose_task(parent_id, subtasks)` for batch creation under the epic. Include dependencies, effort, due, consequence, and deliverable descriptions as explicit fields.

## Hierarchy and Depth

- **Prefer depth over breadth**: If decomposition produces >10 tasks, group into sub-epics.
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

Tasks will be picked up by a **different agent** with only the task body as context.

- **Self-contained context**: Include enough background that someone with no session context understands _why_ this task exists and _what decisions led to it_.
- **Include data findings**: Record actual numbers discovered during decomposition, not just summaries.
- **Link to related tasks**: Use explicit task ID wikilinks (e.g., [[task-id]]), not "the other task."
- **Record design decisions and terminology**: Capture user choices as design constraints with rationale; define new terms in the task body.

## Critical Rules

- **Completeness & Actionability**: All tasks together must achieve the original epic; every task must be completable in a single session.
- **Verification**: Every epic must include at least one QA/review task.
- **Conservative expansion**: If a task can be done in one sitting, don't decompose further.
- **Graph placement & drift**: Every task must be parented under a live epic with dependencies. When upstream work changes scope, update affected task bodies.
- **No parallel tracking**: After creating subtasks, remove any `- [ ]` checklists from the parent body that duplicate the subtask graph. Replace with a summary reference (e.g., "Decomposed into N subtasks — see children"). Body checklists and subtask graphs inevitably diverge over time.
