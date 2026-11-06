---
id: coordinator-failure-enforcement
title: User-Facing Coordinator Failure Enforcement Design
status: draft
type: spec
tags: [enforcement, coordinator, failure-classes, verification, premise-check, hooks, attention-protection]
---

# User-Facing Coordinator Failure Enforcement Design

This specification defines the architectural design, enforcement moves, and observable build criteria for five recurrent coordinator failure classes identified in system learning audits:

1. **Unbacked Behavioral Promises**: Promising future operational conduct in conversation reply text without a corresponding persistent write or control.
2. **Escalation of Settled Items**: Escalating items already decided by the user because incoming "needs user" labels are not evaluated against standing rulings.
3. **Orphaned Remediation Remainders**: Routing review and quality gaps by kind to graph curation alone, leaving the dispatch half of remediation unowned.
4. **Partition Widening and Unchecked Cards**: Broadening filtered user requests into full partitions and older schedule prompts, emitting multi-question cards with no outbound verification.
5. **Dropped Interrupted Turns on Restart**: Treating interrupted, uncompleted turns as finished when a coordinator or worker session restarts.

A rule defines an invariant obligation that agents must follow; a spec defines the intended runtime behavior and mechanisms of a subsystem. The substantive rules governing these five areas already exist in universal axioms and core project rules. These failures are breaches of existing rules in specific operational circumstances, not novel rule classes. This specification does not introduce new rules; it designs the genuinely new enforcement behaviors and mechanisms required to prevent and catch these breaches where baseline instructions have proven insufficient.

## User stories

### US-1: JIT Reminders and In-Turn Persistent Writes on Conduct Challenges

As the user, I want the coordinator's commitments regarding future operational conduct to be backed by in-turn persistent writes or citations to active persistent controls, so that commitments survive session restarts and I am never given unbacked assurances.

- **AC-1.1**: Given a user prompt challenging coordinator conduct or correcting operational behavior, when turn processing initiates, then JIT injection reminds the coordinator that behavioral assurances regarding future conduct require an in-turn persistent write or citation to an active persistent control.
- **AC-1.2**: Given a user correction or operational inquiry, when the coordinator replies with text stating a commitment or rule regarding future operational behavior, then either the session's contemporaneous execution records show a persistent write (instruction edit, rule addition, configuration update, or tracked task creation) executed within the same turn, or the reply explicitly cites an already-active persistent control governing that behavior.

### US-2: JIT Reminders and Autonomous Resolution Against Standing Rulings

As the user, I want incoming worker questions and approval requests tested against my standing rulings before reaching me, so that my attention is never spent re-deciding matters I have already settled while required approvals are preserved.

- **AC-2.1**: Given an incoming worker report or card proposal categorizing an item as requiring user approval or escalation, when verification evaluates the handback, then JIT injection prompts the evaluating agent to verify the item semantically against active standing rulings and merge policies.
- **AC-2.2**: Given an item governed by an active standing ruling, when the coordinator processes the handback, then if the ruling settles the requested decision within delegated authority without requiring further user input, the coordinator resolves the item autonomously and suppresses user escalation; if the ruling explicitly requires user approval or escalation for that class, the coordinator preserves the required approval.

### US-3: Closed-Loop Remediation Routing for Authorized Execution

As the user, I want review and workflow gaps whose execution is authorized to be dispatched to execution immediately after graph capture, while preserving the capture-only boundary for intake and reification requests, so that authorized remediation work does not stall as an unowned queued task.

- **AC-3.1**: Given a discovered deliverable gap or failing review requiring remediation, when the coordinator routes task creation to the graph custodian, then `premise-check` evaluates the custodian's handback against the graph-curation ask (`Answered:` and `Relay:` per `plugins/ida/skills/premise-check/references/checker-reason.md:24-27`), while the coordinator separately evaluates whether the parent turn holds an authorized execution obligation requiring downstream dispatch.
- **AC-3.2**: Given a graph custodian handback reporting that remediation tasks are queued and ready, when the parent turn's originating directive or workflow authorizes execution, then the graph handback passes truthfully on its scoped ask while the parent turn obligation remains open until the coordinator dispatches the queued tasks to the execution dispatcher and records dispatch confirmation within the same turn; conversely, when the originating request is capture-only (`/q` or `/reify` per `plugins/ida/agents/ida.md:32`), the turn completes upon graph capture without starting workers.

### US-4: Scoped Filter Briefs and Outbound Card Serialization

As the user, I want briefings on filtered subsets to remain scoped strictly to the requested criteria without enumerating or asking to re-decide excluded complement items, and I want question cards presented to me strictly serialized to one decision per message across all question-posting paths, so that my attention is protected from partition widening and multi-decision batches.

