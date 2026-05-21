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
   - **Target structure**: `Project → Epic → Task → Action` (see [[../../remember/references/TAXONOMY.md]])
   - **Property Check**: Examine the parent's `scope`, `uncertainty`, and `criticality`.
   - **High Uncertainty**: Priority is to reduce uncertainty. The decomposition should lean heavily into evidence gathering, audits, or probes (Step 3).
   - **Low Uncertainty + High Scope**: Parent is well-understood but large. The decomposition should focus on creating independent, parallelizable execution tasks.

2. **Search for Context**: Query PKB for existing related work, prior decompositions of similar scope, and established patterns. Use `pkb_context(id, hops=2)` to understand the neighbourhood.

3. **Map Unknowns**: Before planning execution, identify what you _don't_ know. Classify each as: **researchable** (others may have solved it → evidence-gathering task), **internal** (we have unanalysed data → audit/survey task), or **probeable** (unknown-unknown → time-boxed spike). High parent `uncertainty` means most subtasks should start here.

4. **Cross-cutting Impact & Prerequisites** — Ask two questions: (a) "What other projects consume or depend on what's changing?" Search PKB for affected tasks/epics — scope per-project queries with `list_tasks(project=<project-id>)` rather than inferring membership from ID prefixes or walking parent chains. Create sibling tasks in THOSE projects with `depends_on` pointing back here. (b) "What must be true for this change to work?" For each unmet prerequisite, create a prep task that implementation `depends_on`. Both often live in different projects.

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

11. **Set Priority — default P3**: Subtasks default to **P3**. Do NOT propagate the parent's priority to children or infer priority from subtask content. Only elevate above P3 if the user explicitly signals urgency. See [[../SKILL.md#priority-assignment-rules]].

12. **Apply the Decision Surfacing Heuristic** — Before drafting any user-facing "design conversation" or ratification message, classify each open decision as DECIDE / DEFER / SURFACE per [[../SKILL.md#decision-surfacing-heuristic]]. Bundling DECIDE-class items with SURFACE-class items trains rubber-stamping (issue #816).
13. **Create in PKB** — Use `mcp__pkb__decompose_task(parent_id, subtasks)` for batch creation under the epic. Include dependencies, effort, due, consequence, priority, and deliverable descriptions as explicit fields.

14. **Apply Multi-agent Review Gate (default, mandatory)** — For each proposed epic, file ONE blocking `james review of <epic-title> (pauli + rbg + revise)` child (epic stays `inbox` until it lands). For each proposed standalone task, file `pauli + rbg review of planned approach` as the first subtask (execution children `depends_on` it) and `james review of work against original instructions, user intent, and project rules` as the last subtask (`depends_on` execution children). State only the artifact and link to parent; defer methodology to the agents' framework instructions. Stacks with — does not replace — the lens-based profile in step 15.

15. **Apply Review Profile** — Create SEPARATE child subtasks for review based on work type. Tag with `lens: <name>` (use `aops-core/skills/planner/references/verification-template.md` as a base).
    - **Methodology/Analysis**: Agent methodology critique followed by binary Human "accept/redesign" approval (`assignee="nic"`). Block promotion on these.
    - **Citation-heavy Writing**: Citation verification & Argument review (runs AFTER execution, does not block promotion).
    - **Outbound Comms**: Alignment, Quality, & Voice review (runs AFTER execution, does not block promotion).
    - **Student Assessment**: Rubric fidelity & Consistency review (runs AFTER execution, does not block promotion).
    - **Exploratory**: _Escape Hatch_ — Create minimal verification tasks and do not block promotion to ready for exploratory work.

16. **Record Promotion Decision** — Write a `## Promotion Log` entry to the parent body capturing the rationale for promotion and transition status from `inbox` to `ready`.

## Hierarchy and Depth

- **Prefer depth over breadth**: If decomposition produces >10 tasks, group into sub-epics.
- **Avoid the star pattern**: A flat list of sibling tasks is a failure of decomposition.
- **Every task belongs to an epic**: No orphans. If a task exists, its epic gives it purpose.

## Workflow-Step Mapping Example

Epic: "Add user authentication" using `feature-dev` workflow:

| Workflow Step              | Task(s)                                               |
| -------------------------- | ----------------------------------------------------- |
| 1. Understand Requirements | Write auth acceptance criteria (planning)             |
| 2. Propose Plan            | Design auth architecture doc (planning)               |
| 3. Draft Tests             | Write auth unit tests (execution)                     |
| 4. Implement               | Implement auth middleware (execution)                 |
| 5. Verify & Submit         | Run integration tests, review, open PR (verification) |

## Task Handoff Quality (P#120)

Tasks will be picked up by a **different agent** with only the task body as context. This is the canonical compose-then-dispatch shape: decompose writes the brief to PKB; a separate invocation (the worker, the next supervisor tick) reads it fresh. See [[../../aops/references/authoring-discipline#3-compose-then-dispatch-separation-a17-propagated-to-the-dispatch-surface]].

- **Intent + AC, not prescription**: Apply the Task-Body Authoring Discipline ([[../../aops/references/authoring-discipline]]). Task bodies must state intent and observable Acceptance Criteria without prescribing implementation or adding phantom review gates.
- **Self-contained context**: Include enough background that someone with no session context understands _why_ this task exists and _what decisions led to it_.
- **Include data findings**: Record actual numbers discovered during decomposition, not just summaries.
- **Link to related tasks**: Use explicit task ID wikilinks (e.g., [[task-id]]), not "the other task."
- **Record design decisions and terminology**: Capture user choices as design constraints with rationale; define new terms in the task body.

## Critical Rules

- **Completeness & Actionability**: All tasks together must achieve the original epic; every task must be completable in a single session.
- **Verification**: Every epic must include at least one QA/review task. The Multi-agent Review Gate (step 14) is the default and is non-optional — `james` blocker on every new epic; `pauli + rbg` first / `james` last on every new standalone task. The user is often not the right substantive reviewer; do not skip the gate just because they look ready to approve.
- **Conservative expansion**: If a task can be done in one sitting, don't decompose further.
- **Graph placement & drift**: Every task must be parented under a live epic with dependencies. When upstream work changes scope, update affected task bodies.
- **No parallel tracking**: After creating subtasks, remove any `- [ ]` checklists from the parent body that duplicate the subtask graph. Replace with a summary reference (e.g., "Decomposed into N subtasks — see children"). Body checklists and subtask graphs inevitably diverge over time.
