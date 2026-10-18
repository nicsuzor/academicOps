---
title: Telegram Mini App Dashboard Integration
status: ready
---

# Telegram Mini App Dashboard Integration

This specification defines the architecture, protocol contract, and operational behaviour for hosting the conversational agent's mobile Mini App within the central operational dashboard domain. It serves operators seeking unified cognitive orientation, real-time session tracking, and bi-directional interaction across mobile and desktop environments.

## User stories

### US-1 Unified Dashboard Serving and Perimeter Access

As an operator, I want to access the agent's cognitive anchor, interactive cards, and session controls directly through the operational dashboard domain, so that I can supervise and guide active work without maintaining separate tunnel configurations.

- **AC-1.1** Given an authenticated dashboard session, when the operator navigates to the agent control interface, then the application renders the cognitive anchor, context usage, and recent turns without prompting for secondary credentials.
- **AC-1.2** Given an operator opening the Mini App within a native Telegram client, when the application initialises, then the backend validates the signed Telegram authentication payload and grants access to the dedicated responsive interface.
- **AC-1.3** Given an unauthenticated HTTP request lacking both valid dashboard perimeter credentials and valid Telegram authentication data, when accessing any protected endpoint, then the server rejects the request with HTTP 401 Unauthorized.

### US-2 Dynamic Real-Time State Population

As an operator observing session execution, I want the interface state to update reactively as the agent works, so that cognitive focus, token consumption, and pending decisions reflect live runtime state.

- **AC-2.1** Given an active agent session, when the agent updates its cognitive focus, task bindings, or context token counts, then connected dashboard clients receive and render the updated state within 500 milliseconds without page reloading.
- **AC-2.2** Given a newly posted question or tool permission request, when the agent emits the request, then the interface dynamically displays the corresponding interactive card with selection options.
- **AC-2.3** Given an unexpected connection interruption, when the client reconnects to the event stream, then the client automatically requests a full state snapshot to reconcile missed updates.
- **AC-2.4** Given a pending artifact or pull request review assigned to the operator, when the operator inspects reviews in the interface, then the application displays the change diff with approve and request-changes actions.

### US-3 Bi-directional Agent Channel

As an operator directing the agent, I want a direct communication channel through the dashboard, so that I can send prompts, answer structured questions, and approve tool permissions.

- **AC-3.1** Given a pending tool permission request displayed in the dashboard, when the operator submits an allow or deny decision, then the agent receives the decision immediately and unblocks execution.
- **AC-3.2** Given a pending question card in the interface, when the operator selects options or inputs custom text and submits, then the agent receives the structured answer and the question card transitions to resolved.
- **AC-3.3** Given an active session, when the operator dispatches a prompt or directive through the dashboard interface, then the agent receives the turn as an inbound notification and acknowledges receipt.
- **AC-3.4** Given a question or permission resolved via the dashboard interface, when the resolution completes, then the corresponding Telegram chat card updates to show the resolved outcome.
- **AC-3.5** Given an active session, when the operator dispatches a halt directive, then the agent immediately suspends execution and returns a status summary.

## Design

### 1. Unified Serving and Perimeter Authentication (US-1)

#### 1.1 Context and Problem

The agent interface must serve two client topologies: (a) standalone mobile access embedded as a Telegram WebApp inside a mobile messenger, and (b) integrated desktop access embedded within the operator's central dashboard application. The hosting layer must securely identify the operator across both surfaces while preserving single-tap mobile launching.

#### 1.2 Architectural Options

