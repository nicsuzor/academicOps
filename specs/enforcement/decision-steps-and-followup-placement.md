---
id: decision-steps-and-followup-placement
title: Decision Steps on Design Research and Task Follow-Up Structural Placement
status: draft
type: spec
tags: [enforcement, workflow-library, task-contract, reify, execution, decisions]
---

# Decision Steps on Design Research and Task Follow-Up Structural Placement

This specification establishes the architectural standard and structural invariants for two foundational workflow rules across academicOps:

1. **Decision Step on Design Research Invariant:** Every research task addressing an open design question, architectural pattern, or implementation alternative includes by default a dedicated decision task assigned to the user, dependent on the research findings, to select an implementation route before downstream implementation work can unblock.
2. **Review and Follow-Up Placement Invariant:** Every task requiring an independent review, verification, or subsequent follow-up step is structured either as a single task with internal subtasks (when executable by the same agent in one session) or as an epic with separate child tasks (when multi-session or independent context is required); never as loose siblings under an external parent.

## 1. User Stories

### US-1: Decision Step on Design Research

As the framework principal (the user), I want every research task exploring open design questions or architectural choices to provide a dedicated decision task assigned to me, so that I can choose the implementation route before downstream build tasks proceed.

- **AC-1.1**: Given an objective requiring research into open design questions, architectural patterns, or technology choices, when `/reify` composes the workflow, then it creates a research task and an explicit downstream decision task assigned to the user (`assignee: user`) that `depends_on` the research task.
- **AC-1.2**: Given a design decision task on the graph, when implementation tasks are composed, then all implementation tasks are wired with `depends_on` the decision task, remaining blocked until the user selects the route and completes the decision task.

### US-2: Task Review and Follow-up Structural Placement

As an execution supervisor and dispatch coordinator, I want tasks requiring review or follow-up to be structured as internal subtasks or dedicated epics with child tasks, so that tasks never become loose siblings with deadlocked dependencies.

- **AC-2.1**: Given a task requiring review or follow-up that can be executed by the same agent in one continuous session, when `/reify` composes the task, then it structures the review and follow-up as internal checklist subtasks within a single task body.
- **AC-2.2**: Given a task requiring review or follow-up that requires independent sessions, clean context, distinct reviewer personas (`pauli`, `rbg`, `marsha`), or human decisions, when `/reify` composes the task, then it structures the work as a dedicated epic with separate child tasks (e.g. Child 1: Primary Task, Child 2: Review / Follow-up), with dependencies wired between children (`Child 2` `needs: [Child 1]`).
- **AC-2.3**: Given a task and its subsequent follow-up or review step, when `/reify` or any coordinator places them on the graph, then they are never placed as loose siblings under an external parent.

## 2. The Two General Rules (Stated Over Their Whole Class)

Both rules apply across the entirety of the framework, covering all domains, repositories, and workflow compositions.

### Rule 1: Decision Step on Design Research

> **Operative Rule:**
> Every research task investigating an open design question, architectural pattern, technology evaluation, or implementation trade-off must, by default, include a dependent decision task assigned to the user (`assignee: user`) that depends on the research artifact. In this decision task, the user selects the implementation route. Downstream implementation tasks are strictly blocked on this decision task.

- **Class Definition:** Applies to all tasks composed with `wf-research`, `wf-research-and-implement`, or any task whose primary deliverable is an evaluation of architectural options, trade-offs, or designs.
- **Exemptions:** Purely factual lookups, empirical reproduction runs, data health diagnostics, or retrospective log audits that do not decide future design or architecture do not require a decision task.
- **Task Contract:**
  - `Title`: `Decide implementation route for <objective>` (imperative, descriptive; no personal names in titles).
  - `Assignee`: Assigned to the user (`assignee: user`) via frontmatter metadata.
  - `Dependency`: `depends_on: [<research_task_id>]`.
  - `Body`: Concise pointers to the research findings, a clear summary of competing candidate routes, and the concrete trade-offs, with a default recommendation.
  - `Unblocking Behavior`: Downstream build or specification tasks wire `depends_on: [<decision_task_id>]` (or `needs: [<decision_task_id>]`), ensuring implementation cannot proceed until the user records the chosen route.
