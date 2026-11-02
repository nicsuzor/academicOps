---
title: Default Planning Workflow
status: draft
---

# Default Planning Workflow

Defines the planning workflow across projects: in academicOps, design changes require an in-repository technical specification reviewed by agents and approved by the principal before implementation proceeds; across all other projects, plans are captured directly on the knowledge base task graph, with detailed plans reified as dedicated reviewable plan tasks rather than repository markdown documents.

## User stories

### US-1 Specification-first design for academicOps changes

As a framework architect contributing to academicOps, I want proposed design changes specified in the repository's specification format, reviewed by independent agents on a draft pull request, and approved by the principal before building begins, so that system architecture remains documented, vetted, and approved prior to code modifications.

- **AC-1.1** Given a proposed design change in academicOps, when planning starts, then the design is authored as an in-repository specification following the canonical specification template and document taxonomy.
- **AC-1.2** Given an authored academicOps specification, when submitted for review, then it is committed to a feature branch and opened as a draft pull request into the integration base branch carrying the specification and no implementation code.
- **AC-1.3** Given a draft pull request containing an academicOps specification, when independent agents review the specification, then review verdicts are recorded on the pull request thread.
- **AC-1.4** Given an academicOps specification with all review findings resolved, when the specification task completes, then it is held for principal approval before implementation work begins.
- **AC-1.5** Given approved specification changes, when implementation proceeds, then implementation builds on the same branch and pull request, and the pull request is marked ready for review only after implementation completes.

### US-2 Direct task-graph planning for general projects

As a developer planning work for repositories outside academicOps, I want implementation plans recorded directly on the task graph as tasks, so that project repositories remain focused on code and documentation while task tracking stays on the knowledge base.

- **AC-2.1** Given a proposed change or feature outside academicOps, when planning is initiated, then the plan is captured directly onto the knowledge base task graph through intake and reification.
- **AC-2.2** Given a general project planning workflow, when tasks are dispatched, then pull requests target functional implementation only.

### US-3 Proportionately reviewed plan tasks for detailed approvals

As a developer requiring explicit principal approval for a non-trivial architectural plan outside academicOps, I want a dedicated task created on the task graph to document the plan and an independent worker to review it proportionately before principal sign-off, ensuring complex plans receive rigorous review on the task graph.

- **AC-3.1** Given a non-trivial change outside academicOps requiring plan approval prior to implementation, when reifying the task, then one worker authors a new unqueued knowledge base task specifying the plan, objective-level acceptance criteria, weighed alternatives, and primary sources.
- **AC-3.2** Given a reified plan task on the knowledge base, when the plan task is drafted, then an independent worker reviews the plan task proportionately across quality, strategic fit, and compliance.
- **AC-3.3** Given a reviewed plan task with findings resolved, when review completes, then the plan task is presented to the principal for approval before implementation is queued or dispatched.
- **AC-3.4** Given principal approval of the plan task, when implementation starts, then the approved plan task is queued for execution with code delivered via standard pull request.

## Design

### 1. The Planning Boundary: Repository Specs vs Task-Graph Plans

Planning artifacts are partitioned by repository governance:

1. **academicOps Design Changes**:
   - academicOps maintains an authoritative, version-controlled architecture corpus under `specs/`.
   - Every design change in academicOps (architectural overhaul, rule change, multi-component refactor, or new capability) must be authored as a formal specification matching `specs/meta/writing-specs.md` and placed in accordance with `specs/meta/doc-taxonomy.md`.
   - The specification is authored on a feature branch and published as a draft pull request against the designated integration base branch (e.g. `release/v1.0-rc0`).
   - Independent reviewing agents evaluate the specification on the pull request thread. All findings must be resolved.
   - The specification task releases for principal approval. Implementation work remains strictly blocked until approval is recorded.
   - Implementation continues on the same feature branch and draft pull request; the pull request is converted to ready for review once the implementation and its tests are complete. Spec and code merge together.

2. **General Projects (The Default Planning Workflow)**:
   - For all repositories other than academicOps (including repositories that maintain no specifications), implementation plans, design proposals, and decision alternatives reside exclusively on the knowledge base task graph.
   - Work flows through standard intake (`/q`) and reification (`/reify`), creating task nodes directly on the knowledge base graph.
   - Target repositories receive functional code and documentation only, with pull requests reserved for functional changes.