- **Option 1.1 (Telegram-Only Authentication):** Require Telegram WebApp signature validation on every request. Direct desktop browser access to the dashboard requires launching via Telegram desktop or passing synthetic Telegram parameters.
- **Option 1.2 (Perimeter-Only Authentication):** Place the entire application behind dashboard perimeter identity (such as Cloudflare Access with Google OAuth). All requests must satisfy perimeter identity headers.
- **Option 1.3 (Dual-Mode Perimeter Authentication -- Recommended):** Employ perimeter identity as the primary gate for direct web visits, combined with an authenticated bypass and validation bridge for signed Telegram WebApp launches.
  - _Recommendation Rationale:_ Mobile WebViews in chat clients struggle with third-party OAuth redirect loops and external identity providers, whereas desktop operators already hold active dashboard sessions. Dual-mode authentication guarantees friction-free access on both devices while strictly enforcing cryptographic identity checks on every request.

#### 1.3 Recommended Serving and Authentication Contract

1. **Perimeter Ingress:**
   - The primary dashboard ingress terminates at the central web application.
   - Standalone client routes are published under `/app/*` (static bundle and responsive standalone shell) and API endpoints under `/api/app/*`.
   - Desktop operators access the embedded view under the primary dashboard layout at `/agent`.
2. **Authentication Flow:**
   - **Mode A (Telegram Launch):** The client transmits the cryptographic initialization payload via `POST /api/app/auth`. The server verifies the cryptographic hash against the bot secret token using HMAC-SHA256, validates timestamp freshness (maximum age: 3600 seconds), and checks user identity against the authorized operator list. On success, the server issues an HTTP-only, secure, strict SameSite session cookie with a 1-hour expiry.
   - **Mode B (Dashboard Perimeter):** For requests arriving from the dashboard domain, the server inspects the perimeter identity assertion header (`Cf-Access-Jwt-Assertion` or verified local session). When the identity assertion matches the authorized operator email, the request is authenticated directly without requiring Telegram initialization payloads.
   - **Rejection:** Any request to protected endpoints (`/api/app/*`) lacking both a valid session cookie and a valid perimeter assertion receives HTTP 401 Unauthorized.

### 2. Dynamic State Population (US-2)

#### 2.1 Context and Problem

The agent's state encompasses multiple components:

- _Cognitive Anchor:_ Current focus summary, active task identifier, waiting-on items, subagent delegations, and token gauge metrics (used tokens, total tokens, percentage).
- _Pending Decisions:_ Interactive multi-choice questions awaiting operator selection.
- _Tool Permissions:_ Pending tool invocations requiring human authorization.
- _Turn History:_ Recent inbound and outbound interaction turns.
- _Artifact Reviews:_ Pending pull request diffs and reviews.

The dashboard host runs on a dedicated service host, while the active agent session executes in an execution runtime. State must synchronize dynamically without manual browser polling.

#### 2.2 Architectural Options

- **Option 2.1 (Periodic Client Polling):** The client polls `GET /api/app/anchor` and `GET /api/app/questions` at fixed intervals (e.g. every 2 seconds).
  - _Trade-off:_ High query churn, unnecessary network overhead, and unacceptable latency (up to 2 seconds) for interactive permission prompts.
- **Option 2.2 (Shared Database Polling):** Centralise state in a shared database accessed by both the agent runtime and the dashboard.
  - _Trade-off:_ Introduces schema coupling and database maintenance overhead for transient interactive promises (such as in-flight permission requests).
- **Option 2.3 (Server-Sent Events with REST Snapshot Hydration -- Recommended):** Use REST endpoints for initial state hydration and on-demand lookups, supplemented by a real-time Server-Sent Events (SSE) stream (`GET /api/app/events`) for instant push updates.
  - _Recommendation Rationale:_ SSE provides unidirectional, lightweight HTTP streaming compatible with standard reverse proxies, corporate tunnels, and mobile WebViews without WebSocket upgrade complexity. State updates propagate in sub-second time.

#### 2.3 Recommended Dynamic Data Contract

1. **Initial Hydration:**
   - `GET /api/app/anchor`: Returns the current anchor snapshot, token gauge, pending questions summary, and recent turns.
   - `GET /api/app/questions`: Returns the active list of unresolved questions.
   - `GET /api/app/review`: Returns pending permission requests and assigned pull request reviews.
