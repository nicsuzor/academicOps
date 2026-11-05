---
title: Telegram Mini App Operator Experience and Agent Bridge
status: ready
---

# Telegram Mini App Operator Experience and Agent Bridge

The Telegram Mini App provides a focused mobile and embedded interface for supervising and directing conversational agents. It serves operators seeking continuous cognitive orientation, real-time context tracking, interactive decision resolution, tool execution governance, and bidirectional steering across mobile and desktop environments.

## User stories

### US-1 Live Cognitive Anchor and Turn History

As an operator observing session execution, I want to view the agent's current focus, task bindings, token consumption, and recent interaction turns, so that I maintain cognitive orientation without interrupting active work.

- **AC-1.1** Given an active agent session, when the agent updates its cognitive focus, task bindings, or context token counts, then connected clients receive and render the updated anchor within 500 milliseconds without requiring a page reload.
- **AC-1.2** Given an active session, when turns occur, then recent inbound and outbound turns render in chronological order with direction indicators and timestamps.
- **AC-1.3** Given a transient network disconnection, when the client reconnects to the event stream, then the client fetches an anchor snapshot to reconcile missed updates.
- **AC-1.4** Given a pending pull request or artifact review assigned to the operator, when inspected in the interface, then the application displays the change diff with review actions.

### US-2 Interactive Structured Question Cards

As an operator directing the agent, I want to answer structured multiple-choice questions with recommendations and contextual drill-down, so that I can resolve design choices and clarifications asynchronously.

- **AC-2.1** Given a newly posted question emitted by the agent, when the card renders in the interface, then it presents selection options with the primary recommendation highlighted first.
- **AC-2.2** Given a question carrying extended background context (`detail`), when rendered in the interface, then the card displays a details action that opens the background modal.
- **AC-2.3** Given a question configured as Mini-App-only (`mini_app_only: true` or `chat: false`), when emitted by the agent, then the card renders in the Mini App interface without dispatching a card to Telegram chat.
- **AC-2.4** Given a pending question card, when the operator selects choices or enters custom text and submits, then the agent receives the answer payload within 100 milliseconds, unblocking execution, and the card transitions to resolved.

### US-3 Tool Permission Authorization and Expiration

As an operator supervising tool executions, I want to authorize or deny sensitive tool invocations with automatic expiration safeguards, so that autonomous operations execute only with verified human oversight.

- **AC-3.1** Given a tool invocation requiring authorization, when emitted by the agent, then the interface displays a permission card detailing the tool name and input parameter preview.
- **AC-3.2** Given a pending permission card, when the operator submits an allow or deny decision, then the agent receives the decision within 100 milliseconds, resuming or blocking execution.
- **AC-3.3** Given a pending permission request exceeding 300 seconds without operator response, when timeout occurs, then the request automatically transitions to expired, denying execution and updating connected cards with buttons disabled.

### US-4 Operator Directives and Emergency Stop

As an operator guiding an active session, I want to dispatch freeform steering directives or trigger an emergency halt, so that I can provide ad-hoc guidance or pause execution when necessary.

- **AC-4.1** Given an active session, when the operator submits a freeform message, then the agent receives the directive as an inbound turn and records it in turn history.
- **AC-4.2** Given an active session, when the operator issues a stop directive, then a high-priority halt signal is delivered into the session context and the interface updates the status card to halted within 500 milliseconds.

### US-5 Automatic Question Dismissal Across Channels

As an operator, I want answered questions dismissed automatically regardless of the resolution channel, so that outstanding lists reflect only unresolved items.

- **AC-5.1** Given a pending question, when answered within the asking agent session or via the Mini App, then the question transitions to resolved and leaves the pending list without manual intervention.
- **AC-5.2** Given a pending question, when answered via a plain Telegram reply to the chat card, then the question transitions to answered and leaves the pending list.
- **AC-5.3** Given a pending question, when Telegram API delivery fails, then the failure is surfaced immediately to the asking agent, marked failed in the broker, and excluded from active pending questions.

## Design

### 1. State Model and Snapshot Endpoints (US-1)