- **AC-4.1**: Given an invocation of a structured user question path (`AskUserQuestion` via `plugins/ida-telegram/hooks/ask-user-question.js` or direct MCP `ask_user` via `plugins/ida-telegram/src/mcp/server.ts`), when syntactic validation executes before the path's first posting side effect, then the call is blocked if the payload contains more than one decision question (`len(questions) > 1`).
- **AC-4.2**: Given a structured user question call on either path containing a single decision question (`len(questions) <= 1`), when syntactic validation executes before posting, then validation allows the call to proceed.
- **AC-4.3**: Given a user prompt requesting a filtered subset or category of items (e.g. ready or uncontroversial items), when the coordinator prepares the briefing or outbound report, then the output includes only items satisfying the requested filter and suppresses unprompted enumeration, diagnostic triage, or decision cards for the excluded complement set.
- **AC-4.4**: Given an active or recurring schedule prompt over a broad domain, when a subsequent user directive specifies a narrower filter, then the narrower filter supersedes the broader scope and prevents re-surfacing excluded complement items as pending decisions.

### US-5: Interrupted Turn Recovery Audit Across Restarts

As the user, I want coordinator and worker sessions that restart mid-turn to detect and resume incomplete turns, so that unhandled prompts and in-flight dispatches are not silently dropped.

- **AC-5.1**: Given a session restart following an interrupted turn that yielded no terminal assistant output, when session initialization executes, then session initialization inspects prior turn history and injects an interrupted turn recovery notice into the initial prompt.
- **AC-5.2**: Given an injected interrupted turn recovery notice, when the coordinator begins execution, then the coordinator resumes and completes the interrupted turn before processing new unrelated requests.

## Design

### Enforcement analysis and proportional moves

Enforcement moves follow the proportionality framework and controlled vocabulary defined in [`specs/enforcement/enforcement.md`](enforcement.md).

#### Class 1: Unbacked Behavioral Promises

- **Breached Rule and Location**: `Axiom: Categorical Imperative` (`plugins/rbg/skills/axioms/categorical-imperative.md:8-10`), `Axiom: Durable Capture` (`plugins/rbg/skills/axioms/durable-capture.md:8-10`), and `Decide or Escalate` (`specs/agents/ida-interaction-rules.md:76-77`, `plugins/ida/agents/ida.md:25-34`).
- **Circumstance of Failure**: When answering a user challenge or correcting operational behavior, the coordinator promises future operational conduct in conversation reply text (such as assuring that future items will be checked against rulings, or promising not to use specific tools) without either executing a corresponding in-turn persistent write (instruction edit, rule addition, configuration update, or tracked task creation) or citing an already-active persistent control. Outbound replies pass without verification because premise-checking gates arm only on incoming messages, allowing unbacked assurances to reach the user.
- **Proposed One-Step Move**: Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
- **New Behaviour Design**:
  - Operational Mechanism: A JIT prompt injection / warning on `UserPromptSubmit` (or turn intake) reminds the coordinator when answering user corrections or committing to future operational conduct that behavioral assurances require an in-turn persistent write (instruction edit, rule, configuration, or tracked task) or an explicit citation to an already-active persistent control.
  - Outbound Reply Trigger Analysis: Premise-checking gates today arm on incoming messages from peers or subagents (`UserPromptSubmit`) and foreground subagent dispatch returns (`PostToolUse`). Although a `Stop` hook surface is registered in `plugins/ida/manifest/hooks.json:90-98,226-235` and handled by `plugins/ida/hooks/handlers.py:1074-1078` (running `hearsay_handler` to block turn completion while an incoming report awaits a verdict), self-composed outbound conversational replies on un-armed turns (or after an incoming verdict is recorded) pass without outbound semantic inspection. Whether the existing `Stop` hook's firing timing and client capabilities across `claude` and `agy` can gate assistant prose before user-visible delivery is recorded in the Open questions section.

#### Class 2: Escalation of Settled Items

- **Breached Rule and Location**: `User Attention Protection` (`specs/enforcement/enforcement.md:59-65`, `plugins/ida/agents/ida.md:70-81`) and `Axiom: Exercise Authority` (`plugins/rbg/skills/axioms/exercise-authority.md:8-23`).
- **Circumstance of Failure**: When incoming worker reports or card proposals categorize an item as requiring user escalation (e.g., labeled "needs user"), the coordinator escalates the item directly without validating whether the decision is already settled within delegated authority by active standing rulings or merge policies. Premise-check verdicts treat user escalation as a safe default rather than testing whether the item can be resolved autonomously.
- **Proposed One-Step Move**: Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
- **New Behaviour Design**:
  - Operational Mechanism: JIT reminder injection (`hearsay.md` on incoming envelopes / `PostToolBatch`) reminds the coordinator when receiving reports or proposals marked "needs user" to check them against active standing rulings and merge policies before escalating to the user.
  - Autonomous Resolution Behavior: When an active standing ruling settles the requested decision within delegated authority without further user input, the coordinator resolves the item autonomously and suppresses user escalation; when the standing ruling or merge policy explicitly requires user approval for that class of item, the coordinator preserves the required approval and escalates with the required evidence and recommendation.