2. **Reactive Event Stream (`GET /api/app/events`):**
   - The server maintains a persistent text/event-stream connection to authenticated clients.
   - Event types emitted:
     - `anchor`: Payload contains updated cognitive anchor and token metrics.
     - `question_posted`: Payload contains newly issued question card.
     - `question_resolved`: Payload contains question identifier and chosen answer.
     - `permission_requested`: Payload contains permission request identifier, tool name, and input preview.
     - `permission_resolved`: Payload contains permission identifier and outcome (`allow` | `deny`).
     - `turn_recorded`: Payload contains direction (`in` | `out`), text summary, and timestamp.
3. **Resilience and Invariants:**
   - The SSE stream includes keep-alive heartbeat comments every 15 seconds.
   - When a client disconnects and reconnects, it receives the latest sequence number and fetches a fresh state snapshot via `GET /api/app/anchor` to guarantee convergence.

### 3. Bi-directional Operator Communication Channel (US-3)

#### 3.1 Context and Problem

The operator must be able to interact with the active agent directly from the dashboard: providing feedback, answering multiple-choice questions, deciding on tool executions, sending freeform steering instructions, or triggering an emergency stop.

#### 3.2 Architectural Options

- **Option 3.1 (Telegram Webhook Proxying):** The dashboard forwards operator inputs to the Telegram Bot API as simulated chat messages.
  - _Trade-off:_ Dependent on external third-party API availability, adds latency, and forces web-specific interactions through Telegram message constraints.
- **Option 3.2 (Direct Agent Channel Bridge -- Recommended):** The dashboard server forwards operator inputs directly to the agent's channel bridge via authenticated HTTP endpoints, dispatching channel notifications into the agent session.
  - _Recommendation Rationale:_ Decouples dashboard communication from external chat networks, provides sub-100ms response delivery, and maintains local custody of operator commands.

#### 3.3 Recommended Communication Protocol

1. **Freeform Direct Messaging (`POST /api/app/message`):**
   - Request: `{ "text": string, "priority": "normal" | "high" }`
   - The channel bridge packages the input as an inbound channel notification delivered directly into the agent session context.
   - Response: `{ "success": true, "message_id": string }`
2. **Structured Question Resolution (`POST /api/app/questions/answer`):**
   - Request: `{ "question_id": string, "option_index"?: number, "option_indices"?: number[], "custom_text"?: string }`
   - The server marks the question resolved, emits a channel event to the agent runtime, and triggers an in-place edit on any associated chat card to display the selected choice.
   - Response: `{ "success": true, "resolved_at": string }`
3. **Tool Permission Resolution (`POST /api/app/review/permission`):**
   - Request: `{ "permission_id": string, "decision": "allow" | "deny" }`
   - The server resolves the pending permission promise, unblocking tool execution in the agent runtime.
   - Associated chat cards update immediately with status "Allowed via Dashboard" or "Denied via Dashboard".
   - Response: `{ "success": true, "decision": "allow" | "deny" }`
4. **Session Intervention (`POST /api/app/stop`):**
   - Request: `{ "reason"?: string }`
   - The server emits a high-priority interrupt notification into the agent session instructing the agent to halt current work and provide a summary report.
   - Response: `{ "success": true, "status": "stop_dispatched" }`

### 4. Cross-Channel State Synchronization Invariants

1. **Single Source of Truth:** The running agent session runtime maintains the authoritative state of active tasks, anchors, questions, and permission requests.
2. **Mutual Invalidation:** An action completed on one surface (such as answering a question in Telegram chat) immediately updates all connected surfaces: the dashboard event stream broadcasts `question_resolved` and the Mini App removes the pending prompt. Conversely, an action resolved in the dashboard immediately edits the Telegram chat card to disable inline buttons and indicate resolution.
3. **Zero Orphaned Permissions:** If a tool permission request times out or the agent session restarts, any open permission cards in both Telegram and the dashboard transition automatically to an expired state.
