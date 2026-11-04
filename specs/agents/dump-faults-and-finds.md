---
title: Dump Skill Triggers for Operational Faults and Major Finds
status: draft
type: spec
tags: [dump, session-lifecycle, handover, pkb, retroactive-tasks, daily-note]
---

# Dump Skill Triggers for Operational Faults and Major Finds

This specification establishes the contracts, triggering conditions, and reporting thresholds for capturing significant operational faults and major diagnostic findings in the session exit and handover skill (`dump`). It extends retroactive task creation and daily note project reporting to cover sessions that diagnose and resolve significant faults or uncover major findings even when no repository project files are modified, establishes clear demarcations separating significant operational actions from routine operational activity, and defines outcome-level build criteria for downstream implementation.

## User stories

### US-1 Retroactive task creation for operational faults and service recoveries

As a practitioner or autonomous agent recovering a service or remediating an operational fault without modifying repository files, I want `dump` to require creating a retroactive task documenting the fault and remediation on the knowledge graph before session exit, so that operational recoveries and bug fixes are durably tracked rather than lost.

- **AC-1.1 (Operational fault recovery trigger)**: Given an ad-hoc or operational session that identified and fixed, or recovered from, a significant operational fault (such as a 502 gateway outage, container crash, authentication breakdown, or dead service daemon) without modifying repository project files, when `dump` executes, then the skill requires creating a retroactive task on the knowledge graph that captures the semantic goal, symptoms, diagnostic root cause, operational actions taken, and verified recovery evidence, releasing the task immediately as complete.
- **AC-1.2 (Demarcation from routine operations)**: Given an ad-hoc session that performs routine infrastructure checks, health pings, inspecting logs showing healthy operations, ephemeral local container restarts during normal development without an underlying fault, or queue inspections, when `dump` executes, then the session is exempt from retroactive task creation.
- **AC-1.3 (Headless worker containment)**: Given a dispatched worker operating under an assigned task, when unparented operational faults outside the assigned task boundary are encountered, then the worker treats the scope mismatch under standard task containment rules, recording observations for handover rather than silently minting unrelated retroactive tasks.

### US-2 Daily note project updates for major finds without code modifications

As the principal reviewing daily progress across projects, I want `dump` to include a project update bullet in the daily note for major operational recoveries and diagnostic discoveries even when no repository code changed, so that major findings and operational milestones are immediately visible in daily reviews.

- **AC-2.1 (Major find daily update trigger)**: Given a session that resolved a significant operational fault, achieved a major operational milestone, or uncovered a critical systemic finding without modifying repository code, when `dump` compiles daily note updates, then it includes a consolidated bullet under the touched project in the preserved daily work section (`## Today's work`) summarizing the find or recovery and its immediate status.
- **AC-2.2 (Demarcation from routine operational activity)**: Given a session that executes routine commands, standard monitoring checks, or informational queries that uncover no unexpected conditions or service recoveries, when `dump` compiles daily note updates, then no daily note project bullet is required for projects lacking code modifications or major finds.
- **AC-2.3 (Headless worker concurrency protection)**: Given a headless worker session operating in an isolated execution environment, when a major find occurs without code changes, then the worker emits the consolidated project bullet in its structured handover block on the record for subsequent absorption by daily sweeps rather than writing directly to shared daily notes.

## Design

### 1. Operational Fault Retroactive Task Trigger

The retroactive task protocol in `dump` requires capturing durable operational changes on the knowledge graph:

- **Expanded Trigger**: Any ad-hoc or interactive session that either:
  1. Modified repository project files (source, tests, configuration, specifications) without an assigned task; OR
  2. Identified and fixed, or recovered from, a significant operational fault (such as resolving an outage, reviving a crashed daemon, recovering from a gateway failure, or fixing an authentication breakdown), even when no repository files were modified.
- **Threshold of "Significant Fault"**:
  - Service downtime or severe degradation (e.g., HTTP 500/502/503 errors, inaccessible web endpoints, dropped connection gateways).
  - Crashed, stuck, or memory-leaking containerized services or background daemons requiring manual intervention or restarts.
  - Security, certificate, or credential failures preventing legitimate operations.
  - Latent system defects diagnosed to root cause, even if the immediate fix is an operational command (e.g., cache flush, container restart) and the code fix is deferred.
