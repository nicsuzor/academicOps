---
id: coordinator-failure-enforcement
title: User-Facing Coordinator Failure Classes and Enforcement Moves
status: ready
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
- **AC-1.2**: Given a drafted reply containing a commitment regarding future behavior without an accompanying persistent write or citation of an active persistent control, when the coordinator attempts to output the text or terminate the turn, then execution friction halts the action and requires either persisting the mechanism or retracting the unbacked assurance.

### US-2: Autonomous Resolution Against Standing Rulings

As the user, I want incoming worker questions and approval requests tested against my standing rulings before reaching me, so that my attention is never spent re-deciding matters I have already settled.

- **AC-2.1**: Given an incoming worker report or card proposal categorizing an item as requiring user approval or escalation, when verification evaluates the handback, then the evaluation tests the item against active standing rulings and merge policies.
- **AC-2.2**: Given an item covered by an active standing ruling, when the coordinator processes the item, then the coordinator applies the ruling autonomously and suppresses user escalation.
- **AC-2.3**: Given a question or approval card presented to the user, then verification records an explicit check confirming the absence of applicable standing rulings before the card is emitted.

### US-3: Closed-Loop Remediation Dispatch

As the user, I want review and workflow gaps identified by the coordinator to be dispatched to execution immediately, so that remediation work does not stall as an unowned queued task.

- **AC-3.1**: Given a discovered deliverable gap or failing review requiring remediation, when the coordinator routes task creation to the graph custodian, then the handback evaluation explicitly tests for operational remainders.
- **AC-3.2**: Given a handback reporting that remediation tasks are queued and ready for dispatch, when the coordinator completes handback evaluation, then the evaluation records an unowned remainder and automatically initiates dispatch to the execution dispatcher within the same turn.
- **AC-3.3**: Given an identified quality or review gap, then the coordinator emits no status to the user indicating remediation is underway without a verified dispatch invocation recorded in the trace.

### US-4: Scoped Filter Briefs and Outbound Card Verification

As the user, I want filtered requests briefed strictly to the requested scope and outbound question cards verified against checked relay lines, so that I am never asked to review excluded items or multi-decision batches.

- **AC-4.1**: Given a user request for a filtered subset of items, when the coordinator briefs a subagent, then the brief specifies only the filtering criteria and contains no instructions requesting categorization or status of items outside the filter.
- **AC-4.2**: Given a standing scheduled prompt, when the user provides a subsequent narrower directive over the same domain, then the standing schedule yields to the narrower user directive and does not generate competing approval items.
- **AC-4.3**: Given an invocation of the structured user question tool, when outbound validation executes, then the tool call is blocked unless the card contains at most one decision question and every proposed option resolves directly to a verified relay line answering the user's latest conversation directive.

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
- **Current Placement**: Level 2 `instructions` (`imperative`) in axioms and core persona instructions, accompanied by an unenforced outbound reply verification specification.
- **Failure Evidence**:
  - Issue #3302 (RCA): During session execution (2026-10-30), the coordinator answered a user challenge regarding repeated escalations with the promise: _"From here, every item gets checked against your rulings before it reaches you..."_. Contemporaneous trace records showed zero write or edit tool calls, zero git commits, and no dispatched tasks. An earlier promise in the same session (*"I'm asking in plain text from now on..."*) was similarly unbacked and broken within hours by invoking the structured question tool.
  - Issue #3303 (Verification Miss 1): Premise-checking gates arm exclusively on incoming messages from peers or subagents. Outbound self-composed coordinator replies pass without verification, allowing forward-looking commitments to reach the user without verifying supporting write operations.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` to Level 4 **`structural` (`friction`)** via outbound turn verification.
  - Operational Mechanism: A pre-output / turn termination hook evaluates outbound conversational replies. When a reply contains forward-looking behavioral commitments (*"from now on"*, _"from here"_, _"in future"_, _"I will ensure"_), the hook inspects the turn's tool execution trace. If the turn contains no persistent write operation (file edit, rule creation, configuration write, or tracking task creation) and cites no active persistent control, turn completion is refused with a friction notice directing the agent to either persist the control or strike the unbacked commitment.

### Class 2: Escalation of Already-Ruled Items

