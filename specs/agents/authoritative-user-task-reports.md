---
title: Authoritative User Task Reports in Pauli
status: ready
type: spec
tags: [pauli, task-state, user-authority, lifecycle, capture, enforcement]
---

# Authoritative User Task Reports in Pauli

Defines the protocol under which the knowledge base graph custodian treats the user's first-person reports of real-world actions, completed steps, and state changes as authoritative over task state, reconciling task bodies and recording user-directed lifecycle transitions without waiting for external workers or reconciliation sweeps.

## User stories

### US-1 Authoritative handling of user-reported task progress and facts

As the graph custodian, I want to treat the user's first-person reports of completed actions or changed facts as authoritative primary-source evidence, so that the knowledge base accurately reflects real-world state and never preserves contradictory or obsolete to-do statements.

- **AC-1.1** Given a direct or relayed statement from the user reporting that a task step or real-world action has occurred, when the graph custodian evaluates or updates the corresponding task node, then the custodian updates the node body to reflect current state, checks off completed acceptance criteria (`- [x]`), and removes obsolete contradictory assertions.
- **AC-1.2** Given a user prompt or incoming brief containing both completed actions and subsequent work requests, when the graph custodian processes the input, then the custodian isolates the reported factual completion from the forward-looking ask, identifies the matching target node semantically via graph search, and reconciles the body concisely without pasting conversational prose.
- **AC-1.3** Given a factual report that affects durable domain knowledge beyond an ephemeral task body, when the graph custodian reconciles the task, then the custodian routes durable facts to their appropriate knowledge topic notes rather than turning the task record into an append-only log.

### US-2 Lifecycle status transitions driven by user reports

As the user, I want my reports of task completion or cancellation to be recorded directly on task lifecycle status by the custodian, so that tasks I have finished or abandoned never resurface as active to-dos on subsequent daily runs.

- **AC-2.1** Given a user report that satisfies all remaining acceptance criteria or declares a task fully finished, when the graph custodian reconciles the node, then the custodian transitions the task status to `done` on the user's behalf, providing completion evidence derived from the user's report.
- **AC-2.2** Given a user report indicating that a pending objective or task has been abandoned, superseded, or made redundant by external events, when the graph custodian reconciles the node, then the custodian transitions the task status to `cancelled`.
- **AC-2.3** Given a user report that settles only a partial subset of acceptance criteria on a multi-step task, when the graph custodian reconciles the node, then the custodian updates the body and checklist while preserving the task's existing active status (`queued` or `in_progress`).

### US-3 Preservation and operational interpretation across relay chains

As the graph custodian receiving a delegation brief from an upstream coordinating agent, I want to treat user completion statements contained within the brief as operative instructions for graph maintenance, so that factual updates are never discarded as inert narrative context.

- **AC-3.1** Given an upstream agent brief that includes the user's first-person report of an action taken alongside a request for follow-up work, when the graph custodian reads the brief, then the custodian executes the factual state update against the referenced task before or during the execution of the follow-up request.
- **AC-3.2** Given incoming brief context that contradicts existing body text on an open task node, when the graph custodian touches the node, then the custodian resolves the contradiction in favor of the user's statement under standing maintenance authority.

## Design

### Factual Authority of User Reports

The user's first-person statement that an action was taken or that an external fact has changed is primary-source testimony. When the graph custodian encounters a user report in direct conversation or within an upstream agent brief:

1. **Semantic Relevance & Target Node Resolution**: The custodian extracts the entities, actions, and project context from the user's statement and queries open tasks via semantic graph search. The custodian matches the statement against open task deliverables, titles, and acceptance criteria.
2. **Reconciliation of Current State**: In accordance with the Single Source of Truth and Current State Only principles, the custodian updates the target node body immediately. Any text stating that the action is pending (e.g., statements asserting that a communication has not been sent or an appointment not yet scheduled) is deleted. The corresponding acceptance criterion item is checked (`- [x]`).
3. **Calibrating Information Density**: Task bodies remain strictly concise (50–150 words). The custodian does not append conversational excerpts, timestamps, or narrative logs to task bodies. Durable facts (such as contact updates or policy decisions) are stored in destination topic notes; task bodies carry only the remaining active work checklist and pointers.

### Lifecycle Status Ownership Harmonization

Framework governance assigns lifecycle status to specific owners: the user promotes to `queued`, executing workers claim and release, and reconciliation sweeps correct structural drift.

This specification harmonizes user task reports with the lifecycle ownership model:

1. **The User as Primary Lifecycle Owner**: The user is the principal and ultimate owner of task lifecycle. When the user reports that an action is finished or that work is no longer needed, the user is exercising lifecycle authority.
2. **Ministerial Execution by the Custodian**: The custodian does not claim autonomous discretion over lifecycle status; rather, the custodian acts ministerially on the user's behalf to record the declared lifecycle transition.
3. **Scope of State Transitions**:
   - **Partial Step Completion**: When the user's report satisfies some but not all acceptance criteria of an active task, the custodian updates the body and checklist only. The task status remains unchanged (`queued` or `in_progress`).
   - **Full Task Completion**: When the user's report satisfies all remaining acceptance criteria, or when the user explicitly states that the task is finished, the custodian transitions the task status to `done` on the user's behalf, supplying completion evidence derived from the user's statement.
   - **Cancellation**: When the user indicates that a task is no longer required or has been abandoned, the custodian transitions the task status to `cancelled`.

### Relay Preservation and Operational Status

Investigation of execution traces demonstrates that upstream coordinating agents do not drop the user's task-relevant statements. Relaying agents capture the user's words and transmit them in delegation briefs.

The breakdown in prior workflows occurred at the boundary of semantic categorization:

