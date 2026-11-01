---
title: Default Dialectical Review Workflow
status: ready
type: spec
category: workflow
tags: [spec, workflow, review, dialectic, composition, default]
---

# Default Dialectical Review Workflow

Establishes dialectical multi-agent evaluation as the workflow library's default independent review stage in place of monolithic review, while enabling callers and projects to substitute alternative review workflows.

## User stories

### US-1 Default Dialectical Review for Independent Review Stages

As an agent composing tasks from composite workflows, I want an independent review stage to resolve to the dialectical review workflow by default, so that deliverables receive thorough multi-perspective independent evaluation without hardcoding implementation templates.

- **AC-1.1** Given a composite workflow defining an independent review stage with no explicit review template designated, when the stage is resolved, then it resolves to the workflow template tagged `review` marked `default: true`.
- **AC-1.2** Given a review stage executing under the default review workflow, when execution begins, then it coordinates multiple distinct evaluative perspectives (addressing strategic direction, compliance, and quality/acceptance criteria) via internal subagents under an evaluative supervisor and yields a unified verdict (`PASS`, `REVISE`, or `FAIL`).
- **AC-1.3** Given an environment where subagent spawning is unavailable, when the default dialectical review executes, then it halts immediately with an explicit error without silent single-agent fallback.

### US-2 Review Workflow Substitution and Calibration

As a user or project author, I want to substitute an alternative review workflow or calibrate review depth, so that specialized, lightweight, or domain-specific review procedures can replace or streamline the default review when desired.

- **AC-2.1** Given an incoming direction or task definition explicitly designating an alternative review template, when the review stage is composed, then the designated template substitutes for the default review workflow.
- **AC-2.2** Given a project workspace defining a project-tier review workflow marked `default: true`, when an unspecialized review stage is composed within that project, then the project-tier default template shadows and substitutes for the universal default template.
- **AC-2.3** Given a low-stakes or routine task executing under the default dialectical review, when the supervisor calibrates review proportionality upfront, then it may execute a single-pass sanity check without spawning concurrent subagents.

## Design

The default review architecture provides multi-perspective evaluation while preserving runtime workflow composition and caller substitution:

1. **Resolution Hierarchy**:
   When resolving an independent review stage:
   - **Explicit Designation**: When the caller, task brief, or user directive names a specific review template, that template is composed.
   - **Project-Tier Default**: In the absence of an explicit designation, a project-scoped template tagged `review` with `default: true` shadows universal defaults.
   - **Universal-Tier Default**: In the absence of an explicit designation or project override, the composing agent selects the universal template tagged `review` marked `default: true`.
   - **Collision Handling**: If multiple templates within the same tier declare `default: true` under the `review` tag, resolution halts loudly with a collision failure.

2. **Internal Perspective Coordination & Proportionality**:
   The default review workflow coordinates multiple specialist review perspectives concurrently as internal subagents under an evaluative supervisor, returning a single consolidated findings synthesis and reconciled verdict (`PASS`, `REVISE`, or `FAIL`). Spawning subagents internally allows deep dialectical evaluation within a single assigned review worker task without requiring outer orchestrators to manage multiple review tasks.
   The supervisor evaluates task complexity and stakes upfront: high-stakes and architectural tasks receive full multi-agent dialectical deliberation; routine or low-stakes tasks execute via single-pass review.

3. **Headless Release Contract**:
   A review worker executing the default review workflow releases its task with terminal status strictly matching the review outcome:
   - A `PASS` verdict releases the task as `done` with the structured review report and verification evidence.
   - A `REVISE` or `FAIL` verdict releases the task as `failed` (or `partial`), recording findings and defect tags in the release reason. The worker never prompts interactively, pauses for user input, or mints downstream tasks on the graph.

## Open questions

None.
