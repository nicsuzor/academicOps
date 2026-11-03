---
title: Dump Skill Revision for End-of-Session Wrap-Up
status: ready
type: spec
tags: [ida, dump, session-lifecycle, handover, pkb, daily-note]
---

# Dump Skill Revision for End-of-Session Wrap-Up

This specification establishes the contracts, lifecycle behavior, and reporting requirements for the session exit and handover skill (`dump`). It reframes the skill as the routine, composed wrap-up for all session completions rather than an emergency abort mechanism, defines consolidated daily note updates per touched project, institutes retroactive task creation for ad-hoc file modifications with explicit routing exemptions, mandates durable fact retention and knowledge graph conflict correction on sight, enforces strict prohibitions against fabricated next steps while standardizing resumption prompts for interrupted work, and requires producing session identification in handover reports for end-to-end traceability.

## User stories

### US-1 Routine wrap-up across all session terminations

As an agent or practitioner ending a work session, I want `dump` to act as the standard, composed wrap-up procedure across all completion modes (task done, context reset, tool or environment transition, or unexplained external pause) without treating normal stops as alarm conditions, so that every session exits cleanly, safely, and predictably.

- **AC-1.1 (Standard wrap-up posture)**: Given a session ending normally upon task completion, when the agent invokes `dump`, then the procedure completes file persistence, task status updates, and handover reporting methodically without emitting panic, abort, or emergency failure language.
- **AC-1.2 (Context reset or environment transition)**: Given an agent session stopping to reset context windows or migrate execution to a different tool environment, when `dump` executes, then it records current progress, saves all workspace state, and releases claimed tasks with verified partial progress without treating the transition as an operational failure.
- **AC-1.3 (External or unknowable user interruption)**: Given an external halt or user-directed stop for unspecified reasons, when `dump` executes, then it handles the pause calmly and records the clean state of the workspace while retaining full emergency stop protections (preventing data loss, staging dirty worktrees, and releasing locks).

### US-2 Consolidated daily note project pointers

As the principal reviewing daily progress, I want `dump` to record one consolidated status pointer per touched project in the daily note with its immediate next step, so that project status is scannable at a glance without cluttering the note with fragmented task logs.

- **AC-2.1 (One consolidated pointer per touched project)**: Given a session that modified files or updated tasks across one or more projects, when `dump` compiles its final updates, then it writes exactly one consolidated bullet per touched project into the daily note under the preserved daily work section (`Today's work`), stating the project's current state.
- **AC-2.2 (Project next-step integration)**: Given each project pointer added to the daily note, when `dump` formats the line, then it appends the verified direct follow-up pointer or resumption prompt defined under US-5, or omits the next step if no follow-up exists.
- **AC-2.3 (Preserved block isolation and clean absorption)**: Given the daily note formatting contract where named sections are preserved across automated note composition runs, when `dump` appends project pointers, then it writes them exclusively into the designated preserved daily work section, allowing the subsequent daily note sweep to absorb completed milestones into structured summary views without losing in-flight pointers.

### US-3 Retroactive task creation for unparented project changes

As a maintainer tracking project evolution on the knowledge graph, I want any ad-hoc session that modified project files without an existing task to create a retroactive task documenting the work, so that repository changes are never orphaned from the graph.

- **AC-3.1 (Retroactive task for unparented file changes)**: Given a worker session that executed ad-hoc commands or modifications resulting in uncommitted or committed changes to repository project files (source code, tests, configuration, specifications) without an assigned or existing task, when `dump` executes, then the skill requires creating a retroactive task on the knowledge graph that documents the completed changes, records the commit SHA, and releases the task as complete with verification evidence.
- **AC-3.2 (Exemption for routing work)**: Given an ad-hoc session performing operational routing, dispatching, task triage, or reviewing queues without modifying repository project files, when `dump` executes, then the session is exempt from retroactive task creation.
- **AC-3.3 (Exemption for ephemeral minor edits)**: Given an ad-hoc session executing minor adjustments directly at the user's instruction (such as fixing a minor typo or updating a transient comment) where the information holds no enduring institutional value and would not be useful thirty days later, when `dump` executes, then the session is exempt from retroactive task creation.