- Relaying agents framed the user's completed actions as narrative background for downstream tasks rather than distinct maintenance asks.
- The graph custodian received the briefs and rewrote the target tasks, but treated the reported completion as background narrative rather than an operative instruction to update task state.
- Existing custodian instructions specifically restricted lifecycle status changes and lacked an explicit directive recognizing user reports as authoritative for task state.

Under this specification, the custodian is explicitly instructed that any user factual report contained within an incoming brief has operative force over the referenced task's body and lifecycle status.

## Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, mechanisms to enforce authoritative user task reporting were evaluated across the enforcement pyramid from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Rejected.** Universal axioms (`Durable Capture`, `Current State Only`) declare the principles of capturing truth and eliminating stale state, but failed in practice because the custodian's explicit instructions restricted lifecycle status changes and did not define how to handle user completion reports. |
| 2 | `instructions` (`imperative` / `absolute`) | **Adopted.** Adding explicit imperative directives to `plugins/ida/agents/pauli.md` directly resolves the conflict. It instructs the custodian to treat user reports as authoritative for task state, update task bodies immediately, and record user-directed lifecycle transitions to `done` or `cancelled`. This provides precise behavioral steering at zero token overhead for unrelated tasks. |
| 3 | `JIT injection` | **Evaluated.** Injecting reminders on prompt submission was considered. Prompt hydration already injects relevant task context; adding separate reminder hooks is redundant when clear instructions in the agent persona govern the custodian's deliberation. |
| 4 | `structural` | **Evaluated.** Mechanical NLP parsers or regex filters to detect "I did X" phrases violate `judgment-non-delegable` and `no-over-engineering`. Identifying semantic equivalence between conversational reports and task criteria requires agentic qualitative judgment. |
| 5 | `process` | **Evaluated.** Review lenses (`wf-strategic-fit`, `wf-rbg`) evaluate PR artifacts but do not run during conversational task updates in active user sessions. |
| 6 | `post-hoc` | **Evaluated.** Daily sweeps and reconciliation jobs detect some forms of graph drift, but empirical evidence shows sweeps scoped to specific message classes miss conversational reports of completed actions. Prevention at the point of custody is required. |

### Evidence for the Move

1. **Empirical Failure in Runtime Traces**: In multi-agent execution traces, a user reported having emailed to schedule an appointment and requested a subsequent planning document. The coordinating agent relayed the report in the delegation brief. The graph custodian rewrote the target task twice to update its title and scope for the downstream request, but retained the sentence asserting that the appointment was not yet scheduled and left the checklist item unticked.
2. **Defect in Lifecycle Ownership Framing**: The custodian definition explicitly stated: "You own structure, not lifecycle status ... Lifecycle status belongs to its owners -- the user promotes to `queued`, the worker claims and releases, `/reconcile` corrects." Because user completion reports were not listed among recognized lifecycle triggers, the custodian treated the report as narrative context rather than an authoritative state transition.
3. **Sweep Gaps**: Subsequent automated sweeps failed to correct the stale task state because correspondence sweeps were scoped narrowly to explicit reply tasks, while prompt sweeps evaluated prompts solely as work requests rather than statements of completed action.

## Enforcement Map Extract (for Downstream Implementation)

Per `specs/enforcement/enforcement-map.md § 3`, single-carrier prompt and persona instructions reside in their respective definition files (`plugins/ida/agents/pauli.md`) and are not added as standalone rows to `specs/ENFORCEMENT-MAP.md`. During downstream Stage 2 implementation, the existing governing rule rows in `specs/ENFORCEMENT-MAP.md` will have their `Detail` coordinates updated to reference the new Pauli persona instructions:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts, and update existing documents in the knowledge base rather than creating duplicates. | instructions, JIT injection, process | imperative, warning, required gate | `plugins/rbg/skills/axioms/durable-capture.md:9`, `plugins/ida/agents/pauli.md` (authoritative user task reports), `plugins/ida/skills/remember/SKILL.md:10-70`, `plugins/ida/skills/q/SKILL.md:12-65`, `plugins/ida/skills/dump/SKILL.md:15-55`, `plugins/ida/hooks/handlers.py:594-638` (`search_the_pkb`), `wf-reconcile.md:1-55` |
| [Project Rule: Current State Only](../.agents/rules/current-state-only.md) -- Maintain current state only across the repository. Do not preserve backwards compatibility or maintain history in instructions or code. | instructions, process | imperative, required gate | `.agents/rules/current-state-only.md:1-20`, `plugins/ida/agents/pauli.md` (body reconciliation and elimination of contradictory pending state), `plugins/rbg/agents/rbg.md:16-44`, `.github/PULL_REQUEST_TEMPLATE.md:1-40` |

## Outcome-Level Build Criteria (for Downstream Implementation)

The downstream implementation task (Stage 2) must satisfy the following verifiable criteria:

- [ ] **BC-1 (Authoritative Task Body Updates)**: When the graph custodian receives or identifies a user report of an action completed or real-world state changed, the custodian identifies the matching open task node, checks off completed acceptance criteria (`- [x]`), deletes contradictory pending assertions, and updates the body to current state.
- [ ] **BC-2 (User-Directed Lifecycle Status Transitions)**: When a user report satisfies all acceptance criteria of a task, or explicitly declares the task finished or abandoned, the custodian transitions the task status to `done` or `cancelled` on the user's behalf with completion evidence derived from the user's statement.
- [ ] **BC-3 (Instruction Quality and Concision)**: Proposed modifications to `plugins/ida/agents/pauli.md` conform to `/craft` standards--concise, general across the entire class of tasks, free of PKB identifiers or conversational histories, and preserving the single source of truth.
