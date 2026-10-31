---
id: coordinator-failure-enforcement
title: User-Facing Coordinator Failure Classes and Enforcement Moves
status: awaiting_review
type: spec
tags: [enforcement, coordinator, failure-classes, verification, premise-check, hooks, attention-protection]
---

# User-Facing Coordinator Failure Classes and Enforcement Moves

This specification defines the architectural design, enforcement moves, and observable build criteria for five recurrent failure classes of the user-facing coordinator identified in system learning audits:

1. **Unbacked Behavioral Promises**: Promising future operational conduct in conversation reply text without a corresponding persistent write or change.
2. **Escalation of Settled Items**: Escalating items already decided by the user because incoming "needs user" labels are not evaluated against standing rulings.
3. **Orphaned Remediation Remainders**: Routing review and quality gaps by kind to graph curation alone, leaving the dispatch half of remediation unowned.
4. **Partition Widening and Unchecked Cards**: Broadening filtered user requests into full partitions and older schedule prompts, emitting multi-question cards with no outbound verification.
5. **Dropped Interrupted Turns on Restart**: Treating interrupted, uncompleted turns as finished when a coordinator or worker session restarts.

For each failure class, this specification documents the touched rows of the enforcement map, the current placement in the enforcement pyramid, the empirical failure evidence, the proportional one-step enforcement move, and the observable build criteria that guarantee the defect no longer reaches the user.

## 1. User Stories

### US-1: Backed Behavioral Commitments

As the user, I want the coordinator's statements about future operational behavior to be strictly backed by persistent writes, so that commitments survive session restarts and I am never given unbacked assurances.

- **AC-1.1**: Given a user correction or operational inquiry, when the coordinator replies with text stating a commitment or rule regarding future operational behavior, then the session's contemporaneous execution records show a persistent write (instruction edit, rule addition, configuration update, or tracked task creation) executed within the same turn.
- **AC-1.2**: Given a user prompt challenging coordinator conduct or correcting operational behavior, when turn processing initiates, then JIT injection reminds the coordinator that behavioral assurances regarding future conduct require an in-turn persistent write or citation to an active persistent control.

### US-2: Autonomous Resolution Against Standing Rulings

As the user, I want incoming worker questions and approval requests tested against my standing rulings before reaching me, so that my attention is never spent re-deciding matters I have already settled.

- **AC-2.1**: Given an incoming worker report or card proposal categorizing an item as requiring user approval or escalation, when verification evaluates the handback, then JIT injection prompts the evaluating agent to verify the item semantically against active standing rulings and merge policies.
- **AC-2.2**: Given an item covered by an active standing ruling, when the coordinator processes the handback, then the coordinator resolves the item autonomously and suppresses user escalation.

### US-3: Closed-Loop Remediation Dispatch

As the user, I want review and workflow gaps identified by the coordinator to be dispatched to execution immediately, so that remediation work does not stall as an unowned queued task.

- **AC-3.1**: Given a discovered deliverable gap or failing review requiring remediation, when the coordinator routes task creation to the graph custodian, then the handback evaluation explicitly tests whether downstream dispatch obligations remain unfulfilled.
- **AC-3.2**: Given a handback reporting that remediation tasks are queued and ready for dispatch, when the coordinator completes handback evaluation under canonical `Answered:` and `Relay:` rules, then `Relay: none` is prohibited from closing the thread, and the coordinator routes the unowned remainder directly to the execution dispatcher within the same turn.

### US-4: Scoped Filter Briefs and Outbound Card Serialization

As the user, I want question cards presented to me strictly serialized to one decision per message, so that I am never asked to review multi-decision batches.

- **AC-4.1**: Given an invocation of the structured user question tool, when syntactic pre-tool validation executes, then the tool call is blocked if the payload contains more than one decision question (`len(questions) > 1`).
- **AC-4.2**: Given a structured user question tool call containing a single decision question (`len(questions) <= 1`), then the pre-tool validation allows the call to proceed.

### US-5: Interrupted Turn Recovery Across Restarts

As the user, I want coordinator and worker sessions that restart mid-turn to detect and resume incomplete turns, so that unhandled prompts and in-flight dispatches are not silently dropped.