- **Interaction with Graph Option Nodes:** The decision task serves as the governing human gate ($D$). Where competing technical approaches are pre-composed on the graph, candidate option nodes attach to $D$ via `alternative` edges; when the user resolves $D$ by selecting an option, the winning node is adopted and competing alternatives are marked `cancelled` per `specs/meta/naming-and-decisions.md`. Where implementation is reified after the decision, completing $D$ triggers reification of the chosen implementation route.

### Rule 2: Review and Follow-Up Structural Placement Invariant

> **Operative Rule:**
> Every task requiring a review, verification, or subsequent follow-up step must be structured in exactly one of two valid topological patterns:
>
> 1. **Single Task with Internal Subtasks:** If all steps (e.g. build, local verification, documentation) can be executed by the **same agent in one continuous session**, they must remain internal subtasks (checklist items) within a single task body.
> 2. **Dedicated Epic with Child Tasks:** If the steps require **independent sessions, clean execution context, distinct reviewer personas (`pauli`, `rbg`, `marsha`), different tool boundaries, or human decision gates**, the work must be structured as a dedicated epic containing separate child tasks (e.g. Child 1: Primary Task, Child 2: Review / Decision / Follow-up), with dependencies explicitly wired between children (`Child 2` `needs: [Child 1]`).
>
> **Prohibition:** A task and its subsequent follow-up or review step must **never be created as loose siblings under an external parent**.

- **Class Definition:** Applies to all tasks that generate or require follow-up work: QA reviews, multi-stage code tasks (`wf-code-task-base`), documentation tasks (`wf-doc-base`), design-to-build progressions, escalated sign-offs, and verification passes.
- **Topological Clarification:** Child tasks under a dedicated epic share that epic as a parent and are explicitly sequenced via child-to-child `needs` edges. The pathology prohibited by this rule is minting follow-up tasks as _loose siblings under a broad external parent epic_ alongside unrelated parallel deliverables, which corrupts parent scope and causes graph dispatch deadlocks.

## 3. Highest Tier Placement in the Workflow Library

Under `plugins/ida/skills/workflow-library/SKILL.md`, the workflow library is structured in three tiers:

1. **Project Tier** (PKB templates scoped to a project)
2. **PKB Tier** (Personal knowledge base templates)
3. **Universal Tier** (`${CLAUDE_SKILL_DIR}/workflows/` / `plugins/ida/skills/workflow-library/workflows/`)

The **Universal Tier** is the highest architectural authority across all repositories and execution environments. Placing these rules at the highest tier ensures every workflow inherits them before domain-specific customization.

### Universal Artifacts Updated

1. **`plugins/ida/skills/workflow-library/SKILL.md` (Workflow Library Core Standard):**
   - Incorporates the foundational topological invariant: all composed workflows requiring review or follow-up must instantiate either as a single task with internal checklist subtasks or as an epic with child tasks; never as loose siblings.
   - Codifies the default requirement for decision tasks following design research.
2. **`plugins/ida/skills/workflow-library/workflows/wf-task-base.md` (Universal Task Foundation):**
   - The root template composed onto every task. States the structural placement rule directly in its contract.
3. **`plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md` (Universal Code Task Foundation):**
   - Formalizes multi-stage progressions as a dedicated epic with child tasks: Stage 1 (Design), Stage 2 (Build), and Stage 4 (Review) form children under a dedicated epic with explicit child-to-child `needs` edges, or execute as internal subtasks when allowable.
4. **`plugins/ida/skills/workflow-library/workflows/wf-doc-base.md` (Universal Documentation Task Foundation):**
   - Replaces loose sibling task structures with the dedicated epic pattern for multi-stage documentation and spec drafting (Child 1: Drafting, Child 2: Independent Review).