### US-4 Durable fact capture and PKB conflict repair

As a knowledge system maintaining durable institutional truth, I want `dump` to capture findings that will remain valuable over six months and invoke the knowledge base custodian to repair or retire conflicting, incorrect, irrelevant, or stale notes encountered during the session, so that knowledge never degrades.

- **AC-4.1 (Six-month durable fact offering)**: Given verified architectural decisions, operational constraints, environment invariants, or factual discoveries made during the session that will remain relevant in six months, when `dump` runs, then it offers these durable facts to the knowledge base custodian (`pauli`) as content (or records them under `## Durable Facts` in the handover block and task record if running in an isolated execution context where the custodian cannot be messaged directly).
- **AC-4.2 (Repairing defective or conflicting knowledge)**: Given conflicting, incorrect, irrelevant, demonstrably false, or outdated knowledge base information encountered during the session, when `dump` runs, then it explicitly directs the knowledge base custodian (`pauli`) to correct the contradictions, prune stale content, and update the canonical topic notes on sight.

### US-5 Disciplined next-step pointers and resumption prompts

As an agent or user picking up after a completed or interrupted session, I want clear, un-invented pointers to existing follow-ups or a copy-pasteable resumption prompt for interrupted tasks, so that the next session resumes immediately without speculative busywork.

- **AC-5.1 (Prohibition against invented next steps)**: Given a completed task with no existing dependent tasks or pre-planned follow-ups on the graph, when `dump` generates the handover report or daily note pointer, then the next step field is left empty or marked `None`, strictly prohibiting fabricated or speculative follow-up suggestions.
- **AC-5.2 (Pointers to pre-existing follow-ups)**: Given a completed task where dependent follow-up tasks, open PR review tasks, or child QA tasks already exist on the graph, when `dump` formats the next step, then it provides an exact pointer (`[[id]]` or URL) to the pre-existing task.
- **AC-5.3 (Resumption prompt for interrupted tasks)**: Given an interrupted, partial, or paused task (e.g. token limit, context refresh, or user interrupt), when `dump` formats the next step, then it generates a self-contained, 2-4 sentence resumption prompt summarizing current state, completed files, and exact next actions that can be pasted directly into a fresh agent's initial prompt.

### US-6 Handover block session traceability

As a framework auditor investigating execution history, I want the session identifier prominently printed in the handover block, so that the handover report links directly to its generating session logs, OpenTelemetry traces, and container records.

- **AC-6.1 (Explicit session ID in handover header)**: Given any execution of `dump`, when the skill emits its structured handover block, then the producing session's identifier (`session_id` / `conversation_id`) is printed directly in the handover heading (`## Handover: <agent> <session-id>`).
- **AC-6.2 (Session ID in task release payload)**: Given task status updates performed during `dump`, when `pkb_release_task` is called, then the active `session_id` is supplied in the release parameters to correlate task state transitions with the executing session.

## Design

### 1. Unified Wrap-Up Posture Across Session Exit Types

The `dump` skill serves as the single universal exit gate for all interactive, automated, and worker sessions. Historically, agent implementations often treated `/dump` as an alarm signal or panic stop, emitting apologies or failure logs when invoked mid-stream. Under this specification, `dump` maintains a calm, disciplined posture across four standard exit triggers:

1. **Task Completion**: The assigned task has met all acceptance criteria with verifiable evidence. Work is committed and pushed, tasks are released as `done`, and a structured handover is emitted.
2. **Context Reset**: The session has approached context token limits or requires a fresh workspace context. Completed modifications are saved, in-progress tasks are released as `partial` with progress documented in `reason`, and a resumption prompt is emitted.
3. **Environment Transition**: Execution needs to move between runtime surfaces (e.g. from local console to headless polecat container, or from code execution to interactive browser). Current state is committed, task status is updated, and clear handover pointers are recorded.
4. **External Pause / Stop**: The user or harness signals an abrupt halt for reasons that may be entirely external or unknowable to the agent. The agent handles the stop without alarm or speculative diagnoses, ensures workspace safety (staging and committing uncommitted changes, releasing locks, and updating task records), and exits cleanly.

### 2. Consolidated Daily Note Project Updates

