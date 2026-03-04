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

## Critical Rules

- **Completeness**: All tasks together must fully achieve the original goal.
- **Actionability**: Every task must be actionable by an agent or human.
- **Cohesion**: Keep related work in a single task where appropriate.
- **Validation**: Ensure each task includes a verification or check step.
