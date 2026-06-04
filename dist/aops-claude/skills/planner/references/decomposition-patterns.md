# Decomposition Patterns and Strategies

Common patterns for breaking down epics into manageable tasks. Used by the [[decompose]] workflow and the [[planning]] skill.

## Workflow-Step Mapping

When an epic has an assigned workflow, the workflow's steps provide the decomposition skeleton. Each step becomes one or more tasks. The mapping is not always 1:1 — a complex step may need multiple tasks, and simple steps may combine.

**Process**: Read the workflow → list its steps → for each step, create tasks that fulfill it → add planning tasks before and verification tasks after.

**Example**: `feature-dev` workflow applied to "Build search API":

| Phase        | Workflow Step           | Derived Task(s)                       | Type         |
| ------------ | ----------------------- | ------------------------------------- | ------------ |
| Planning     | Understand Requirements | Write search API spec with edge cases | planning     |
| Planning     | Propose Plan            | Design query parser architecture      | planning     |
| Execution    | Draft Tests             | Write search endpoint unit tests      | execution    |
| Execution    | Implement               | Implement query parser + endpoint     | execution    |
| Verification | Verify Feature          | Integration test with sample data     | verification |
| Verification | Submit PR               | PR with review + CI pass              | verification |

## Epic Shape

Every well-decomposed epic has three phases:

- **Head** (planning): At least one task that establishes what "done" means before work begins
- **Body** (execution): Tasks that do the actual work, derived from workflow steps
- **Tail** (verification): At least one task that independently verifies the work meets criteria

An epic without a tail is not verifiable. An epic without a head risks building the wrong thing.

## Temporal Patterns

- **Sequencing**: Task A must finish before Task B begins (hard dependency).
- **Parallelism**: Multiple tasks can be performed independently — look for these to reduce elapsed time.
- **Milestones**: Group tasks around key delivery points or decision gates.

## Functional Patterns

- **Layered**: Breaking down by technical layers (e.g., UI, backend, database).
- **Feature-Based**: Grouping tasks by user-facing features.
- **Dependency-Driven**: Identifying core bottlenecks and addressing them first.

## Complexity-Based Patterns

- **Spike**: Researching an unknown to reduce uncertainty. Use when "we don't know if X is possible." See [[spike-patterns]].
- **Prototype**: Building a minimal version to validate an idea.
- **Productionisation**: Moving from a prototype to a stable, tested system.

## Task Granularity Heuristics

- Aim for tasks that take 1–4 hours to complete (single session).
- Each task should have a clear "why" (traced to its epic) and a single primary deliverable.
- If a task needs context switches between different domains, split it.
- Avoid over-decomposing into trivial subtasks that add more overhead than value.
- See [[dependency-types]] for hard vs soft dependency decisions.
- See [[knowledge-flow]] for propagating findings between sibling tasks.