5. **`plugins/ida/skills/workflow-library/workflows/wf-research.md` (Universal Research Template):**
   - In its **Composition** section, establishes that when `/reify` composes research addressing design questions or architectural choices, `/reify` automatically composes a dependent decision task assigned to the user on the graph. The worker's execution procedure in isolated containers remains focused on documenting findings without minting graph tasks (`headless-workers.md`).
6. **`plugins/ida/skills/workflow-library/workflows/wf-research-and-implement.md` (Universal Composite):**
   - Formalizes Stage 4 as a dedicated decision task assigned to the user, strictly blocking Stage 5 (Implementation).

## 4. Comprehensive Audit of Contradicting Instructions & Amendments

A repository-wide audit of instructions, skills, agent definitions, and specifications across `plugins/`, `specs/`, and `.agents/` identified the following contradicting instructions. Each contradiction is paired with its required amendment.

### Audit Item 1: `plugins/ida/skills/reify/SKILL.md`

- **Location 1 (line 114):**
  - _Existing Contradicting Text:_ `- Do not create standalone decision tasks or file questions as tasks.`
  - _Amendment:_ `- Do not create standalone decision tasks or file questions as tasks, with the exception of design research tasks: any research task on a design question gets, by default, a decision task assigned to the user (assignee: user) that depends on the research results, in which the user chooses the implementation route.`
- **Location 2 (lines 86–98, Mint QA follow-up):**
  - _Existing Contradicting Text:_
    `3. Set parent to the primary task's parent.`
    `4. Wire dependency: needs: [<primary_task_id>] so the QA task stays blocked until the primary task is done.`
  - _Amendment:_
    `3. Structure the task and its QA review either as a single task with internal subtasks (if executable by the same agent in one session) or as a dedicated epic with child tasks (Child 1: Primary Task, Child 2: QA Task with needs: [<child_1_id>]); never mint a follow-up or review task as a loose sibling under an external parent.`
- **Location 3 (line 46):**
  - _Existing Contradicting Text:_ `- Write each follow-up the workflow calls for as its own task. Never fold a follow-up into the primary task or into another follow-up.`
  - _Amendment:_ `- When a task and its follow-up can be executed by the same agent in one session, structure them as a single task with internal subtasks. When independent sessions or review personas are required, structure them as a dedicated epic with child tasks, never as loose siblings.`

### Audit Item 2: `plugins/ida/skills/dispatch/SKILL.md`

- **Location (line 19):**
  - _Existing Contradicting Text:_
    `- A task that folds follow-ups into itself is not ready: send it to /reify to be cut.`
  - _Amendment:_
    `- A task that folds follow-ups into internal subtasks is ready when executable by the same agent in one session; only send to /reify when work requires independent sessions, personas, or approval gates that must be cut into an epic with child tasks.`

### Audit Item 3: `.agents/rules/RULES.md`

- **Location (lines 64–71, Decisions Emerge from Graph Relationships):**
  - _Existing Contradicting Text:_
    `Agents must never create standalone "decision" tasks or file questions as backlog tickets.`
  - _Amendment:_
    `Agents must never create un-actionable "decision" tasks or file conversational questions as backlog tickets. Where research investigates an open design question or architectural alternatives, it must by default include a decision task assigned to the user (assignee: user) that depends on the research findings to decide an implementation route before downstream implementation tasks can proceed.`

### Audit Item 4: `plugins/ida/agents/pauli.md`