- **AC-5.1**: Given a session restart following an interrupted turn that yielded no terminal assistant output, when session initialization executes, then session initialization inspects prior turn history and injects an interrupted turn recovery notice into the initial prompt.
- **AC-5.2**: Given an injected interrupted turn recovery notice, when the coordinator begins execution, then the coordinator resumes and completes the interrupted turn before processing new unrelated requests.

## 2. Enforcement Analysis and Proportional Moves

Enforcement moves follow the controlled vocabulary and proportionality framework defined in `specs/enforcement/enforcement.md`:
`doctrine only` → `instructions` (`suggestion` → `advisory` → `imperative` → `absolute`) → `JIT injection` → `structural` (`scoped` → `permissions` → `warning` → `friction` → `block` → `protection` → `isolation`) → `process` (`advisory check` → `routing` → `required gate`) → `post-hoc` (`reversibility` → `observability` → `proactive detection`).

### Class 1: Unbacked Behavioral Promises

- **Touched Enforcement Map Rows**:
  - `[Axiom: Categorical Imperative]` (`specs/ENFORCEMENT-MAP.md:17`): `instructions` (`imperative`), `process` (`required gate`).
  - `[Axiom: Durable Capture]` (`specs/ENFORCEMENT-MAP.md:24`): `instructions` (`imperative`), `JIT injection` (`warning`), `process` (`required gate`).
  - `[Shared Core: Decide or Escalate]` (`specs/ENFORCEMENT-MAP.md:60`): `instructions` (`imperative`).
  - `Verification of outbound replies against declared Relay lines` (`specs/ENFORCEMENT-MAP.md:119`): `process` (`required gate`), recorded as `[MAP DRIFT] not enforced`.
- **Current Placement**: Level 2 `instructions` (`imperative`) in axioms and core persona instructions, accompanied by an unenforced outbound reply verification specification (`[MAP DRIFT] not enforced`).
- **Failure Evidence**:
  - Issue #3302 (RCA): During session execution (2026-10-30), the coordinator answered a user challenge regarding repeated escalations with the promise: _"From here, every item gets checked against your rulings before it reaches you..."_. Contemporaneous trace records showed zero write or edit tool calls, zero git commits, and no dispatched tasks. An earlier promise in the same session (*"I'm asking in plain text from now on..."*) was similarly unbacked and broken within hours by invoking the structured question tool.
  - Issue #3303 (Verification Miss 1): Premise-checking gates arm exclusively on incoming messages from peers or subagents. Outbound self-composed coordinator replies pass without verification, allowing forward-looking commitments to reach the user without verifying supporting write operations.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
  - Operational Mechanism: A JIT prompt injection / warning on `UserPromptSubmit` (or turn intake) reminds the coordinator when answering user corrections or committing to future operational conduct that behavioral assurances require an in-turn persistent write (instruction edit, rule, configuration, or tracked task).
  - Outbound Reply Trigger Analysis: Premise-checking gates today arm exclusively on incoming messages from peers or subagents (`UserPromptSubmit`) and foreground subagent dispatch returns (`PostToolUse`). Self-composed outbound conversational replies pass without verification because no hook intercepts outgoing assistant messages to the user. Enforcing outbound reply verification under `premise-check` would require a new hook trigger (such as a pre-output or stop-turn inspection hook) that does not exist today; this missing trigger is recorded as an open question in § 4.

### Class 2: Escalation of Already-Ruled Items

- **Touched Enforcement Map Rows**:
  - `[Persona: Ida: Briefing Rules]` (`specs/ENFORCEMENT-MAP.md:53`): `instructions` (`imperative`).
  - `[User Attention Protection]` (`specs/ENFORCEMENT-MAP.md:54`): `instructions` (`imperative`).
  - `[Shared Core: Decide or Escalate]` (`specs/ENFORCEMENT-MAP.md:60`): `instructions` (`imperative`).
  - `Report format, contrast test, verdict tokens` (`specs/ENFORCEMENT-MAP.md:91`): `instructions` (`guidance`/`imperative`).
