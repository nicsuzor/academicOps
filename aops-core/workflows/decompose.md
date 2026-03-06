---
id: decompose
name: decompose-workflow
category: planning
bases: [base-task-tracking, base-handover]
description: Break down goals into manageable tasks using structural decomposition
permalink: workflows/decompose
tags: [workflow, planning, decomposition, tasks, epics]
version: 1.1.0
---

# Decompose Workflow

**Purpose**: Systematically break down a high-level goal or epic into specific, actionable tasks.

**When to invoke**: User says "plan X", "break this down", "what steps are needed?", or similar.

## Core Decompose Process

1. **Understand Goal**: Clarify the primary objective and any constraints.
2. **Identify Key Stages**: Determine the high-level phases of the work.
3. **Draft Tasks**: Propose a set of tasks that together achieve the goal.
4. **Define Deliverables**: For each task, specify what the final output should be.
5. **Estimate Effort**: Assign rough complexity scores (e.g., XS, S, M, L).
6. **Identify Dependencies**: Note which tasks must complete before others can start.
7. **Create in PKB**: Use `mcp__pkb__create_task` to record the plan.

## Decompose Strategies and Patterns

For common patterns and heuristics for task granularity, see **[[decomposition-patterns]]**:

- **Temporal Patterns** - Sequencing, parallelism, and milestones
- **Functional Patterns** - Layered and feature-based decomposition
- **Complexity Patterns** - Spikes, prototypes, and productionization
- **Granularity Heuristics** - Guidelines for task sizing and focus

## Hierarchy and Depth (P#101, P#110)

- **Prefer Depth over Breadth**: If a goal produces >5 tasks, group them into functional **Epics**.
- **Target Structure**: Multi-session work should aim for `Project -> Epic -> Task -> Action`.
- **Avoid the Star Pattern**: A flat list of sibling tasks under a project is a failure of decomposition.
- **Traceability**: Each level of the hierarchy must provide context and justification for the level below it (The WHY Test).

## Task Handoff Quality (P#120)

Tasks created during decomposition will often be picked up by a **different agent or session** than the one that created them. The creating agent has rich context from the conversation — the picking-up agent has only what's in the task body.

- **Self-contained context**: Each task must include enough background that someone with no session context can understand _why_ this task exists and _what decisions led to it_.
- **Include data findings**: If the decomposition session discovered relevant data (node counts, edge distributions, performance characteristics), record these in the task body — not just "we found the hierarchy is flat" but the actual numbers.
- **Link to related tasks**: Use explicit task IDs, not "the other task" or "as discussed."
- **Record design decisions and constraints**: If the user made a choice (e.g., "filters are dishonest — show everything"), capture it in the task as a design constraint with rationale.
- **Name terminology**: If new terms were coined (e.g., "unlockers" for soft dependencies), define them in the task body so the next agent uses them correctly.

## Critical Rules

- **Completeness**: All tasks together must fully achieve the original goal.
- **Actionability**: Every task must be actionable by an agent or human.
- **Cohesion**: Keep related work in a single task where appropriate.
- **Validation**: Ensure each task includes a verification or check step.