- **Touched Enforcement Map Rows**:
  - `[Persona: Ida: Briefing Rules]` (`specs/ENFORCEMENT-MAP.md:53`): `instructions` (`imperative`).
  - `[User Attention Protection]` (`specs/ENFORCEMENT-MAP.md:54`): `instructions` (`imperative`).
  - `[Shared Core: Decide or Escalate]` (`specs/ENFORCEMENT-MAP.md:60`): `instructions` (`imperative`).
  - `Report format, contrast test, verdict tokens` (`specs/ENFORCEMENT-MAP.md:91`): `instructions` (`guidance`/`imperative`).
- **Current Placement**: Level 2 `instructions` (`imperative`).
- **Failure Evidence**:
  - Issue #3303 (Verification Miss 2): Decision cards presented hotfix and configuration questions that were already settled by established merge policies and earlier peer handbacks in the same session. Premise-check verdicts marked routing to the user as "cheap to reverse" and low-stakes, treating user escalation as a safe default.
  - Issues #3308, #3309, #3310: An unconfirmed hotfix label was silenced during a merge pass without validating the label against user rulings, leading to unnecessary user inquiry.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` to Level 5 **`process` (`required gate`)** within handback verification and card composition.
  - Operational Mechanism: Classify user escalation as high-stakes under User Attention Protection principles (`specs/enforcement/enforcement.md`), eliminating the presumption of cheap reversibility. In `premise-check`, the `Sufficient:` evaluation for any claim routing a decision to the user must execute a mandatory `standing-rulings` check, verifying that the question is not settled by existing repository rules, merge policies, or recorded directives. If settled, `PASS` is refused, and the agent must resolve the item autonomously.

### Class 3: Orphaned Remediation Remainders

- **Touched Enforcement Map Rows**:
  - `[Axiom: Do One Thing]` (`specs/ENFORCEMENT-MAP.md:23`): `instructions` (`imperative`), `structural` (`scoped`), `process` (`required gate`).
  - `Report format, contrast test, verdict tokens` (`specs/ENFORCEMENT-MAP.md:91`): `instructions` (`guidance`/`imperative`).
  - `Gate arms only when a report or direction arrives` (`specs/ENFORCEMENT-MAP.md:106`): `structural` (`friction`).
- **Current Placement**: Level 2 `instructions` (`imperative`) and Level 4 `structural` (`friction`), with gate arming bound to message receipt rather than open obligations.
- **Failure Evidence**:
  - Issue #3304 (RCA): Upon discovering unreviewed pull requests, the coordinator routed the gap to the graph custodian alone. The custodian queued the review tasks and reported back: _"build QAs are queued and only need dispatching"_. The thread terminated because no carrier routed the remainder to the dispatcher, leaving tasks queued indefinitely until user intervention.
  - Issue #3305 (Verification Miss): Premise-check judged the custodian's handback solely against the partial ask sent to it, recording `Answered` and `Relay: none`. The seven keyed lines contained no check evaluating what the report left undone or identifying who owned the remainder.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` to Level 5 **`process` (`routing` / `required gate`)** in handback verification.
  - Operational Mechanism: Extend handback evaluation in `premise-check` with an explicit `Remainder:` check. When a handback report indicates that downstream actions remain necessary (e.g., tasks queued awaiting execution), `Relay: none` is prohibited from closing the thread. The gate requires an immediate chained dispatch message to the execution dispatcher before turn completion can succeed.

### Class 4: Partition Widening and Unchecked Cards

- **Touched Enforcement Map Rows**:
  - `[Persona: Ida: Briefing Rules]` (`specs/ENFORCEMENT-MAP.md:53`): `instructions` (`imperative`).
  - `[User Attention Protection]` (`specs/ENFORCEMENT-MAP.md:54`): `instructions` (`imperative`).
  - `Verification of outbound replies against declared Relay lines` (`specs/ENFORCEMENT-MAP.md:119`): `process` (`required gate`), recorded as `[MAP DRIFT] not enforced`.
- **Current Placement**: Level 2 `instructions` (`imperative`), with outbound reply and card verification remaining unenforced.
- **Failure Evidence**:
  - Issue #3318 (RCA): A user request for uncontroversial pull requests suitable for batch approval was briefed by the coordinator as a full partition, explicitly demanding failure reasons for all excluded items. Concurrently, an older standing loop prompt re-armed after restart without accounting for the user's narrower request. The coordinator combined both into a multi-question card presenting excluded items as separate decisions.
  - Issue #3319 (Verification Miss): Premise-check evaluated materiality against what a reader might do rather than what the user asked, approving inclusion of the complement set. The outgoing decision card was emitted four seconds after the verdict without undergoing any outbound check.