- **Current Placement**: Level 2 `instructions` (`imperative`) in briefing rules, user attention protection, and core decide-or-escalate instructions.
- **Failure Evidence**:
  - Issue #3303 (Verification Miss 2): Decision cards presented hotfix and configuration questions that were already settled by established merge policies and earlier peer handbacks in the same session. Premise-check verdicts marked routing to the user as "cheap to reverse" and low-stakes, treating user escalation as a safe default.
  - Issues #3308, #3309, #3310: An unconfirmed hotfix label was silenced during a merge pass without validating the label against user rulings, leading to unnecessary user inquiry.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
  - Operational Mechanism: JIT reminder injection (`hearsay.md` on incoming envelopes / `PostToolBatch`) reminds the coordinator when receiving reports or proposals marked "needs user" to check them against active standing rulings and merge policies before escalating to the user. This increments friction without prematurely jumping to a required gate.

### Class 3: Orphaned Remediation Remainders

- **Touched Enforcement Map Rows**:
  - `[Axiom: Do One Thing]` (`specs/ENFORCEMENT-MAP.md:23`): `instructions` (`imperative`), `structural` (`scoped`), `process` (`required gate`).
  - `Report format, contrast test, verdict tokens` (`specs/ENFORCEMENT-MAP.md:91`): `instructions` (`guidance`/`imperative`).
  - `Gate arms only when a report or direction arrives` (`specs/ENFORCEMENT-MAP.md:106`): `structural` (`friction`).
- **Current Placement**: Level 4 `structural` (`friction`) (hearsay gate arms when a report arrives) alongside Level 2 `instructions` (`imperative`).
- **Failure Evidence**:
  - Issue #3304 (RCA): Upon discovering unreviewed pull requests, the coordinator routed the gap to the graph custodian alone. The custodian queued the review tasks and reported back: _"build QAs are queued and only need dispatching"_. The thread terminated because no carrier routed the remainder to the dispatcher, leaving tasks queued indefinitely until user intervention.
  - Issue #3305 (Verification Miss): Premise-check judged the custodian's handback solely against the partial ask sent to it, recording `Answered` and `Relay: none`. The seven keyed lines contained no check evaluating what the report left undone or identifying who owned the remainder.
- **Proposed One-Step Move**:
  - Advance from Level 4 `structural` (`friction`) to Level 5 **`process` (`routing`)**.
  - Operational Mechanism: Enforce complete obligation evaluation across the canonical `Answered:` and `Relay:` lines in `premise-check`. When a handback report indicates that downstream actions remain necessary (e.g., tasks queued awaiting execution), the obligation cannot be marked answered in full, and `Relay: none` is prohibited from closing the thread. The evaluating agent routes the unowned remainder by dispatching the execution message to the dispatcher before turn completion can succeed, without escalating to an unyielding required gate.

### Class 4: Partition Widening and Unchecked Cards

- **Touched Enforcement Map Rows**:
  - `[Persona: Ida: Briefing Rules]` (`specs/ENFORCEMENT-MAP.md:53`): `instructions` (`imperative`).
  - `[User Attention Protection]` (`specs/ENFORCEMENT-MAP.md:54`): `instructions` (`imperative`).
  - `Prompt hydration delivery channel` (`specs/enforcement/enforcement.md:66`): `JIT injection`.
- **Current Placement**: Level 3 `JIT injection` (prompt hydration across incoming messages) alongside Level 2 `instructions` (`imperative`).
- **Failure Evidence**:
  - Issue #3318 (RCA): A user request for uncontroversial pull requests suitable for batch approval was briefed by the coordinator as a full partition, explicitly demanding failure reasons for all excluded items. Concurrently, an older standing loop prompt re-armed after restart without accounting for the user's narrower request. The coordinator combined both into a multi-question card presenting excluded items as separate decisions.
  - Issue #3319 (Verification Miss): Premise-check evaluated materiality against what a reader might do rather than what the user asked, approving inclusion of the complement set. The outgoing decision card was emitted four seconds after the verdict without undergoing any outbound check.
- **Proposed One-Step Move**:
  - Advance from Level 3 `JIT injection` to Level 4 **`structural` (`friction`)**.
  - Operational Mechanism: A single mechanism--a deterministic pre-tool hook on `AskUserQuestion`--inspects parameter structure and blocks calls where `len(questions) > 1`, enforcing single-decision serialization by construction without NLP.
  - Outbound Card Trigger Analysis: Validating outbound card options semantically under premise-check prior to user delivery would require an outbound inspection trigger; because no pre-output hook exists today, card serialization is enforced structurally via the pre-tool hook on `AskUserQuestion`, while outbound reply triggers remain an open question recorded in § 4.