Under the daily note architecture, the daily note is composed by a scheduled routine that writes the note whole and preserves designated sections verbatim: `### My priorities` (for the user's manual priorities) and `## Today's work` (for in-flight session work).

To prevent daily note clutter while ensuring cross-project visibility:

- **Consolidation**: `dump` inspects all modified repository files and updated tasks across the session to determine which projects were touched.
- **Single Bullet Per Project**: For each touched project, `dump` writes exactly one consolidated bullet into `## Today's work`:
  ```markdown
  - **<project-name>**: <latest status in 10-20 words> -- Next: <pointer or prompt>
  ```
- **Absorption**: When the subsequent automated daily run executes, the daily sweep reads `## Today's work` alongside graph state. Finished milestones are absorbed into structured sections (`## Done for you` or `## Your work`), while active threads remain visible until completed.

### 3. Retroactive Task Creation Protocol

To uphold the principle that repository file changes must be auditable and linked to the knowledge graph:

- **Trigger**: Any session that ran without an active task and made durable modifications to repository files (source code, configuration, tests, schemas, specifications) must create a retroactive task before exiting.
- **Procedure**:
  1. Mint a task on the knowledge graph via the task creation tool with `classification: implementation` or `chore`.
  2. Set `task_title` to a concise imperative description of the completed work.
  3. Include in the body a summary of changes, the list of touched files, and the git commit SHA.
  4. Release the task immediately as `done`, supplying `completion_evidence` referencing the commit SHA and diff.
- **Explicit Exemptions**:
  1. _Routing Work_: Triage sweeps, dispatching workers, queue inspections, and conversational inquiries that do not alter repository project files require no task.
  2. _Ephemeral Minor Edits_: Minor edits requested directly by the user (such as fixing a minor typo or updating an ephemeral comment) where knowing about the change will definitely not be useful thirty days later are exempt from retroactive task creation.

### 4. Durable Fact Retention and Knowledge Graph Repair

This specification aligns the `dump` skill with the framework's knowledge management architecture:

- **Six-Month Threshold**: During session exit, the agent reviews decisions, discoveries, and verified state. Any fact that represents an enduring constraint, architectural decision, or verified environment invariant with a utility horizon of six months or longer must be preserved.
- **Routing to the Custodian**:
  - In connected/interactive sessions, the agent offers the durable facts directly to the knowledge base custodian (`pauli`) as content, leaving note formatting, topic merging, and anti-sprawl checks to the custodian.
  - In isolated or headless worker sessions where subagent communication is unavailable, the worker records the facts under a dedicated `## Durable Facts` section in the task record and handover summary, where the custodian harvests them during regular reconcile sweeps.
- **Retirement and Repair on Sight**: When a session uncovers contradictory, demonstrably false, stale, or obsolete knowledge base documents, the agent directly invokes the custodian (`pauli`) to correct or retire the defective notes on sight, ensuring that obsolete information does not linger across sessions.

### 5. Disciplined Next-Step Rules ("Park on a Downward Slope")

This specification reconciles the handover template contract with the rule that workers do not sequence work:

- **No Speculative Busywork**: Workers and sessions are strictly forbidden from inventing plausible-sounding "next steps" or speculative chores. The task graph and parent epics hold authorized work.
- **Strict Tri-State Next-Step Determination**:
  1. _Pre-Existing Dependent Work_: If an authorized follow-up task, child QA task, or dependent review task already exists on the graph, the `Next step` field provides an explicit pointer to it (`[[task-id]]` or URL).
  2. _Interrupted Work_: If a task is released as `partial` or `in_progress` due to an interruption, context boundary, or user halt, the `Next step` field provides a self-contained 2-4 sentence resumption prompt detailing current state, touched files, and exact starting instructions for a fresh agent.
  3. _Fully Completed Work_: If the task is `done` and no pre-existing dependent task exists on the graph, the `Next step` field states `None`.

### 6. Handover Block Schema with Session Traceability

The handover block emitted at session exit must follow this standardized schema:

```markdown
## Handover: <agent> <session-id / conversation-id>

1. **Task**: <task-id and title, or "Ad-hoc / Retroactive: <id>">
2. **Summary**: Concise synthesis of findings, modifications, and outcomes.
3. **Status & Safeguards**:
   - STATUS: <done | partial | failed | cancelled | in_progress>
   - GATE: <the acceptance criterion id tested, and observed result against it>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <did a clean-room/differential control run? result? -- or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Next step**: <[[task-id]] pointer | Resumption prompt | None>
6. **Durable Facts**: [None | List of durable facts offered to Pauli or recorded for collection]
7. **Argument**: The `argdown` block recorded under the task's `## Report`.
8. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
9. **Rule Violations**: [None | Disclosed violations with rule citations and reasons]
```

### 7. Proportional Enforcement Pyramid Options Pass and One-Step Placement

Any modification shaping agent behavior must run through the enforcement pyramid options pass evaluated from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Insufficient.** Universal axioms (`Durable Capture`, `Single Source of Truth`, `Honest Epistemics`, `Full Observability`) state the high-level policy, but existing handover templates and skill instructions lack the concrete operational rules for daily note updates, retroactive tasks, and disciplined next steps. |
| 2 | `instructions` (`imperative`) | **Adopted as primary mechanism.** Updating `plugins/ida/skills/dump/SKILL.md` with explicit, imperative rules for the six core behaviors is the least-invasive, most proportionate intervention. Agent instructions operate directly at the cognitive decision point during session exit without creating fragile mechanical tooling dependencies. |
| 3 | `JIT injection` | **Rejected.** Dynamic hook injection of exit reminders during session execution would inject unnecessary tokens on every prompt or tool call, adding cost and context noise when wrap-up logic is only needed at session completion. |
| 4 | `structural` | **Adopted for schema only.** Standardizing the structured fields of the handover block (`## Handover: <agent> <session-id>`, `Next step`, `Durable Facts`) provides structural clarity for downstream parsing. Mechanical keyword gates or regex sniffers on exit are rejected as brittle and violating non-mechanical baselines. |
| 5 | `process` | **Adopted for PR review.** Candidate instruction updates undergo independent dialectical review (`strategic-review`) to verify adherence to craftsmanship standards, rule compliance, and quality. |
| 6 | `post-hoc` | **Adopted for observability.** Printing session IDs and recording commit SHAs ensures that all exit operations are verifiable via session traces and git history. |

**One-Step Placement**:
The change is implemented as a single, cohesive update to the `dump` skill instructions (`plugins/ida/skills/dump/SKILL.md`), paired with synchronizing the handover template and daily note documentation to ensure cross-tier consistency.

### 8. Evidence for the Move

1. **Direct User Directives**:
   - The framework principal directed (console, 2026-11-03) that the `dump` skill be revised to provide consolidated daily note project pointers, require retroactive tasks for unparented project changes (with routing and minor edit exemptions), file 6-month durable facts and invoke Pauli to repair PKB contradictions on sight, enforce strict next-step discipline (pointing to existing work or providing resumption prompts rather than inventing next steps), and present itself as a routine, calm wrap-up across all termination modes.
   - The principal earlier directed (console, 2026-10-22) that `/dump` print the session ID in its handover block for complete auditability. Under the direct user instructions rule, these directives carry an immediate execution obligation.
2. **Reconciliation of Contradictory Handover Rules**: Existing handover guidance in `wf-handover` required a `Next step` field without restrictions, leading agents to fabricate speculative follow-ups. Simultaneously, daily reconcile rules established that workers do not sequence work. This revision resolves the conflict by allowing only pre-existing task pointers or resumption prompts for interrupted work.
3. **Preventing Untracked Repository Drift**: Ad-hoc exploration and interactive sessions frequently modified project files without creating task records on the knowledge graph, leaving git changes orphaned from the issue and task tracking graph. Instituting retroactive task creation closes this auditability gap.
4. **Eliminating Exit Panic Posture**: Prior agent behavior frequently treated `/dump` as an abort condition or emergency halt, emitting apologetic narrative and confusing ordinary context resets with catastrophic failures. Establishing a routine wrap-up posture ensures consistent, reliable exit behavior.

### 9. Enforcement Map Extract (for Downstream Implementation)

The following rows will be updated in `specs/ENFORCEMENT-MAP.md` during downstream implementation when the skill instructions are merged:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts, update existing documents rather than creating duplicates, create retroactive tasks for unparented file changes, and route durable facts to Pauli. | instructions, JIT injection, process | imperative, warning, required gate | `plugins/rbg/skills/axioms/durable-capture.md:9`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/remember/SKILL.md:10-70`, `plugins/ida/skills/q/SKILL.md:12-65`, `wf-reconcile.md:1-55` |
| [Axiom: Single Source of Truth](../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact without duplication, retiring or repairing conflicting knowledge base content on sight. | instructions, structural, process | imperative, protection, required gate | `build/build.py:42-95`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/remember/SKILL.md:10-48`, `wf-reconcile.md:15-50` |
| [Axiom: Honest Epistemics](../plugins/rbg/skills/axioms/honest-epistemics.md) -- State unknowns explicitly, tailor claims strictly to evidence, and prohibit inventing speculative next steps during session handover. | instructions, JIT injection, structural, process | imperative, warning, block, required gate | `plugins/rbg/skills/axioms/honest-epistemics.md:9-11`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/premise-check/SKILL.md:49-123` |
| [Axiom: Full Observability](../plugins/rbg/skills/axioms/full-observability.md) -- Accompany every discrete modification with a git commit and push, print session IDs in handovers, and record consolidated project updates in the daily note. | instructions, structural, process, post-hoc | imperative, protection, required gate, observability | `plugins/rbg/skills/axioms/full-observability.md:9`, `plugins/ida/skills/dump/SKILL.md`, `claude_code_tracer.py:1-180`, `agy_tracer.py:1-140` |
| [Project Rule: Headless Workers Cannot Pause for a Person](../.agents/rules/headless-workers.md) -- Workers operate headlessly without prompting users mid-task; releases hand back on the task record and provide resumption prompts when interrupted. | instructions, structural, process | imperative, block, required gate | `.agents/rules/headless-workers.md:1-18`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/pull/SKILL.md:14-39` |

### 10. Outcome-Level Verification Checks (Fresh Agent Run against Baseline)

Per framework testing policy (`tests-verify-behaviour.md`), changes to instruction text owe no programmatic unit tests; instead, behavioral contracts are verified through a fresh agent execution comparing behavior against an un-modified baseline run:

- **VC-1 (Wrap-Up Posture Verification)**: Run a fresh agent tasked with a clean context reset using the revised `dump` skill. Verify that the agent executes file saving and handover reporting without emitting abort, panic, or error terminology in its turn output. Baseline comparison: un-modified skill emits abort/panic notices when invoked before full task completion.
- **VC-2 (Daily Note Consolidated Pointer Verification)**: Run a session that touches multiple project files and invokes `dump`. Verify that exactly one consolidated bullet per touched project is written into `## Today's work` in the daily note, following the format `- **<project>**: <state> -- Next: <pointer>`. Baseline comparison: un-modified skill writes no consolidated project updates to the daily note.
- **VC-3 (Retroactive Task Creation Verification)**: Run an ad-hoc session that modifies a repository source file without a prior task. Verify that `dump` mints a retroactive task recording the commit SHA and releases it as `done`. Verify that a pure routing/triage session creates no retroactive task. Baseline comparison: un-modified skill exits without creating a tracking task for unparented changes.
- **VC-4 (Durable Fact and PKB Repair Verification)**: In a session encountering a deliberate PKB contradiction, verify that `dump` invokes Pauli to resolve the contradiction on sight and offers 6-month durable facts as content. Baseline comparison: un-modified skill ignores PKB contradictions and leaves uncurated facts in transient logs.
- **VC-5 (Next-Step Discipline Verification)**: Run two test sessions: (a) a fully completed task with no dependents; verify `Next step` is `None` with zero invented tasks; (b) an interrupted session; verify `Next step` outputs a copy-pasteable 2-4 sentence resumption prompt. Baseline comparison: un-modified skill fabricates speculative next steps.
- **VC-6 (Session ID Verification)**: Execute `dump` and verify that the handover block header matches `## Handover: <agent> <session-id>` with the exact active session ID. Baseline comparison: un-modified skill prints placeholders or omits session ID.