- **Location (lines 54 & 56–58):**
  - _Existing Contradicting Text:_
    `- **Decisions and questions emerge from graph relationships:** Never create standalone "decision" tasks or file questions as tasks. Represent competing alternatives as mutually exclusive option nodes with mutual blocking edges where choosing one branch resolves the conflict, and model unknowns as empirical probe tasks (classification: spike). In-turn questions use AskUserQuestion directly.`
    `Parent/child is already an edge: Setting parent_id automatically links the node into its parent hierarchy. Do not wire edges between siblings or descendants under the same parent unless there is a specific, genuine interaction...`
  - _Amendment:_
    `- **Decisions and questions emerge from graph relationships:** Never create un-actionable "decision" tasks or file routine questions as tasks. For design research, an explicit decision task assigned to the user (assignee: user) is required by default to select an implementation route before build work can proceed. All tasks requiring review or follow-up must be structured as a single task with internal subtasks (if executable in one session) or as an epic with separate child tasks; never as loose siblings under an external parent.`

### Audit Item 5: `specs/meta/naming-and-decisions.md`

- **Location (Section 3, lines 48–56):**
  - _Existing Contradicting Text:_
    `1. Abolition of Standalone Decision Tasks: Standalone "decision" tasks are strictly prohibited across all prompts, skills, and documentation.`
  - _Amendment:_
    `1. Abolition of Un-actionable Decision Tickets & Preservation of Design Decision Gates: Standalone "decision" tasks filed as holding bins for open conversational questions are strictly prohibited. In contrast, structured decision tasks assigned to the user that resolve an explicit design research fork and unblock downstream implementation are authorized and mandatory for design research workflows, operating in harmony with option-node branching (§4).`

### Audit Item 6: `plugins/ida/skills/workflow-library/workflows/wf-research.md`

- **Location (Composition section, lines 30–36):**
  - _Existing Contradicting Text:_
    (Omitted any composition rule for subsequent decision gates).
  - _Amendment:_
    `## Composition: When /reify composes a research task investigating an open design question or architectural alternatives, /reify automatically creates a dependent decision task assigned to the user (assignee: user) on the graph (Title: Decide implementation route for <topic>, depends_on: [<research_task_id>]), strictly blocking downstream implementation until the decision is recorded.`

### Audit Item 7: `specs/enforcement/task-contract.md`

- **Location (line 64):**
  - _Existing Contradicting Text:_
    `- **Decisions as graph relationships** -- decisions and questions must never be created as standalone "decision" tasks.`
  - _Amendment:_
    `- **Decisions as graph relationships and design gates** -- un-actionable question tasks are prohibited. Design research tasks receive a dedicated decision task assigned to the user to choose an implementation route. Tasks requiring review or follow-up are structured as a single task with subtasks or as an epic with child tasks, never as loose siblings.`

## 5. Enforcement Pyramid & Proportionality Analysis

Per `specs/enforcement/enforcement.md`, every measure shaping agent behavior must run through the enforcement pyramid options from least invasive to most invasive:

1. **`doctrine only`**: Evaluated and rejected as sole mechanism. High-level principles failed to prevent agents from eliminating decision steps or minting sibling review tasks.
2. **`instructions` (`imperative`)**: **Selected as primary mechanism.** Updating universal workflow templates, `/reify`, and agent personas places explicit requirements at the moment of composition. Defaulting to instructions preserves flexibility while imposing clear constraints. Evaluating whether an inquiry is a design question requires qualitative semantic judgment (`judgment-non-delegable.md`) and must remain with the composing agent rather than a rigid regex/AST script.
3. **`JIT injection`**: Evaluated and deferred. Not required at intake since `/reify` and workflow composition natively consult the workflow library and task base templates.
4. **`structural` (`block`)**: **Restricted strictly to mechanical graph topology.** Mechanical validation may enforce that tasks with sequential `needs` dependencies cannot share an external parent without a dedicated epic container. Mechanical blocking of research tasks without decision tasks is rejected because classifying design questions requires semantic judgment.
5. **`process` (`required gate`)**: **Selected as verification backstop.** The multi-lens strategic review (`wf-review`, `strategic-review` via `pauli`, `rbg`, `marsha`) audits task graphs, specifications, and PR structures to verify adherence to topological invariants.
6. **`post-hoc` (`observability`)**: Retained. Phoenix traces and PKB graph inspection verify that research epics contain decision nodes and multi-stage tasks avoid loose sibling wiring.

