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
- **AC-1.4** Given implementation and specification changes, when delivered, then a single pull request is opened into `dev` carrying both the specification and its implementation code.
- **AC-1.5** Given a pull request carrying specification and code, when prepared for review and merge, then mandatory independent reviews are performed by agents with verdicts posted to the pull request thread before the pull request is marked ready for review.

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
   - academicOps maintains an authoritative, version-controlled architecture corpus under `specs/`.
   - Every design change in academicOps (architectural overhaul, rule change, multi-component refactor, or new capability) must be authored as a formal specification matching the canonical template in `specs/meta/writing-specs.md` and placed in accordance with `specs/meta/doc-taxonomy.md`.
   - In a spec-then-build workflow (one PR, opened by the build), Stage 1 records its design, any drafted spec change, and its review verdicts on the knowledge base in a note or task record the Stage 2 task points to. Stage 1 commits no plan or design file and opens no pull request.
   - Mandatory review of the specification in Stage 1 is carried out by independent agents, never by the principal. Review findings are resolved before Stage 2 proceeds. Stage 1 never releases as `review` or puts a specification to the principal for approval on its own.
   - Stage 2 implementation builds on the feature branch, committing both the specification and the implementation code together.
   - Stage 2 opens the single pull request into `dev` carrying both the specification and its implementation code (opened as a draft using `--draft` when requiring reviewer or principal approval). The specification remains editable as the build teaches more.
   - Proportionate review by independent agents is posted to the pull request thread before the pull request is marked ready for review (`gh pr ready`), without waiting for approval.
   - The specification and its code reach the principal for approval together on that single pull request, merging together after full review.

2. **General Projects (The Default Planning Workflow)**:
   - For all repositories other than academicOps, implementation plans, design proposals, and decision alternatives reside exclusively on the knowledge base task graph.
   - Universal workflow templates direct planning to the knowledge base task graph by default. Target repositories receive functional code and documentation only, with pull requests reserved for functional changes.
   - Work flows through standard intake (`/q`) and reification (`/reify`), creating task nodes directly on the knowledge base graph.
   - No draft pull requests containing planning or design files are opened against external repositories.

3. **Detailed Plan Approval via the Knowledge Base**:
   - When an initiative outside academicOps involves high complexity, architectural uncertainty, irreversible commitments, or explicit requirements for principal approval before implementation:
     a. **Plan Task Authoring**: A worker executes a planning task that generates a new, unqueued task on the knowledge base. This plan task conforms to canonical task invariants: strictly concise (50–150 words), defining objective-level acceptance criteria mapped to verifiable behaviors rather than implementation recipes, and factoring durable architectural background or trade-off analyses into linked knowledge notes (`type: note`) rather than accreting narrative into the task body. The plan is recorded exclusively as a knowledge base task; no plan or design file is committed to any repository and no PR is opened before the build.
     b. **Proportionate Independent Review & Remediation**: A separate, independent worker reviews the newly minted plan task on the knowledge base. The review evaluates simplicity and reuse (quality), alignment with originating asks and parent objectives (strategic fit), and conformity to axioms and project rules (compliance). The review worker folds minor refinements directly into the plan task; for blocking defects, findings are recorded on the record for remediation before escalation.
     c. **Headless Approval Lifecycle**: Workers operate headlessly and hand back on the task record upon completing their stage. The reviewed plan task remains unqueued on the graph (`status: ready` or `inbox`), gating downstream execution until the principal explicitly promotes the task to `status: queued`. Workers never release as `review`.
     d. **Execution**: Upon principal approval, the plan task is queued for worker execution (`/dispatch`). Implementation proceeds test-first where code executes, and the first pull request opened against the target repository contains the actual functional implementation.

## Open questions

None.

## Verification mapping

