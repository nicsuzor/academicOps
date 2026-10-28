---
title: Fault Reporting via /learn and User-Authority Boundaries for Task Creation
status: ready
type: spec
tags: [ida, learn, authority, fault-reporting, task-creation, enforcement]
---

# Fault Reporting via /learn and User-Authority Boundaries for Task Creation

This specification defines the canonical protocol for how the conversational front agent (`ida`) handles operational faults and restricts task creation to explicit user authority. It ensures that every infrastructure, tool, or capability failure encountered by Ida is diagnosed and reported through the systemic learning pipeline (`/learn`), and eliminates autonomous, un-authorized task creation--including self-directed fixes.

## User stories

### US-1 Universal fault reporting through /learn

As an agent encountering an operational error or capability degradation, I want unambiguous instructions to report the failure through `/learn`, so that the systemic cause is diagnosed and filed in the responsible repository without polluting the local task graph or attempting un-authorized fixes.

- **AC-1.1** Given an inbound channel event carrying an error attribute (such as `transcript_error` or `*_error`) or a tool returning a degraded capability flag (such as `voiceError` or `voiceSent: false`), when Ida handles the event, then Ida reports the failure verbatim to the user on the channel and dispatches `/learn` to diagnose the root cause from execution records.
- **AC-1.2** Given an unexpected tool failure, hook rejection, execution fault, or broken external dependency during a session, when Ida handles the error, then Ida halts without ad-hoc workarounds and dispatches `/learn` to record the defect in the owning repository.
- **AC-1.3** Given any fault or capability failure, when Ida processes the failure, then Ida never creates a local backlog task or attempts an ad-hoc fix on her own initiative.

### US-2 Strict user-authority boundaries for task creation

As the user, I want Ida to create tasks only when I have explicitly authorized them, so that the knowledge base and execution pipelines are never cluttered with self-directed fixes, speculative work, or un-directed background tasks.

- **AC-2.1** Given an operational defect, friction point, or potential improvement observed by Ida without an explicit user directive to fix it, when Ida responds, then Ida reports the findings or facts to the user (and dispatches `/learn` if it is a framework or tool fault) and creates no task on the graph.
- **AC-2.2** Given an open conversation or returned worker report, when Ida evaluates next steps, then Ida never decides on a fix on her own or mints a task to implement a self-chosen solution.
- **AC-2.3** Given an explicit directive from the user to track or execute work, when Ida captures or reifies tasks via `/q` or `/reify`, then every created task derives strictly from the user's authorizing words, citing the authorising request.

## Instruction Surfaces and Current Enforcement-Map Placement

The following inventory identifies every instruction surface governing how Ida handles faults and creates tasks, along with its current placement in `specs/ENFORCEMENT-MAP.md`:

| Area | Surface | Scope & Rule Intent | Current Enforcement-Map Row & Mechanism |
| :- | :- | :- | :- |
| **Fault Handling** | `plugins/ida/agents/ida.md:60-65` (`Inbound capability and infrastructure failures`) | Instructs Ida to treat inbound errors as infrastructure halts, report verbatim to the user, and "file an escalation issue or task for the broken capability." | `specs/ENFORCEMENT-MAP.md:31` under `[Axiom: Halt on Failure]` (`instructions, JIT injection, structural, process` \| `absolute, warning, block, required gate`). Contradicts centralized fault reporting by directing task creation for broken capabilities. |
| **Fault Handling** | `plugins/ida/agents/ida.md:26` (`Ask routing`) | Directs diagnosis, non-PKB lookups, and questions to internal subagents rather than direct execution in main context. | `specs/ENFORCEMENT-MAP.md:20, 23` under `[Axiom: Costly Ops Approval]` & `[Axiom: Do One Thing]` (`instructions, structural, process` \| `imperative, scoped, required gate`). |
| **Fault Handling** | `plugins/ida/CORE.md:60-65` (`Decide or Escalate`) | Defines when agents autonomously decide, defer via probes, or surface/escalate to the user. | `unenforced` (no row in `specs/ENFORCEMENT-MAP.md` links general escalation to Ida's fault handling). |
| **Fault Handling** | `plugins/ida/skills/learn/SKILL.md:1-50` | Defines root-cause analysis from session traces and filing issues/evidence bumps in owning repositories; explicitly prohibits proposing fixes or opening implementation tasks. | `specs/ENFORCEMENT-MAP.md:17, 21, 26, 32` under `[Axiom: Categorical Imperative]`, `[Axiom: Data Boundaries]`, `[Axiom: Explanations Are Not Reasons]`, and `[Axiom: Honest Epistemics]`. Universal routing of Ida faults to `/learn` is `unenforced` (no row binds Ida to invoke `/learn` on faults). |
| **Fault Handling** | `plugins/ida/skills/up/SKILL.md:1-4` | Clarifies that `/up` climbs to the class of user corrections, whereas filing framework bugs from session logs routes to `/learn`. | `specs/ENFORCEMENT-MAP.md:17` under `[Axiom: Categorical Imperative]`. |
| **Task Creation** | `plugins/ida/agents/ida.md:26, 28` (`Ask routing`, `Separate dispatch from capture`) | Limits task dispatch pipeline to real code changes; separates capture (`/q`, `/reify`) from execution (`dispatch`). | `specs/ENFORCEMENT-MAP.md:23` under `[Axiom: Do One Thing]`. |
| **Task Creation** | `plugins/ida/agents/ida.md:58` (`Compliance consequences`) | Instructs Ida to file compliance consequences (outside-work approvals, disclosures) as background tasks when the user is deciding whether to take on work. | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`). |
| **Task Creation** | `plugins/ida/agents/ida.md:63` (`Inbound capability and infrastructure failures`) | Directs Ida to "file an escalation issue or task for the broken capability." | `specs/ENFORCEMENT-MAP.md:31` under `[Axiom: Halt on Failure]`. Erroneously authorizes un-prompted task creation for errors. |
| **Task Creation** | `plugins/ida/CORE.md:7-14` (`Agent Roles`) | Defines Ida as capturing ideas and coordinating execution, Pauli as sole writer to the PKB graph, and Sara as code change dispatcher. | `specs/ENFORCEMENT-MAP.md:78` (role boundary); authority boundaries for task creation are `unenforced`. |
| **Task Creation** | `plugins/ida/skills/q/SKILL.md:8-10, 48-60` | Captures natural-language asks from the user on the strategic graph; requires linking tasks to authorising user messages. | `specs/ENFORCEMENT-MAP.md:24, 34` under `[Axiom: Durable Capture]` and `[Axiom: Proportionate]`. |
| **Task Creation** | `plugins/ida/skills/reify/SKILL.md:8-10, 34-36, 52-54` | Composes dispatchable tasks from objectives; strictly requires `## Ask` to record verbatim authorising user words. | `specs/ENFORCEMENT-MAP.md:34` under `[Axiom: Proportionate]`. |
| **Task Creation** | `plugins/ida/skills/workflow-library/workflows/wf-daily.md:49-55` | Elevates verbatim user requests and high-signal handwritten prompts from daily traces into tracking tasks. | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`). |

## General Rule Formulations Over Whole Classes

Both rules are formulated over their full class of application rather than narrow situational instances:

### Rule 1: Universal Fault Reporting via /learn

- **Class Definition**: Any fault, error, degraded capability flag, tool execution failure, hook block, schema mismatch, or infrastructure breakdown encountered during Ida's operation belongs to the class of framework and tooling defects.
- **Operative Obligation**: Whenever Ida encounters any fault within this class:
  1. Ida reports the verbatim failure to the user on the active channel (if operating in an interactive session).
  2. Ida reports the defect by invoking `/learn` (dispatched to `pauli`) to diagnose the systemic root cause from session telemetry spans and file an anonymised issue or evidence-bump comment in the owning repository.
  3. Ida never creates a task on the task graph, never opens an ad-hoc bugfix task, and never attempts a self-directed workaround.

### Rule 2: Prohibition of Task Creation Outside User Authority

- **Class Definition**: Any task creation, task queueing, task reification, or task mutation on the knowledge base graph that is not directly authorized by an explicit directive or ask from the user belongs to the class of _ultra vires_ actions.
- **Operative Obligation**: Ida may never create, queue, or reify a task on the task graph unless authorized by explicit direction from the user.
  - This strictly prohibits Ida from deciding to fix things on her own, inventing proactive refactoring tasks, converting internal observations into backlog items, or filing tasks for encountered faults.
  - Encountered issues, compliance considerations, or potential improvements are reported as verifiable facts to the user or routed to `/learn`; tasks are created only when the user explicitly directs that a task be captured or created.

## Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, both rules were evaluated through the enforcement pyramid to select the least-invasive mechanism that fits the risk:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Rejected.** Universal axioms (`Do One Thing`, `Closure`, `Categorical Imperative`, `Halt on Failure`) declare the general principle, but failed to prevent agents from creating tasks on errors. In fact, `ida.md:63` explicitly instructed agents to "file an escalation issue or task", demonstrating that doctrine alone is insufficient when instructions conflict. |
| 2 | `instructions` (`imperative` / `absolute`) | **Adopted.** Adding explicit imperative instructions to `plugins/ida/agents/ida.md` (under `## Governing Rules` and replacing the flawed clause in `### Inbound capability and infrastructure failures`) directly eliminates the contradictory command and provides clear, actionable behavioral rules during deliberation at zero token overhead for unaffected turns. |
| 3 | `JIT injection` | **Evaluated.** Injecting JIT reminders on every prompt submit or tool error was considered. However, JIT injection adds recurring token costs and attention clutter. Because the failure was caused by contradictory instruction text in `ida.md`, correcting the instructions at Level 2 is the proportional first step. |
| 4 | `structural` | **Evaluated.** Programmatic gating of task-creation tools (`pkb_create_task`, `pkb_claim_task`) to require user-attestation payloads was considered. Structural prevention is disproportionately heavy at this stage; instructions must be tried and proven ineffective before escalating to mechanical blocks. |
| 5 | `process` | **Evaluated.** Review lenses (`wf-rbg`) already check compliance on PRs. However, in-session task creation does not pass through PR review, making post-hoc review ineffective for interactive task pollution. |

### Evidence for the Move

1. **Defect in Existing Instructions**: `plugins/ida/agents/ida.md:63` specifically told Ida: "file an escalation issue or task for the broken capability." This directly induced Ida to create unauthorized tasks on tool errors instead of using `/learn`.
2. **Centralized Learning Protocol**: `specs/enforcement/enforcement.md:126-130` establishes `/learn` as the singular path for framework learning and friction routing: "Two flows, deliberately separated as witness and judge... 1. Diagnose and route (/learn)... It proposes no fix to anything governing future sessions; writing a standing rule needs the user to have asked."
3. **Prevention of Task Graph Pollution**: Multi-session analysis reveals that agents regularly overreach by attempting autonomous self-repairs and minting un-directed tasks. Explicitly forbidding task creation without user authority enforces `Axiom: Do One Thing` ("Find related issues -> Report them, don't fix them") at the exact operational boundary where Ida deliberates.

## Enforcement Map Extract (for Downstream Implementation)

The following rows will be incorporated into `specs/ENFORCEMENT-MAP.md` during downstream implementation when instruction text is merged:

| Rule / nudge | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Persona: Ida: Faults Reported by /learn](../plugins/ida/agents/ida.md) -- All operational faults, capability failures, and tool errors must be reported via `/learn`; creating tasks or fixing faults autonomously is prohibited. | instructions | imperative | `plugins/ida/agents/ida.md`: Instructs Ida to report verbatim errors to the user and dispatch `/learn` on all faults, prohibiting creating tasks or attempting self-directed fixes. |
| [Persona: Ida: Task Creation Bounded by User Authority](../plugins/ida/agents/ida.md) -- Ida may never create tasks outside the authority given by the user, including deciding to fix things on her own. | instructions | absolute | `plugins/ida/agents/ida.md`: Prohibits Ida from creating, queueing, or reifying any task without explicit user directive, including self-directed fixes or proactive backlog creation. |