The local agent bridge maintains live session state identified by a strictly increasing monotonic sequence counter (`seq`).

1. **Snapshot Hydration:**
   - `GET /api/app/anchor`: Returns the current cognitive anchor snapshot (focus summary, active task, waiting-on items, subagent delegations), token gauge (used tokens, total tokens, percentage), recent turns, and current `seq`.
   - `GET /api/app/questions`: Returns all currently pending questions with their option arrays, recommendations, and current `seq`.
   - `GET /api/app/review`: Returns pending tool permission requests and artifact review diffs. Each permission record carries `status: "pending" | "expired"`.
2. **Reactive Event Stream (`GET /api/app/events`):**
   - Transmits standard `text/event-stream` frames with monotonic sequence numbering:
     ```http
     id: <seq>
     event: <eventType>
     data: {"seq": <seq>, ...payload}
     ```
   - Event types: `anchor`, `question_posted`, `question_resolved`, `permission_requested`, `permission_resolved`, and `turn_recorded`.
   - Emits `: keepalive\n\n` comments every 15 seconds during idle periods.
   - When a client reconnects with `Last-Event-ID: <seq>` or `?since=<seq>`, the bridge replays buffered events with sequence numbers greater than the requested sequence, or supplies a fresh snapshot if sequence gap exceeds buffer capacity.

### 2. Structured Questions Protocol (US-2, US-5)

1. **Posting Contract:**
   - Agents emit structured questions with options, optional single/multi-selection flags, optional recommendation, and optional extended markdown detail.
   - When `mini_app_only: true` or `chat: false` is configured, the question registers in the bridge store but skips posting a message card to Telegram chat.
   - When extended `detail` is provided, question cards display a details action opening the background modal.
2. **Resolution Contract (`POST /api/app/questions/answer`):**
   - Request Body:
     ```json
     {
       "question_id": "string",
       "option_index": 0,
       "option_indices": [0],
       "custom_text": "string"
     }
     ```
   - Transitions question status to resolved in the local broker, unblocks the waiting agent turn, broadcasts `question_resolved` over SSE, and updates associated Telegram chat cards to display the selected choice with inline keyboard buttons removed.
3. **Cross-Channel Resolution Invariant:**
   - Answering a question on any channel (in-session tool resolution, Telegram chat card reply, or Mini App submission) updates the broker status to resolved, broadcasting the resolution to all connected surfaces and removing the item from `GET /api/app/questions`.
4. **Delivery Failure Isolation:**
   - If Telegram API delivery fails, the failure reason is returned to the asking agent, the question status is marked `failed`, and it is excluded from active pending questions.

### 3. Tool Permission Authorization Protocol (US-3)

1. **Permission Card Contract:**
   - When a tool requires authorization, the agent bridge creates a pending permission record and emits `permission_requested` over SSE.
2. **Resolution Contract (`POST /api/app/review/permission`):**
   - Request Body:
     ```json
     {
       "permission_id": "string",
       "decision": "allow" | "deny"
     }
     ```
   - Resolves the execution promise in the runtime, emits `permission_resolved`, and updates any Telegram card to show allowed or denied with buttons cleared.
3. **Expiration Safeguard:**
   - Pending permissions have a maximum lifetime of 300 seconds.
   - Upon timeout or agent process restart, lingering pending records transition to `status: "expired"`, denying execution to prevent dangling actions, emitting `permission_resolved` with `outcome: "expired"`, and disabling card buttons.

### 4. Directives and Emergency Stop (US-4)

1. **Steering Directive (`POST /api/app/message`):**
   - Request: `{ "text": "string", "priority": "normal" | "high" }`
   - Injects the text directly as an inbound turn into the agent session, appends to turn history, and emits `turn_recorded`.
2. **Session Halt (`POST /api/app/stop`):**
   - Request: `{ "reason": "string" }`
   - Delivers a high-priority interrupt notification into the session instructing the agent to pause work and provide a summary report, updates card display to halted, and returns `{ "success": true, "status": "stop_dispatched" }`.