3. **Detailed Plan Approval via the Knowledge Base**:
   - When an initiative outside academicOps involves high complexity, architectural uncertainty, irreversible commitments, or explicit requirements for principal approval before implementation:
     a. **Plan Task Authoring**: A worker executes a planning task that generates a new, unqueued task on the knowledge base. This plan task articulates the concrete goal, outcome-level acceptance criteria, primary source citations, and alternatives considered. The plan is recorded exclusively as a knowledge base task.
     b. **Proportionate Independent Review**: A separate, independent worker reviews the newly minted plan task on the knowledge base. The review evaluates simplicity and reuse (quality), alignment with originating asks and parent objectives (strategic fit), and conformity to axioms and project rules (compliance). Findings are reconciled directly on the plan task.
     c. **Principal Approval Gate**: Once independent review passes, the reviewed plan task is submitted to the principal for approval.
     d. **Execution**: Upon principal approval, the plan task is queued for worker execution (`/dispatch`). Implementation proceeds test-first where code executes, and the first pull request opened against the target repository contains the actual functional implementation.

### 2. Affected Templates and Planning Skills

Implementing this specification requires updating the following workflow templates, planning skills, and taxonomy documents to align with target behaviour:

#### Universal Workflow Templates (`plugins/ida/skills/workflow-library/workflows/`)

- `wf-code-task-base.md`:
  - Update Stage 1 (Design) and output contracts to eliminate instructions directing workers in non-spec projects to commit plan markdown files to the repository and open draft pull requests.
  - Define the general planning route: plans go directly to the knowledge base as tasks. For changes requiring plan approval, compose the PKB plan-task workflow (`wf-code-design`).
  - Restrict draft pull requests in Stage 1 exclusively to repositories that maintain specifications (with academicOps using `aops-wf-spec`).

- `wf-finish.md`:
  - Clarify the "One branch, one PR" and draft PR finish policy to state that draft pull requests carrying Stage 1 deliverables apply exclusively to formal specifications in specification-keeping repositories, never to planning markdown files.

- `wf-spec.md`:
  - Clarify that Stage 1 draft pull requests are reserved for technical specifications in repositories with formal specification architecture.

- `wf-research-and-implement.md`:
  - Align Stage 1 and Stage 2 handoffs to distinguish specification deliverables in specification-governed repositories from task-graph plan deliverables in general projects.

#### Project-Local Templates (`.agents/templates/`)

- `.agents/templates/wf-finish.md`:
  - Reiterate that Stage 1 draft PRs in academicOps carry specifications adhering to repository specification standards, and that plans for external projects belong on the task graph.

- `.agents/templates/develop-specification.md`:
  - Confirm that specification development applies to academicOps processes and features, producing repository specifications in `specs/`.

#### Planning Skills (`plugins/ida/skills/`)

- `plugins/ida/skills/reify/SKILL.md`:
  - Update workflow composition instructions: when reifying design changes for academicOps, select the project-local specification workflow (`aops-wf-spec`).
  - For all other projects, ensure reification directs plans onto the knowledge base graph directly as tasks.
  - Where a detailed plan requires approval before building, compose the PKB plan-task workflow (`wf-code-design`) where one worker authors a new unqueued PKB task, an independent worker reviews it proportionately, and the plan task is approved by the principal before queuing for build.
  - Prohibit reifying Stage 1 tasks that instruct workers to commit plan markdown files or open draft PRs for plans in repositories outside academicOps.

- `plugins/ida/skills/q/SKILL.md`:
  - Affirm that all inbound asks, ideas, and plans capture onto the knowledge base task graph as tasks, maintaining clean separation between task tracking and repository contents.

- `plugins/ida/skills/decompose/SKILL.md`:
  - Clarify that decomposition produces abstract sub-objectives, decision forks, and probes on the graph, never repository plan documents.

- `plugins/ida/skills/workflow-library/SKILL.md`:
  - Confirm the tier resolution where project-local academicOps templates (`aops-wf-spec`) govern academicOps specifications, PKB-tier templates (`wf-code-design`) govern default plan tasks, and universal templates provide base contracts without prescribing repository plan files.

#### Architectural State & Documentation (`specs/`)

- `specs/meta/doc-taxonomy.md`:
  - Add explicit guidance under § State and § Instructions clarifying that design plans, implementation roadmaps, and decision alternatives belong on the knowledge base task graph as tasks, not as markdown files in project repositories (distinguishing them from formal subsystem specs in `specs/`).

- `specs/enforcement/workflow.md`:
  - Update the spec-then-build workflow section to clarify that repository draft pull requests apply to specifications in specification-keeping projects like academicOps, whereas general planning remains native to the task graph.