- **Demarcation: Routine Operations (Exempt)**:
  - Routine system inspections, status checks, or running diagnostic queries that report healthy state.
  - Ephemeral container restarts performed as standard initialization during routine development setup without an underlying fault.
  - Routing work: triage sweeps, queue inspections, passing messages, dispatching workers.
  - Conversational inquiries and informational queries that alter no files and uncover no faults.
- **Bug Tracking Demarcation**:
  - The retroactive task captures the operational recovery chore on the knowledge graph.
  - Any latent software defect or underlying code bug uncovered during the incident is filed as an issue on the issue tracker ("Bugs go on GitHub only"), rather than tracking software bug backlogs inside ephemeral task descriptions.
- **Procedure**:
  1. Mint a task on the knowledge graph via the task creation interface with `classification: chore` or `implementation`, specifying a `parent` node linking to the relevant project or standing operational epic (e.g., platform infrastructure or operations) to prevent orphan root tasks.
  2. Provide a concise, verb-led imperative task title describing the recovery or fix (e.g., `Recover gateway from 502 outage`).
  3. Format the task body using the canonical 5-section concise template (`Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) per standard task brevity invariants (`synthesize-not-accrete`). Specific CLI execution traces, diagnostic logs, and recovery checks belong in task completion metadata (`status: done` release evidence), while enduring architectural insights belong in durable topic notes offered to the knowledge base custodian.
  4. Release the task immediately as complete (`status: done`), supplying `completion_evidence` detailing the recovery actions and verified health check.

### 2. Major Find Daily Note Project Update Trigger

The consolidated daily note project update protocol in `dump` ensures visibility of major non-code operational milestones:

- **Expanded Trigger**: Projects touched during a session are determined by:
  1. Repository files modified; OR
  2. Claimed or retroactive tasks updated; OR
  3. Major operational finds or service recoveries achieved, even when no repository code changed.
- **Threshold of "Major Find"**:
  - Remediating a significant service outage or operational fault.
  - Isolating the root cause of an elusive or long-standing systemic issue.
  - Significant empirical discovery during analysis or inspection that invalidates a working hypothesis or uncovers a critical dependency risk.
- **Demarcation: Routine Operations (Exempt)**:
  - Running standard commands, exploratory queries, or routine maintenance checks that yield expected results.
  - Pure routing, queue triage, or dispatch operations with no novel findings.
- **Project Attribution**:
  - Recoveries of shared infrastructure services, daemons, or gateways attribute to the relevant platform infrastructure project.
- **Recording Format**:
  - _Interactive / Coordinator Sessions_: Write exactly one consolidated bullet per touched project into the daily note under `## Today's work`:
    ```markdown
    - **<project-name>**: <latest status or major find in 10-20 words> -- Next: <pointer or resumption prompt>
    ```
    If the completed recovery has no follow-up task or resumption prompt, omit the `-- Next: ...` suffix:
    ```markdown
    - **<project-name>**: <latest status or major find in 10-20 words>
    ```
  - _Headless / Isolated Worker Sessions_: Emit the consolidated project status in the handover block on the record to prevent concurrent multi-writer race conditions; automated daily note sweeps absorb them.

### 3. Outcome-Level Build Criteria for Downstream Implementation (Stage 2)

Downstream implementation in Stage 2 must satisfy the following outcome-level criteria without prescribing brittle file-slice edits:

- **BC-1 (Retroactive Task Trigger for Faults)**: Given an agent executing `dump` after resolving an operational service disruption without modifying repository files, when the agent evaluates wrap-up requirements, then the skill instructions direct the agent to create and release a retroactive task documenting the fault, remediation, and recovery evidence.
- **BC-2 (Routine Operation Exemption)**: Given an agent executing `dump` after routine status checks or benign operational queries without modifying repository files, when the agent evaluates wrap-up requirements, then the skill instructions explicitly exempt the session from creating a retroactive task.
- **BC-3 (Daily Note Update for Major Finds)**: Given an agent executing `dump` after diagnosing or resolving a major operational issue without modifying repository files, when compiling project updates, then the skill instructions direct the agent to include a project bullet in the daily note (or handover record for headless sessions) summarizing the find.
- **BC-4 (Cross-Distribution Consistency)**: Given all packaged plugin distributions built from the canonical source, when the build pipeline runs, then the revised instructions are synchronized across all platform distributions.

### 4. Proportional Enforcement Pyramid Options Pass and One-Step Placement

Any measure intended to shape agent behavior must run through the enforcement pyramid options pass evaluated from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Insufficient.** Universal axioms (`Durable Capture`, `Full Observability`) establish the high-level duty to capture knowledge and persist material work, but existing skill text tied retroactive tasks and daily bullets strictly to modified repository files, causing agents to actively reject task creation for operational fixes. |
| 2 | `instructions` (`imperative`) | **Adopted as primary mechanism.** Updating `plugins/ida/skills/dump/SKILL.md` with explicit, imperative rules governing operational faults and major finds is the least-invasive, most proportionate intervention. Agent instructions operate directly at the cognitive decision point during session exit without creating brittle mechanical tooling dependencies. |
| 3 | `JIT injection` | **Rejected.** Injecting dynamic reminders during interactive sessions on every command or tool call introduces token overhead and distraction when wrap-up logic is needed only at session exit. |
| 4 | `structural` | **Rejected.** Deterministic heuristics or file-diff checks cannot distinguish between a significant service recovery (e.g. restoring an outage) and a routine benign command. Evaluating whether an operational find is "significant" inherently requires qualitative semantic judgment (`judgment-non-delegable`). |
| 5 | `process` | **Adopted for PR review.** Candidate instruction updates undergo independent dialectical review (`strategic-review`) to verify adherence to craftsmanship standards, rule compliance, and quality. |
| 6 | `post-hoc` | **Adopted for observability.** Retroactive task records and daily note bullets provide auditable evidence of operational work in the knowledge base and session traces. |

**One-Step Placement**:
The change is implemented as a single, cohesive update to the `dump` skill instructions (`plugins/ida/skills/dump/SKILL.md`), updating the retroactive task creation section and the daily note project update section, paired with updating the enforcement map.

### 5. Open questions

None. All triggering thresholds, demarcations, task schemas, and outcome-level build criteria are resolved.

### 6. Evidence for the Move

1. **Direct User Directive**:
   - The framework principal directed (console, 2026-11-04): "you found and fixed a pretty big bug, so you should have created a task. Make sure that the /ida:dump instructions make that point -- add a bullet to the daily list if you find something major, even if you don't change the code."
   - Under the framework authority model, explicit user directions approve the change and establish the requirement for immediate execution.
2. **Empirical Failure at Current Placement**:
   - In an operational session that diagnosed an HTTP 502 gateway outage and successfully recovered the production service by restarting containers, the agent emitted the following handover: "Task: Ad-hoc ops, no PKB task. I only restarted containers and edited no repo files, so no retroactive task was needed."
   - Because the previous `dump` skill instructions tied retroactive tasks strictly to modifying repository project files and daily note updates to projects with touched files or tasks, the agent strictly followed the letter of the instructions and omitted both the task and the daily note bullet.
   - This failure provides direct empirical evidence that the existing instruction boundary is under-inclusive, necessitating an explicit expansion to cover significant faults and major finds.

### 7. Enforcement Map Extract (for Downstream Implementation)

The following rows will be updated in `specs/ENFORCEMENT-MAP.md` during downstream implementation (Stage 2) when the skill instructions are merged:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts, update existing documents rather than creating duplicates, create retroactive tasks for unparented file changes and significant operational fault recoveries, and route durable facts to the knowledge base custodian. | instructions, JIT injection, process | imperative, warning, required gate | `plugins/rbg/skills/axioms/durable-capture.md:9`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/remember/SKILL.md:10-70`, `plugins/ida/skills/q/SKILL.md:12-65`, `wf-reconcile.md:1-55` |
| [Axiom: Full Observability](../plugins/rbg/skills/axioms/full-observability.md) -- Persist material actions in git commits and knowledge graph tasks with clear rationale, print session IDs in handovers, and record consolidated project updates in the daily note for modified files and major operational finds. | instructions, structural, process, post-hoc | imperative, protection, required gate, observability | `plugins/rbg/skills/axioms/full-observability.md:9`, `plugins/ida/skills/dump/SKILL.md`, `claude_code_tracer.py:1-180`, `agy_tracer.py:1-140` |