### Protection of User Attention

User cognitive load is protected by:

- Confining decision tasks strictly to **design questions** (where principal authority over system architecture is substantive);
- Restricting decision cards to **one question per message** with a concise recommendation grounded in primary research evidence;
- Forbidding decision tasks for routine operational steps, bug fixes, or mechanical refactors.

## 6. Entry Point Analysis & One-Step Placement

| Entry Point | Location | Current Contradiction / Failure Mode | One-Step Move | Category & Severity |
| - | - | - | - | - |
| **1. Universal Workflow Standards** | `plugins/ida/skills/workflow-library/SKILL.md`, `wf-task-base.md`, `wf-code-task-base.md`, `wf-doc-base.md` | Base templates omit the follow-up placement invariant and default design research decision step. | Codify both rules as universal invariants across all task templates at the library's highest tier. | `instructions`, `imperative` |
| **2. Research Workflow Templates** | `plugins/ida/skills/workflow-library/workflows/wf-research.md`, `wf-research-and-implement.md` | Research composition omits queueing a decision task for the user to choose the implementation route. | Add compositional requirement for a dependent decision task assigned to the user (`assignee: user`) on design research. | `instructions`, `process` (`required gate`) |
| **3. Task Reification Engine** | `plugins/ida/skills/reify/SKILL.md`, `specs/agents/reify.md` | Explicitly commands setting QA parent to primary task's parent (minting siblings) and unconditionally bans decision tasks. | Amend `/reify` to mandate single-task-with-subtasks or dedicated epics with children, and add design decision task rule. | `instructions`, `imperative` |
| **4. Task Dispatch Engine** | `plugins/ida/skills/dispatch/SKILL.md` | Directs sending tasks that fold follow-ups into themselves back to `/reify` to be cut. | Amend dispatch check to permit internal subtasks for single-session execution. | `instructions`, `imperative` |
| **5. Agent Personas & Rules** | `plugins/ida/agents/pauli.md`, `.agents/rules/RULES.md` | Unconditional ban on decision tasks and imprecise sibling edge guidance. | Align Pauli instructions and project rules with design decision gates and epic-child hierarchy. | `instructions`, `imperative` |
| **6. Architectural Specs** | `specs/meta/naming-and-decisions.md`, `specs/enforcement/task-contract.md`, `specs/enforcement/workflow.md` | Specifies total abolition of decision tasks without carving out design research approval gates. | Update specifications to differentiate legacy anti-patterns from authorized architectural decision gates. | `instructions`, `imperative` |

## 7. Enforcement-Map Extract