#### Class 3: Orphaned Remediation Remainders

- **Breached Rule and Location**: `Axiom: Do One Thing` (`plugins/rbg/skills/axioms/do-one-thing.md:8-21`), `Dropped Means Not Delivered` (`plugins/ida/agents/ida.md:26`), and `Separate Dispatch from Capture` (`plugins/ida/agents/ida.md:32`).
- **Circumstance of Failure**: Upon discovering review or quality gaps whose remediation execution is authorized, the coordinator routes task creation to the graph custodian alone. Once the custodian creates the tasks and hands back a valid report answering the graph-curation ask, the coordinator records `PASS` on the custodian's handback and terminates the turn without routing the queued tasks to the execution dispatcher, leaving authorized remediation tasks unowned.
- **Proposed One-Step Move**: Advance from Level 4 `structural` (`friction`) to Level 5 **`process` (`routing`)**.
- **New Behaviour Design**:
  - Operational Mechanism: Separate graph-handback evaluation from parent-turn obligation tracking while respecting the capture-only authority boundary (`plugins/ida/agents/ida.md:32`). Under `plugins/ida/skills/premise-check/references/checker-reason.md:24-27`, `Answered:` evaluates whether the custodian's report answered its scoped graph-curation ask, and `Relay:` records sentences sent upward; thus the custodian's graph-only handback passes truthfully when tasks are created. Separately, the coordinator tracks the parent turn's original obligation, next owner (`sara` / `/dispatch` when execution is authorized, or none when capture-only), and dispatch confirmation. When the originating directive or active workflow authorizes execution of the remediation, the parent obligation remains open after the custodian's handback passes until the coordinator dispatches the queued tasks to the execution dispatcher and records dispatch confirmation in the same turn. For capture-only `/q` or `/reify` requests, readiness never grants execution authority, and the obligation closes upon graph capture.

#### Class 4: Partition Widening and Unchecked Cards

- **Breached Rule and Location**: `User Attention Protection` (`specs/enforcement/enforcement.md:59-65`, `plugins/ida/agents/ida.md:70-81`) and `Axiom: Do One Thing` (`plugins/rbg/skills/axioms/do-one-thing.md:8-21`).
- **Circumstance of Failure**: When asked for a filtered subset (such as uncontroversial pull requests suitable for batch approval), the coordinator widens the brief into a full partition, explicitly demanding failure reasons and presenting decision cards for excluded complement items. Concurrently, older standing schedule prompts re-arm without accounting for narrower user directives. The coordinator aggregates these into multi-question cards emitted across structured question paths without pre-post validation.
- **Proposed One-Step Move**: Advance question serialization from Level 3 `JIT injection` to Level 4 **`structural` (`friction`)**; advance filter scoping from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
- **New Behaviour Design**:
  - Scoped filter briefs: Briefing instructions and JIT reminders on turn intake enforce strict filter scoping. When a user directive requests a subset, the coordinator restricts briefings strictly to matching items, suppressing unprompted complement set enumeration and diagnostic decision cards. Narrower conversational filters explicitly supersede broader standing schedule scopes.
  - Card serialization across both posting paths: Because `plugins/ida-telegram/hooks/ask-user-question.js:73-84` writes questions to the Unix socket broker during `PreToolUse` (before the underlying `AskUserQuestion` tool runs) and `plugins/ida-telegram/src/mcp/server.ts:334-385` exposes a direct MCP `ask_user` tool that posts cards without invoking `AskUserQuestion`, deterministic single-question validation (`len(questions) <= 1`) must execute before the first posting side effect on both paths -- inside `ask-user-question.js` prior to socket write (as well as `PreToolUse` validation) and at the entry of the MCP `ask_user` handler prior to calling `this.broker.askUser(...)`.
  - Outbound Card Semantic Verification vs. Prose Interception: Unlike ordinary assistant prose, structured question cards already expose their full payload at `PreToolUse` or MCP tool entry. Therefore, semantic inspection of card content does not require a new prose pre-output event; what remains unresolved is the checker handoff protocol, binding a checker verdict to the exact card payload, and ordering execution so verification precedes any hook or MCP posting side effect (recorded in the Open questions section).

#### Class 5: Dropped Interrupted Turns on Restart