- **Proposed One-Step Move**:
  - Advance from Level 2 `instructions` to Level 4 **`structural` (`friction`)** on question tool calls.
  - Operational Mechanism: Enforce pre-tool validation on the structured question tool (`AskUserQuestion`). The pre-tool hook verifies that:
    1. The payload contains at most one decision question, strictly enforcing single-decision serialization.
    2. Every question and option text maps directly to a verified `Relay:` line of a current turn verdict answering the user's latest active directive.
    3. Standing scheduled prompts yield to subsequent conversational filters over the same target domain.

### Class 5: Dropped Interrupted Turns on Restart

- **Touched Enforcement Map Rows**:
  - `[Axiom: Full Observability]` (`specs/ENFORCEMENT-MAP.md:30`): `instructions` (`imperative`), `structural` (`protection`), `process` (`required gate`), `post-hoc` (`observability`).
  - `[Dropped Means Not Delivered]` (`specs/ENFORCEMENT-MAP.md:71`): `instructions` (`imperative`).
  - Current placement: Level 1 `doctrine only` / Level 2 `instructions` (`imperative`). No active enforcement map row governs in-session turn recovery on restart.
- **Failure Evidence**:
  - Session Execution Record (`cee1226c-192b-5538-b797-17be9a4f5dda`): Trace spans show instances where turns received user prompts or launched dispatches, experienced session restarts, and recorded `null` assistant output. The coordinator confessed in active session cards that it repeatedly treated unfinished turns as finished upon restart, dropping user instructions until re-prompted.
  - Hook Architecture: The `SessionStart` hook exports session identity and environment variables but executes no audit of the prior turn's completion status.
- **Proposed One-Step Move**:
  - Advance from Level 1 `doctrine` to Level 3 **`JIT injection`** / Level 5 **`process` (`routing`)** at session start.
  - Operational Mechanism: During `SessionStart` execution, the initialization handler inspects the immediate prior turn in the local transcript or trace store. If the preceding turn contains an incoming prompt or dispatch without a corresponding terminal output, the hook synthesizes an `UNFINISHED_TURN_RECOVERY` block containing the interrupted prompt and context, injecting it into the session's opening prompt to ensure immediate resumption.

## 3. Implementation Contract and Build Criteria Matrix

| Failure Class | Current Placement | Target Placement | Mechanism | Verification Surface | Build Acceptance Criterion |
| :- | :- | :- | :- | :- | :- |
| **1. Unbacked Promises** | Level 2: `instructions` (`imperative`) | Level 4: `structural` (`friction`) | Turn completion / reply hook checks persistent write backing | PreToolUse / Stop hook | AC-1.1 & AC-1.2: Unbacked behavioral promises refused unless supported by in-turn write tool call or git commit. |
| **2. Settled Items Escalated** | Level 2: `instructions` (`imperative`) | Level 5: `process` (`required gate`) | `premise-check` `Sufficient:` validates against standing rulings | `premise_check_verdict.py` / card intake | AC-2.1 & AC-2.2: Reports escalating items covered by standing rulings fail `Sufficient:`, enforcing autonomous resolution. |
| **3. Orphaned Remainder** | Level 2: `instructions` (`imperative`) | Level 5: `process` (`routing` / `required gate`) | `premise-check` `Remainder:` check gates thread termination | `premise_check_gate.py` / `verdict.py` | AC-3.1 & AC-3.2: Handbacks stating queued tasks require verified dispatch invocation to close the gate. |
| **4. Partition Widening & Cards** | Level 2: `instructions` (`imperative`) | Level 4: `structural` (`friction`) | Pre-tool check on `AskUserQuestion` enforces single-decision and `Relay:` map | PreToolUse on `AskUserQuestion` | AC-4.1 & AC-4.2: Multi-question cards blocked; questions must derive from verified `Relay:` lines answering latest ask. |
| **5. Interrupted Turns Dropped** | Level 1: `doctrine only` | Level 3: `JIT injection` / Level 5: `process` (`routing`) | `SessionStart` prior turn audit injects interrupted context | `SessionStart` hook handler | AC-5.1 & AC-5.2: Interrupted turns detected on restart; recovery block injected into first prompt. |

## 4. Open Questions

- _None_: Stage 1 design specifications establish the complete behavioural contracts, touchpoints, and observable criteria across all five classes. Downstream Stage 2 tasks will implement the corresponding hook handlers, validator checks, and integration tests.