| Text / Touchpoint | Tier | Route Contract | Verification Check |
| - | - | - | - |
| `plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md` | Universal | Plans stay on PKB; Stage 1 commits no plan/spec and opens no PR; Stage 2 opens single PR carrying build and spec; agent review posted to PR before ready | Inspect template text for `One PR, opened by the build` and absence of code-less spec PRs or spec-only approval releases |
| `plugins/ida/skills/workflow-library/workflows/wf-finish.md` | Universal | Universal finish baseline: one PR opened by build into base branch; draft PR flipped to ready after proportionate agent review; no code-less spec PR | Inspect template lines for `One PR, opened by the build` and worker completion checklist |
| `plugins/ida/skills/workflow-library/workflows/wf-spec.md` | Universal | Stage 1 records spec draft on PKB note, opens no PR; Stage 2 opens draft PR with build + spec; agent review posted to PR before ready | Inspect template lines for `One PR, opened by the build` and submit procedure |
| `plugins/ida/skills/workflow-library/workflows/wf-research-and-implement.md` | Universal | Research and spec stay on PKB; implementation opens single draft PR with build + spec; agent review posted to PR | Inspect template lines for `One PR, opened by the build` and stage descriptions |
| `.agents/templates/wf-finish.md` | Project | Stage 1 records on PKB, opens no PR; Stage 2 opens draft PR to `dev` with build + spec; merges together after agent review | Inspect template lines for `One PR, opened by the build` and `dev` base branch |
| `.agents/templates/develop-specification.md` | Project | Stage 1 records drafted spec and agent review on PKB, opens no PR; build task opens draft PR with build + spec | Inspect template lines for `One PR, opened by the build` and step 12 submit procedure |
| `aops-wf-finish` | PKB (Project) | Opens PR into `dev`; Stage 1 opens no PR; agent reviews posted to PR before ready; never release `review` | Inspect PKB document body for `One PR, opened by the build` and release contract |
| `aops-wf-dev-task` | PKB (Project) | One PR opened by build; Stage 1 agent review, no code-less spec PR, no release as `review`; Stage 2 carries spec + build | Inspect PKB document body for `One PR, opened by the build` and procedure |
| `aops-wf-framework-change` | PKB (Project) | Stage 1 enforcement pass + agent review recorded on PKB, opens no PR; Stage 2 opens PR into `dev` with code + spec + map update | Inspect PKB document body for `One PR, opened by the build` and two-stage gate |
| `aops-wf-spec` | PKB (Project) | Stage 1 records spec + agent review on PKB, opens no PR; Stage 2 opens PR into `dev` with build + spec; never release `review` | Inspect PKB document body for `One PR, opened by the build` and submit step |
| `wf-code-design` | PKB (Universal) | Plan recorded as PKB task, no plan in repo, no PR before build; points to `aops-wf-spec` for academicOps | Inspect PKB document body for PKB plan task route and academicOps pointer |
| `plugins/ida/skills/reify/SKILL.md` | Skill | Directs plans to PKB task graph; never directs committing plans or opening code-less spec PRs; mandatory agent reviews | Inspect skill instructions for workflow composition and plan routing |
| `plugins/ida/skills/q/SKILL.md` | Skill | Captures asks and plans to task graph, separating tasks from repo markdown files | Inspect skill instructions for task placement |
| `plugins/ida/skills/decompose/SKILL.md` | Skill | Expands objectives into abstract graph nodes, never repo plan documents | Inspect skill instructions for objective-level graph modeling |
| `plugins/ida/skills/workflow-library/SKILL.md` | Skill | Dynamic discovery across Project > PKB > Universal tiers; enforces non-interactive resolution | Inspect skill instructions for tier resolution |
| `specs/meta/doc-taxonomy.md` | State | Plans, roadmaps, and decision alternatives belong on PKB task graph as tasks, not as repo markdown files | Inspect doc-taxonomy for guidance under State and Instructions |
| `specs/enforcement/workflow.md` | Spec | Spec-then-build lifecycle: one PR opened by build into `dev`; Stage 1 opens no PR; agent reviews | Inspect section 2 (Execution) and risk-scaled review depth |
| `specs/ENFORCEMENT-MAP.md` | State | Row 54 cites default planning route and pinpoints | Inspect row 54 for `specs/workflows/default-planning.md` citation |

## Appendix: Affected Templates and Skills (Implementation Touchpoints)

This inventory documents the templates, skills, and documentation files updated to realize this specification:

### Universal Workflow Templates (`plugins/ida/skills/workflow-library/workflows/`)

- `wf-code-task-base.md`:
  - Maintains Stage 1 (Design) and output contracts: plans go directly to the knowledge base task graph; Stage 1 commits no plan or design file and opens no PR.
  - Stage 2 build opens the only PR into the base branch carrying the build and any spec change.
  - The PR flips to ready only after proportionate review by agents is posted to the PR thread, without waiting for approval.

- `wf-finish.md`:
  - Maintains universal finish policy: Stage 1 records design on the PKB and opens no PR.
  - Stage 2 build opens the only PR into the base branch as a draft carrying the build and any spec change, marked ready after proportionate review by agents.

- `wf-spec.md`:
  - Maintains Stage 1 spec authoring and review on the PKB with no PR opened; Stage 2 build delivers spec and code together on a single PR.

- `wf-research-and-implement.md`:
  - Sequences research and spec stages onto the PKB with no PR opened; implementation opens the single draft PR carrying build and spec change.

### Project-Local Templates (`.agents/templates/` & PKB Project Templates)

- `.agents/templates/wf-finish.md`:
  - Specifies task delivery into `dev`; Stage 1 records on PKB and opens no PR; Stage 2 build opens draft PR carrying spec and build.

- `.agents/templates/develop-specification.md`:
  - Specifies repository specification development under the "One PR, opened by the build" lifecycle; Stage 1 agent review recorded on PKB; Stage 2 opens draft PR into `dev` with build and spec change.

- `aops-wf-finish`, `aops-wf-dev-task`, `aops-wf-framework-change`, `aops-wf-spec`, `wf-code-design` (PKB tier):
  - Updated so Stage 1 records design and agent reviews on the PKB with no PR opened and no release as `review`.
  - Stage 2 opens the single PR into `dev` carrying both spec and code, marked ready only after proportionate review by agents is posted to the PR thread.

### Planning Skills (`plugins/ida/skills/`)

- `plugins/ida/skills/reify/SKILL.md`:
  - Directs plans onto the PKB task graph; avoids directing workers to commit plan files or open code-less spec PRs; mandatory agent reviews.

- `plugins/ida/skills/q/SKILL.md`:
  - Captures asks and plans directly onto the task graph.

- `plugins/ida/skills/decompose/SKILL.md`:
  - Decomposes objectives into abstract graph nodes, never repository plan files.

- `plugins/ida/skills/workflow-library/SKILL.md`:
  - Governs template resolution across Project > PKB > Universal tiers.

### Architectural State & Documentation (`specs/`)

- `specs/meta/doc-taxonomy.md`:
  - Clarifies that design plans, roadmaps, and decision alternatives belong on the PKB task graph as tasks, not as markdown files in project repositories.

- `specs/enforcement/workflow.md`:
  - Affirms the spec-then-build lifecycle: one PR opened by the build into `dev`, with agent reviews.

- `specs/ENFORCEMENT-MAP.md`:
  - Maps the spec-then-build PR lifecycle rule to `specs/workflows/default-planning.md`.