### Class 5: Dropped Interrupted Turns on Restart

- **Touched Enforcement Map Rows**:
  - `[Axiom: Full Observability]` (`specs/ENFORCEMENT-MAP.md:30`): `instructions` (`imperative`), `structural` (`protection`), `process` (`required gate`), `post-hoc` (`observability`).
  - `[Dropped Means Not Delivered]` (`specs/ENFORCEMENT-MAP.md:71`): `instructions` (`imperative`).
- **Current Placement**: Level 2 `instructions` (`imperative`) in persona and dropped-means-not-delivered rules.
- **Failure Evidence**:
  - Session Execution Record (2026-10-30): Trace spans show instances where turns received user prompts or launched dispatches, experienced session restarts, and recorded `null` assistant output. The coordinator confessed in active session cards that it repeatedly treated unfinished turns as finished upon restart, dropping user instructions until re-prompted.
  - Hook Architecture: The `SessionStart` hook exports session identity and environment variables but executes no audit of the prior turn's completion status.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` (`imperative`) to Level 3 **`JIT injection`**.
  - Operational Mechanism: During `SessionStart` execution, a proposed prior-turn audit inspects the immediate prior turn from the local transcript or Phoenix trace store; if the preceding turn contains an incoming prompt or dispatch without a corresponding terminal output, it synthesizes an `UNFINISHED_TURN_RECOVERY` payload injected into the opening prompt to resume execution.

## 3. Implementation Contract and Build Criteria Matrix

| Failure Class | Current Placement | Target Placement | Mechanism | Verification Surface | Build Acceptance Criterion |
| :- | :- | :- | :- | :- | :- |
| **1. Unbacked Promises** | Level 2: `instructions` (`imperative`) | Level 3: `JIT injection` | JIT prompt injection / warning on `UserPromptSubmit` for conduct commitments | JIT injection audit / prompt inspection | AC-1.1 & AC-1.2: JIT reminder injected on user conduct challenges; commitments unbacked by persistent writes flagged. |
| **2. Settled Items Escalated** | Level 2: `instructions` (`imperative`) | Level 3: `JIT injection` | JIT reminder injection on incoming escalation reports (`hearsay.md`) | JIT injection audit / prompt inspection | AC-2.1 & AC-2.2: JIT reminder injected on incoming escalation reports, prompting autonomous resolution against standing rulings. |
| **3. Orphaned Remainder** | Level 4: `structural` (`friction`) | Level 5: `process` (`routing`) | Canonical `Answered:` & `Relay:` obligation routing prohibits thread closure on unowned tasks | `premise-check` handback evaluation | AC-3.1 & AC-3.2: Handbacks stating queued tasks route remainder to dispatcher to close thread. |
| **4. Partition Widening & Cards** | Level 3: `JIT injection` | Level 4: `structural` (`friction`) | Pre-tool check on `AskUserQuestion` (`len(questions) <= 1`) | PreToolUse hook (`len <= 1`) | AC-4.1 & AC-4.2: Multi-question cards blocked structurally by pre-tool hook. |
| **5. Interrupted Turns Dropped** | Level 2: `instructions` (`imperative`) | Level 3: `JIT injection` | `SessionStart` prior turn audit injects interrupted context | `SessionStart` hook handler | AC-5.1 & AC-5.2: Interrupted turns detected on restart; recovery block injected into first prompt. |

## 4. Open Questions

- **Outbound reply verification trigger**: Premise-checking gates today arm exclusively on incoming messages (`UserPromptSubmit`) and foreground subagent dispatch returns (`PostToolUse`). What hook or lifecycle event should trigger premise-check on outbound conversational replies to the user before transmission, given that no pre-output or stop-turn hook exists in the framework today to intercept self-composed coordinator messages?
- **Standing schedule yielding mechanics**: How should standing scheduled prompts (e.g. periodic background loop tasks) detect subsequent narrower conversational filters over the same target domain to yield autonomously without competing with active user directives?
- **Turn recovery boundaries across session aborts**: What heuristics or boundary conditions determine whether an interrupted turn should be resumed directly upon restart versus discarded when the preceding prompt was rendered obsolete by the restart cause or manual cancellation?