- **Breached Rule and Location**: `Axiom: Full Observability` (`plugins/rbg/skills/axioms/full-observability.md:8-10`) and `Dropped Means Not Delivered` (`plugins/ida/agents/ida.md:26`).
- **Circumstance of Failure**: When coordinator or worker sessions restart mid-turn after receiving user prompts or launching dispatches, unhandled prompts are silently dropped, and the new session treats interrupted turns as finished without resuming in-flight work. The `SessionStart` hook exports session identity and environment variables but executes no audit of prior turn completion status.
- **Proposed One-Step Move**: Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
- **New Behaviour Design**:
  - Operational Mechanism: During `SessionStart` execution, a prior-turn audit inspects the immediate prior turn from the local transcript or trace store; if the preceding turn contains an incoming prompt or dispatch without a corresponding terminal output, it synthesizes an `UNFINISHED_TURN_RECOVERY` payload injected into the opening prompt to resume execution before processing new unrelated requests.

### Implementation contract and build criteria matrix

| Failure Class | Breached Existing Rule | Target Placement | Mechanism | Verification Surface | Build Acceptance Criterion |
| :- | :- | :- | :- | :- | :- |
| **1. Unbacked Promises** | `Categorical Imperative` (`categorical-imperative.md:8`), `Durable Capture` (`durable-capture.md:8`) | Level 3: `JIT injection` | JIT prompt injection / warning on `UserPromptSubmit` for conduct commitments | JIT injection audit / prompt & execution inspection | AC-1.1 & AC-1.2: JIT reminder injected on user conduct challenges; commitments backed by same-turn persistent write or citation to active control. |
| **2. Settled Items Escalated** | `User Attention Protection` (`enforcement.md:59`), `Exercise Authority` (`exercise-authority.md:8`) | Level 3: `JIT injection` | JIT reminder injection on incoming escalation reports (`hearsay.md`) | JIT injection audit / handback resolution inspection | AC-2.1 & AC-2.2: JIT reminder injected on escalation reports; rulings settling decisions within authority resolve autonomously while required approvals are preserved. |
| **3. Orphaned Remainder** | `Do One Thing` (`do-one-thing.md:8`), `Dropped Means Not Delivered` (`ida.md:26`), `Separate Dispatch from Capture` (`ida.md:32`) | Level 5: `process` (`routing`) | Separate parent-turn obligation tracking (`original obligation`, `next owner`, `dispatch confirmation`) alongside truthful graph-handback `Answered:` / `Relay:` evaluation | Handback & turn-completion routing audit | AC-3.1 & AC-3.2: Graph handback passes truthfully on graph ask; when execution is authorized, queued remediation routes to dispatcher in-turn; capture-only (`/q`, `/reify`) stops at capture. |
| **4. Partition Widening & Cards** | `User Attention Protection` (`enforcement.md:59`), `Do One Thing` (`do-one-thing.md:8`) | Level 4: `structural` (`friction`) | Pre-post check (`len(questions) <= 1`) in `ask-user-question.js` (before broker socket write) and MCP `ask_user` (`server.ts`, before `broker.askUser`), plus JIT filter scope reminder | `ask-user-question.js` & `server.ts` pre-post checks / briefing output inspection | AC-4.1 & AC-4.2: Multi-question cards blocked before first posting side effect on both `AskUserQuestion` hook and MCP `ask_user` paths. AC-4.3 & AC-4.4: Filtered briefs suppress complement enumeration. |
| **5. Interrupted Turns Dropped** | `Full Observability` (`full-observability.md:8`), `Dropped Means Not Delivered` (`ida.md:26`) | Level 3: `JIT injection` | `SessionStart` prior turn audit injects interrupted context | `SessionStart` hook handler | AC-5.1 & AC-5.2: Interrupted turns detected on restart; recovery block injected into first prompt. |

## Open questions

- **Outbound prose timing on `Stop` vs. structured card checker handoff**:
  1. _Ordinary assistant prose_: `Stop` is registered in `plugins/ida/manifest/hooks.json:90-98,226-235` and runs `hearsay_handler` in `plugins/ida/hooks/handlers.py:1074-1078`. Across `claude` and `agy`, does `Stop` fire early enough to withhold or revise self-composed assistant prose before user-visible streaming/delivery when no incoming report gate is armed, or is a dedicated pre-delivery / channel-send hook required?
  2. _Structured question cards_: Because `AskUserQuestion` and MCP `ask_user` already expose their full payload before posting, what checker handoff protocol should bind a semantic `premise-check` verdict to the exact card payload and guarantee verification precedes posting side effects in `plugins/ida-telegram/hooks/ask-user-question.js` and `plugins/ida-telegram/src/mcp/server.ts`?
- **Standing schedule yielding mechanics**: How should standing scheduled prompts (e.g. periodic background loop tasks) detect subsequent narrower conversational filters over the same target domain to yield autonomously without competing with active user directives?
- **Turn recovery boundaries across session aborts**: What heuristics or boundary conditions determine whether an interrupted turn should be resumed directly upon restart versus discarded when the preceding prompt was rendered obsolete by the restart cause or manual cancellation?
