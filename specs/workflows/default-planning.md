---
title: Default Planning Workflow
status: ready
---

# Default Planning Workflow

Defines the planning workflow across projects: in academicOps, design changes require an in-repository technical specification reviewed by independent agents and delivered alongside implementation code on a single pull request into `dev`; across all other projects, plans are captured directly on the knowledge base task graph, with detailed plans reified as dedicated reviewable plan tasks rather than repository markdown documents.

## User stories

### US-1 Specification-first design for academicOps changes

As a framework architect contributing to academicOps, I want proposed design changes specified in the repository's specification format, reviewed by independent agents, and delivered alongside implementation code on a single pull request into `dev`, so that system architecture remains documented and vetted without opening code-less pull requests or requiring manual approval of specifications without code.

- **AC-1.1** Given a proposed design change in academicOps, when planning starts, then the design is authored as an in-repository specification following the canonical specification template and document taxonomy.
- **AC-1.2** Given an authored academicOps specification preceding a build, when submitted for review, then it is recorded in a knowledge base note or task record and reviewed by independent agents, without opening a pull request carrying a specification without code and without releasing the specification for principal approval on its own.
- **AC-1.3** Given an academicOps specification with all independent agent review findings resolved, when implementation proceeds, then implementation builds the feature and the specification together on the feature branch.
- **AC-1.4** Given implementation and specification changes, when delivered, then a single pull request is opened into `dev` as a draft (`gh pr create --draft`) carrying both the specification and its implementation code.
- **AC-1.5** Given a draft pull request carrying specification and code, when the independent check passes and mandatory independent review verdicts are posted to the pull request thread, then the pull request is marked ready for review (`gh pr ready`) without waiting for approval.

### US-2 Direct task-graph planning for general projects

As a developer planning work for repositories outside academicOps, I want implementation plans recorded directly on the task graph as tasks, so that project repositories remain focused on code and documentation while task tracking stays on the knowledge base.

- **AC-2.1** Given a proposed change or feature outside academicOps, when planning is initiated, then the plan is captured directly onto the knowledge base task graph through intake and reification.
- **AC-2.2** Given a general project planning workflow, when tasks are dispatched, then pull requests target functional implementation only.

### US-3 Proportionately reviewed plan tasks for detailed approvals

As a developer requiring explicit principal approval for a non-trivial architectural plan outside academicOps, I want a dedicated task created on the task graph to document the plan and an independent worker to review it proportionately before principal sign-off, ensuring complex plans receive rigorous review on the task graph.

- **AC-3.1** Given a non-trivial change outside academicOps requiring plan approval prior to implementation, when the initiative is reified, then a planning task is composed; and when executed, the planning worker authors a new unqueued knowledge base task specifying the plan, objective-level acceptance criteria, weighed alternatives, and primary sources.
- **AC-3.2** Given a reified plan task on the knowledge base, when the plan task is drafted, then an independent worker reviews the plan task proportionately across quality, strategic fit, and compliance.
- **AC-3.3** Given a reviewed plan task with findings resolved, when review completes, then the plan task is presented to the principal on the task graph for approval before implementation is queued or dispatched.
- **AC-3.4** Given principal approval of the plan task, when implementation starts, then the approved plan task is queued for execution with code delivered via standard pull request.

## Design

### 1. The Planning Boundary: Repository Specs vs Task-Graph Plans

Planning artifacts are partitioned by repository governance:

1. **academicOps Design Changes**:
   - academicOps maintains an authoritative, version-controlled architecture specification corpus in the repository.
   - Every design change in academicOps (architectural overhaul, rule change, multi-component refactor, or new capability) is authored as a formal specification following the repository's specification standard and document taxonomy.
   - In a spec-then-build workflow (one pull request, opened by the build), the design stage records its design, any drafted specification change, and its independent agent review verdicts on the knowledge base in a note or task record that the implementation task references. The design stage commits no plan or design file to the repository and opens no pull request.
   - Mandatory review of the specification in the design stage is carried out by independent agents, never by the principal. Review findings are resolved before implementation proceeds, and the design stage never puts a specification to the principal for approval on its own.
   - The implementation stage builds on the feature branch, committing both the specification and the implementation code together.
   - The implementation stage opens a single pull request into `dev` as a draft (`gh pr create --draft`) carrying both the specification and its implementation code. The specification remains editable on the branch as implementation progresses.
   - The draft pull request is marked ready for review (`gh pr ready`) only after the independent check passes and proportionate review by independent agents is posted to the pull request thread, without waiting for principal approval.
   - The specification and its implementation code reach the principal for approval together on that single pull request, merging together after full review.

2. **General Projects (The Default Planning Workflow)**:
   - For all repositories other than academicOps, implementation plans, design proposals, and decision alternatives reside on the knowledge base task graph.
   - Planning workflows direct plans to the knowledge base task graph by default. Target repositories receive functional code and documentation only, with pull requests reserved for functional changes.
   - Work flows through intake and task reification, creating task nodes directly on the knowledge base graph without opening pull requests containing planning or design files against target repositories.

3. **Detailed Plan Approval via the Knowledge Base**:
   - When an initiative outside academicOps involves high complexity, architectural uncertainty, irreversible commitments, or explicit requirements for principal approval before implementation:
     a. **Plan Task Authoring**: A worker executes a planning task that generates a new, unqueued task on the knowledge base. This plan task conforms to canonical task invariants: concise (50–150 words), defining objective-level acceptance criteria mapped to verifiable behaviors rather than implementation recipes, and factoring durable architectural background or trade-off analyses into linked knowledge notes rather than accreting narrative into the task body. The plan is recorded as a knowledge base task; no plan or design file is committed to any repository and no pull request is opened before the build.
     b. **Proportionate Independent Review & Remediation**: A separate, independent agent worker reviews the newly minted plan task on the knowledge base. The review evaluates simplicity and reuse (quality), alignment with originating asks and parent objectives (strategic fit), and conformity to axioms and project rules (compliance). The review worker folds minor refinements directly into the plan task; for blocking defects, findings are recorded on the record for remediation before escalation.
     c. **Headless Approval Lifecycle**: Workers operate headlessly and hand back on the task record upon completing their stage. The reviewed plan task remains unqueued on the graph, gating downstream execution until the principal explicitly approves and queues the task for execution.
     d. **Execution**: Upon principal approval, the plan task is queued for worker execution. Implementation proceeds test-first where code executes, and the worker pull request opened against the target repository opens as a draft (`gh pr create --draft`) containing the functional implementation and goes ready for review (`gh pr ready`) only after the independent check passes.

## Open questions

None.