## Outcome-Level Build Criteria (for Downstream Implementation)

The downstream implementation task must satisfy the following verifiable criteria, stated as what Ida does:

- [x] **BC-1 (Fault Reporting via /learn)**: When encountering any inbound error attribute, tool degradation, hook rejection, or execution fault, Ida reports the verbatim error to the user on the channel and invokes `/learn` to diagnose the failure from session execution records.
  - Evidence: `plugins/ida/agents/ida.md:27,64-67` mandates reporting errors verbatim to the user and invoking `/learn` to diagnose systemic root causes; `plugins/ida/hooks/messages/degraded_capability.md:4` and `plugins/ida/hooks/handlers.py:1031` instruct reporting verbatim and invoking `/learn`.
- [x] **BC-2 (No Task Creation for Faults)**: When encountering any fault or broken capability, Ida never creates, queues, or delegates a task on the task graph to fix or track the broken capability.
  - Evidence: `plugins/ida/agents/ida.md:26,65` explicitly prohibits task creation for faults: "Creating tasks or attempting self-directed fixes for faults or broken capabilities is strictly prohibited" and "never create a task on the task graph."
- [x] **BC-3 (No Self-Directed Fix Tasks)**: When identifying a problem, friction point, or potential improvement on her own, Ida reports the observation as verifiable facts to the user and never creates a task to implement a fix unless the user explicitly directs it.
  - Evidence: `plugins/ida/agents/ida.md:26,66` forbids deciding to fix things on her own, inventing proactive tasks, or turning internal observations into backlog items; `plugins/ida/skills/learn/SKILL.md:39-41` prohibits proposing fixes or opening implementation tasks.
- [x] **BC-4 (Task Creation Strictly Authorized by User)**: When creating, queueing, or reifying tasks via `/q` or `/reify`, Ida creates tasks only for work explicitly directed by the user, linking each task to the user's authorizing request.
  - Evidence: `plugins/ida/agents/ida.md:26` bounds task creation strictly to user authority: "Ida may never create, queue, or reify a task on the task graph unless authorized by explicit direction from the user... tasks are created only when the user explicitly directs that a task be captured or created"; `plugins/ida/skills/q/SKILL.md:52-56` and `plugins/ida/skills/reify/SKILL.md:52-54` preserve authorising asks with message IDs.
- [x] **BC-5 (Instruction Cleanliness)**: `plugins/ida/agents/ida.md` has the phrase "or task" in `Report verbatim and escalate` (line 63) removed, aligns background compliance task handling (line 58) with explicit user authorization, incorporates the explicit obligation to report all faults via `/learn`, and includes the governing rule forbidding task creation outside user authority.
  - Evidence: `plugins/ida/agents/ida.md:26-27` adds governing rules; line 60 updates compliance handling to require explicit user authorization; line 65 removes "or task" and specifies `/learn` escalation; line 66 prohibits self-directed fixes.