The following rows are scheduled for addition to `specs/ENFORCEMENT-MAP.md`:

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Design Research Decision Gate](enforcement/decision-steps-and-followup-placement.md#rule-1-decision-step-on-design-research) -- Every research task on a design question gets by default a decision task assigned to the user that depends on research results to decide the implementation route. | instructions, process | imperative, required gate | `plugins/ida/skills/workflow-library/workflows/wf-research.md:30-36`, `plugins/ida/skills/workflow-library/workflows/wf-task-base.md:8-14`, `plugins/ida/skills/reify/SKILL.md:114`, `specs/meta/naming-and-decisions.md:48`: Mandates that research on design questions or architectural choices queues a dependent decision task assigned to the user (`assignee: user`) before downstream implementation work can unblock. |
| [Task Follow-Up & Review Placement Invariant](enforcement/decision-steps-and-followup-placement.md#rule-2-review-and-follow-up-structural-placement-invariant) -- Tasks needing review or follow-up must be created as a single task with internal subtasks (if single session) or as a dedicated epic with child tasks (if multi-session); never as loose siblings. | instructions, structural | imperative, block | `plugins/ida/skills/workflow-library/SKILL.md:12-25`, `plugins/ida/skills/workflow-library/workflows/wf-task-base.md:8-14`, `plugins/ida/skills/reify/SKILL.md:86-98`, `plugins/ida/skills/dispatch/SKILL.md:19`, `plugins/ida/agents/pauli.md:54,56-58`, `.agents/rules/RULES.md:62`: Requires tasks with reviews or follow-ups to be structured either as single tasks with internal subtasks or as dedicated epics with child tasks, strictly prohibiting loose sibling placement under external parents. |

## 8. Outcome-Level Build Criteria for Implementation

The Stage 2 (Build) implementation task must satisfy the following verifiable criteria:

1. **Universal Workflow Library Base Updates**:
   - `plugins/ida/skills/workflow-library/SKILL.md`, `wf-task-base.md`, `wf-code-task-base.md`, `wf-doc-base.md`, `wf-research.md`, and `wf-research-and-implement.md` embody both rules explicitly.
2. **Reification & Dispatch Logic Realignment**:
   - `plugins/ida/skills/reify/SKILL.md` contains zero instructions directing follow-up tasks to be minted as siblings of their primary task (`parent = primary_task.parent` removed).
   - `/reify` mandates internal subtasks for single-session units and dedicated epics with child tasks for multi-session/review units.
   - `/reify` exception for design research decision tasks is explicitly codified.
   - `plugins/ida/skills/dispatch/SKILL.md` permits single-task units with internal subtasks.
3. **Agent Persona & Rule Alignment**:
   - `plugins/ida/agents/pauli.md` and `.agents/rules/RULES.md` are amended to permit design research decision tasks and enforce epic-child follow-up structuring.
4. **Architectural Specification Sync**:
   - `specs/meta/naming-and-decisions.md`, `specs/enforcement/task-contract.md`, and `specs/enforcement/workflow.md` are updated in the same PR.
5. **Enforcement Register Update**:
   - `specs/ENFORCEMENT-MAP.md` incorporates the two new rows from §7.
6. **Full Verification**:
   - `make lint` and pytest suites pass cleanly with 0 errors.

## 9. Baseline-vs-Changed Verification Protocol

### Test Case 1: Design Research Workflow

- **Input Prompt:** `"Research candidate state store options (SQLite vs DuckDB) for session tracing and design the migration route."`
- **Baseline Behavior (Pre-Change):**
  - `/reify` mints a research task.
  - Worker investigates and completes research.
  - Task releases `done` with no decision step.
  - Workflow stalls or worker guesses an implementation choice.
- **Changed Behavior (Post-Change):**
  - `/reify` composes a research task (`T1: Research state store options`) under an epic.
  - `/reify` automatically mints a dependent decision task (`T2: Decide state store implementation route`, `assignee: user`, `depends_on: [T1]`).
  - Downstream build tasks (`T3: Implement selected state store`) are wired with `depends_on: [T2]`, preventing execution until the user decides.

### Test Case 2: Multi-Stage Task with Independent QA Review

- **Input Prompt:** `"Implement user rule caching in hook handlers, requiring an independent quality review."`
- **Baseline Behavior (Pre-Change):**
  - `/reify` mints `T_build` under Parent Epic `P`.
  - `/reify` mints `T_qa` with `parent = P` and `needs: [T_build]`.
  - `T_build` and `T_qa` are siblings under `P`, creating sibling dependency deadlocks during batch dispatch.
- **Changed Behavior (Post-Change):**
  - `/reify` detects independent review requirement.
  - `/reify` creates a dedicated epic `E: User rule caching`.
  - Inside `E`, `/reify` creates `Child 1: Build user rule caching` and `Child 2: QA: User rule caching`, with `Child 2` `needs: [Child 1]`.
  - No loose siblings under external parents are minted.

## 10. Open Questions

- None. All architectural decisions, role abstractions (`the user`), headless worker composition contracts, and graph topological rules have been reconciled against governing framework standards and peer review feedback.
