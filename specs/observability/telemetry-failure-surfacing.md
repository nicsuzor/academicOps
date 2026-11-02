---
title: Telemetry failure surfacing and session gating
status: draft
---

# Telemetry failure surfacing and session gating

Defines how OpenTelemetry emitters across all execution surfaces detect, report, and handle missing configuration, authorization rejections, and export errors, ensuring zero silent telemetry failures while providing explicit policy choices for session gating.

## User stories

### US-1 Immediate visibility on unconfigured telemetry endpoints

As an operator or agent running in any execution environment, I want immediate, conspicuous notification when OpenTelemetry tracing is unconfigured, so that a session never operates under the false assumption that its activity is being captured in Phoenix.

- **AC-1.1** Given an execution surface where OpenTelemetry tracing is supported, when a session initializes without a trace endpoint configured (telemetry endpoint environment variables unset or empty), then the emitter writes a conspicuous warning notice to standard error, and the session initialization hook injects a diagnostic notice into the active session context.
- **AC-1.2** Given an unconfigured tracer during tool execution or hook evaluation, when the tracer evaluates configuration, then it surfaces the unconfigured state through explicit diagnostic standard error output rather than returning a silent no-op.
- **AC-1.3** Given an unconfigured tracer during CI workflow execution, when CI OpenTelemetry hooks initialize, then the setup script surfaces a visible notice in workflow job annotations and standard output identifying that the run is untraced.

### US-2 Immediate visibility on export authorization rejections

As an operator or agent running in an authenticated or proxied environment, I want immediate, diagnostic reporting when span export is rejected with an HTTP 401 or 403 Forbidden response, so that credential expiration, missing Access service tokens, or network secret mismatches are diagnosed at the first export attempt.

- **AC-2.1** Given an emitter attempting to export spans to an authenticated collector, when the collector or intermediate gateway rejects the export with an HTTP 401 or 403 status code, then the emitter surfaces the rejection immediately to standard error, identifying the target endpoint, the HTTP status code, and the sanitized response headers (excluding secret tokens).
- **AC-2.2** Given an export authorization rejection during an active session turn, when the rejection occurs, then the session context receives a diagnostic notification identifying that span export was refused due to authorization failure.
- **AC-2.3** Given repeated export authorization rejections within a single session, when subsequent tool calls execute, then the emitter throttles redundant network round-trips while keeping the authorization failure state visible in session status.

### US-3 Immediate visibility on network and collector export errors

As an operator or agent running on any surface, I want connection timeouts, connection refusals, DNS resolution failures, and collector server errors reported with actionable diagnostic detail, so that network and infrastructure failures are distinguished from credential or configuration defects.

- **AC-3.1** Given an emitter attempting span export, when the connection fails due to network timeout, DNS failure, connection refusal, or TLS handshake error, then the emitter logs the failure to standard error with the error type, target endpoint, and elapsed duration.
- **AC-3.2** Given an emitter attempting span export, when the collector returns an HTTP 5xx server error, then the emitter logs the collector error to standard error with the HTTP status code and response payload.
- **AC-3.3** Given a failing collector or unreachable network endpoint, when an emitter exports spans, then the export timeout is strictly bounded (at most 2 seconds per batch) to prevent interactive session latency degradation.

### US-4 Observable verification of failure surfacing across emitters

As a developer maintaining telemetry emitters, I want automated verification across all failure modes, so that regressions to silent failure modes are caught deterministically prior to deployment.

- **AC-4.1** Given an emitter executing in a verification run simulating an unconfigured endpoint, HTTP 401/403 authorization rejection, or network timeout, when telemetry export triggers, then standard error output or session context captures explicit diagnostic text for each respective failure condition.
- **AC-4.2** Given an emitter executing in a test environment, when any telemetry failure condition occurs, then the execution process produces non-empty diagnostic notifications rather than exiting silently without logging.

## Design

### Emitter Inventory and Failure Reporting Matrix

The framework encompasses eight distinct telemetry emitters across client sessions, container dispatch, server processes, and CI runners:

| Emitter | Service Name | Surface / Subsystem Role | Case 1: Unconfigured Endpoint | Case 2: Export Refused (HTTP 401/403) | Case 3: Export Error (Timeout / 5xx) |
| :- | :- | :- | :- | :- | :- |
| **Interactive Client Hook Tracer** | `aops-claude-hooks` | Interactive Client Hook Runtime | **User sees:** Stderr warning on first hook call naming missing endpoint.<br>**Session sees:** Injected context warning on session start / turn 1: `WARNING: OpenTelemetry tracing unconfigured`.<br>**When:** Session start and first tool invocation. | **User sees:** Stderr error naming endpoint and HTTP 401/403 rejection.<br>**Session sees:** Post-tool diagnostic notice on export refusal.<br>**When:** Immediately upon failed HTTP POST. | **User sees:** Stderr warning with exception class, endpoint, and timeout duration.<br>**Session sees:** Post-tool diagnostic notice on repeated failure.<br>**When:** Immediately after bounded 2s timeout. |
| **Agent CLI Hook Tracer** | `aops-agy-hooks` | Agent CLI Hook Runtime | **User sees:** Stderr warning on session initialization when endpoint unset.<br>**Session sees:** Injected system message warning: `WARNING: OpenTelemetry tracing unconfigured`.<br>**When:** Session startup. | **User sees:** Stderr error with HTTP 401/403 and target URL.<br>**Session sees:** Diagnostic notification in session context.<br>**When:** Immediately upon failed HTTP POST. | **User sees:** Stderr warning with network error details.<br>**Session sees:** Diagnostic notice on connection error.<br>**When:** Immediately after bounded 2s timeout. |
| **Report Verification Verdict Span** | `aops-verdict-hooks` | Report Verification Gate | **User sees:** Explicit error output naming missing telemetry configuration.<br>**Session sees:** Refusal exception details when evaluating verdict.<br>**When:** During verdict recording execution. | **User sees:** Stderr error with HTTP 401/403 response details.<br>**Session sees:** Refusal exception stating export authorization failure.<br>**When:** During verdict span export. | **User sees:** Stderr error detailing timeout or network fault.<br>**Session sees:** Refusal exception stating span export failed.<br>**When:** During verdict span export. |
| **CI Workflow Hooks** | `academicOps` | CI Workflow Runner | **User sees:** Workflow step output and job annotation notice: `Trace endpoint unset; run untraced`.<br>**Session sees:** N/A (CI headless runner).<br>**When:** CI job initialization step. | **User sees:** Workflow job annotation and step stderr: `OTel export refused (HTTP 401/403)`.<br>**Session sees:** Diagnostic marker file entry.<br>**When:** Job teardown and hook execution. | **User sees:** Workflow job annotation: `OTel export failed (timeout/error)`.<br>**Session sees:** Diagnostic marker file entry.<br>**When:** Job teardown and hook execution. |
| **Rule Evaluation Trace Emitter** | `rbg-evaluator` | Rule Evaluation Engine | **User sees:** Stderr notice once per evaluation sweep when trace path unset.<br>**Session sees:** N/A (evaluator runs out of band).<br>**When:** First evaluation sweep. | **User sees:** Stderr error on file/endpoint write permission rejection.<br>**Session sees:** N/A.<br>**When:** Span write attempt. | **User sees:** Stderr error on file I/O or serialization failure.<br>**Session sees:** N/A.<br>**When:** Span write attempt. |
| **Knowledge Base MCP Server** | `pkb` | Knowledge Base MCP Server | **User sees:** Server startup log warning or container stderr: `Tracing endpoint not configured`.<br>**Session sees:** N/A (server-side background process).<br>**When:** Server startup initialization. | **User sees:** Server error log: `Span export refused: 401/403`.<br>**Session sees:** N/A.<br>**When:** Tool execution span export. | **User sees:** Server error log: `Span export failed: connection timeout`.<br>**Session sees:** N/A.<br>**When:** Batch export flush. |
| **Container Dispatch MCP Server** | `polecat-mcp` | Container Dispatch Daemon | **User sees:** Service stderr log on initialization: `No OTel endpoint configured`.<br>**Session sees:** Tool response metadata indicates untraced dispatch.<br>**When:** Dispatcher daemon startup. | **User sees:** Service stderr error on HTTP 401/403 from collector.<br>**Session sees:** Dispatch span export failure in service logs.<br>**When:** Container run span export. | **User sees:** Service stderr error on connection timeout/refusal.<br>**Session sees:** Dispatch span export failure in service logs.<br>**When:** Container run span export. |
| **Native Client Exporters** | `claude-native` / `antigravity` | Native Client Harness | **User sees:** Harness diagnostic logs in client log directory.<br>**Session sees:** N/A.<br>**When:** Harness startup and turn completion. | **User sees:** Client network log entries reporting HTTP 401/403.<br>**Session sees:** N/A.<br>**When:** Harness native export flush. | **User sees:** Client network log entries reporting timeout or connection refusal.<br>**Session sees:** N/A.<br>**When:** Harness native export flush. |

### Invariants and Telemetry Contracts

1. **Zero Silence Invariant**: Under no circumstance does any telemetry emitter silently swallow a missing configuration or export error into a no-op or debug log. Every failure must produce visible stderr output and, on interactive surfaces, an injected session context notice.
2. **Secret Scrubbing**: Diagnostics output to stderr, logs, or session context must redact authorization tokens, passwords, and service keys. Only hostnames, endpoints, and HTTP status codes are emitted.
3. **Bounded Latency**: Exporters must enforce a strict connection and request timeout not exceeding 2 seconds. Export failures must not cause unbuffered multi-second blocking of user interaction or tool turns.

### Verification Mapping

| Criterion | Condition | Observable Verification Check |
| :- | :- | :- |
| **AC-1.1** | Unset endpoint on session start | Execute session startup with endpoint variables unset; assert standard error contains warning banner and session context receives unconfigured warning. |
| **AC-1.2** | Unset endpoint during tool hook | Execute tool hook with unset endpoint; assert standard error warning is emitted and exit code conforms to mode (code 0 in non-blocking mode; non-zero in blocking mode). |
| **AC-1.3** | Unset endpoint in CI | Execute CI telemetry hook setup with unset endpoint; assert job notice annotation is output. |
| **AC-2.1** | HTTP 401/403 on export | Mock exporter with HTTP 403 Forbidden response; assert standard error contains explicit authorization rejection notice with sanitized endpoint URL. |
| **AC-2.2** | Session context notification on 403 | Mock HTTP 403 during active turn; assert diagnostic notification is returned in hook response or session context. |
| **AC-2.3** | Throttling repeated 403 warnings | Mock repeated HTTP 403 responses across 10 tool calls; assert standard error logs initial diagnostic details and throttles duplicate messages without latency spikes. |
| **AC-3.1** | Network timeout / connection error | Route endpoint to non-routable destination; assert standard error logs connection failure with error type and elapsed duration. |
| **AC-3.2** | Collector 5xx server error | Mock exporter with HTTP 503 Service Unavailable; assert standard error logs HTTP 503 and collector response text. |
| **AC-3.3** | Bounded export timeout | Measure elapsed time on unreachable endpoint; assert total export duration does not exceed 2.0 seconds (with at most 500ms socket/harness overhead, total <= 2.5s). |
| **AC-4.1** | Simulated failure surfacing | Run verification suite simulating missing endpoint, 403 rejection, and timeout; assert standard error and context outputs match specified diagnostic formats. |
| **AC-4.2** | Non-silent failure verification | Run test harness validating that zero telemetry failure conditions exit 0 without writing diagnostic notices to standard error or session context. |

## Enforcement pyramid pass

Following the framework enforcement hierarchy, mechanisms for ensuring telemetry failure visibility are evaluated from least-invasive to most-invasive:

1. **`doctrine only`**:
   - _Proposal:_ Declare in documentation and principles that "telemetry problems must never fail silently."
   - _Evaluation:_ Insufficient on its own. Telemetry emitters execute in low-level runtime processes, hooks, and network boundaries where doctrine has no operational mechanism to prevent silent exceptions or no-op returns.
2. **`instructions` (`suggestion` → `advisory` → `imperative` → `absolute`)**:
   - _Proposal:_ Instruct agents to verify whether their session is actively exporting spans to Phoenix.
   - _Evaluation:_ Insufficient. Agents cannot inspect whether external HTTP POST requests succeeded or whether environment variables were dropped by the host container before session launch.
3. **`JIT injection`**:
   - _Proposal:_ When an emitter detects an unconfigured endpoint, HTTP 401/403 rejection, or persistent export failure, inject an explicit warning notice into the session's active context via session start, prompt submission, or post-tool hook outputs.
   - _Evaluation:_ Highly effective for session awareness. The agent learns immediately that its audit trail is broken, preventing the false premise that work is being traced.
4. **`structural` (`warning` → `friction` → `block` → `protection`)**:
   - _`warning`:_ Emitters write prominent error diagnostics to standard error on every failed configuration or export attempt.
   - _`friction` / `block`:_ Hooks fail with non-zero exit codes or refuse tool calls when telemetry is failing, preventing untraced work from proceeding.
   - _Evaluation:_ Stderr warnings are the required baseline across all surfaces. Whether to escalate from `warning` to `block` is a major policy choice set out below.
5. **`process` (`required gate`)**:
   - _Proposal:_ The report verification gate requires a confirmed OpenTelemetry span export before allowing a verdict to disarm the report gate.
   - _Evaluation:_ Active in the verdict recorder. When tracing is unconfigured, this gate fails closed, creating a deadlock in environments lacking tracing variables.
6. **`post-hoc` (`observability` → `proactive detection`)**:
   - _Proposal:_ Periodic sweeps or monitoring daemons check Phoenix trace ingestion by session ID and alert on sessions missing traces.
   - _Evaluation:_ Complementary, but reactive: does not solve real-time failure visibility during the session.

_Outcome of Pyramid Pass:_ JIT injection and structural warnings are mandatory to satisfy the Zero Silence invariant. The decision whether to escalate to structural blocking is set out as policy options below.

## Policy options: blocking versus non-blocking

The fundamental tension is whether telemetry failure should **halt session execution** (fail-closed, guaranteeing zero untraced work at the expense of availability) or **alert loudly while allowing work to proceed** (fail-open for progress, fail-loud for awareness).

### Option 1: Loud Non-Blocking (Fail-Loud / Fail-Open for Progress)

- **Mechanics:**
  - When no endpoint is set, or when export fails with HTTP 401/403 or network errors, emitters write prominent warnings to standard error and inject a diagnostic notice into the session context.
  - The session is allowed to proceed; tool calls and agent commands are not blocked.
  - The report verification gate detects the unconfigured or failing telemetry state: instead of raising a terminal exception, it logs a loud warning, records a local or untraced verdict record, and disarms the report gate so the session can continue without deadlocking.
- **Consequences:**
  - _Pros:_ Sessions never deadlock due to telemetry infrastructure glitches, transient network outages, or missing credentials in third-party or cloud environments. Progress is never blocked by observability tooling.
  - _Cons:_ Untraced work can occur. If an operator ignores standard error warnings, entire sessions may complete without any trace records in Phoenix, permanently losing auditability.

### Option 2: Hard Blocking (Fail-Closed)

- **Mechanics:**
  - Missing endpoint configuration, HTTP 401/403 authorization rejection, or unresolvable export failure halts session startup or causes hook invocations to exit with a non-zero error code.
  - Tool calls and dispatches are strictly refused while telemetry is broken.
  - The report verification gate strictly fails closed: any failure to export a verification verdict span leaves the gate armed, blocking peer messaging, question asking, and session completion.
- **Consequences:**
  - _Pros:_ Absolute guarantee that zero untraced work is ever performed. Complete auditability across the entire system.
  - _Cons:_ High operational fragility. Any transient network proxy failure or unconfigured cloud container immediately stops all agent work. Ad-hoc, offline, or fork-based workflows are prohibited unless a mock collector is supplied.

### Option 3: Configurable Surface-Gated (Hybrid by Surface and Toggle)

- **Mechanics:**
  - Governed by an explicit configuration flag: `AOPS_TELEMETRY_FAILURE_MODE=block|warn` (defaulting to `block` in production container dispatch workers, and `warn` in interactive local sessions and CI runners).
  - In `block` mode, behaves as Option 2 (hard stop on any telemetry fault).
  - In `warn` mode, behaves as Option 1 (loud standard error banner, injected context notice, verdict gate permits local fallback recording with untraced annotation).
- **Consequences:**
  - _Pros:_ Protects autonomous worker runs where auditability is non-negotiable while preventing deadlocks in interactive human-in-the-loop sessions or lightweight developer environments.
  - _Cons:_ Adds a configuration branch and requires maintainers to understand which mode applies to each surface.

### Report Verification Verdict Gate Specific Options

In a session where OpenTelemetry tracing is unconfigured or failing:

1. **Strictly Require Remote Span Export (Current Baseline):**
   - Attempting verdict recording raises a configuration exception when tracing is not configured.
   - Gate remains armed; agent cannot message peers, ask questions, or stop.
   - _Consequence:_ Complete deadlock in environments lacking telemetry endpoints (as observed in cloud sessions).
2. **Local Fallback Recording with Loud Session Warning:**
   - When tracing is unconfigured or export fails, the verdict recorder records the verdict to local session state with an `untraced: true` marker, emits a conspicuous warning to standard error, injects a warning into the session, and disarms the gate.
   - _Consequence:_ Resolves the deadlock completely; allows review workflows to proceed even when telemetry is degraded, while preserving local auditability on disk.
3. **Dedicated Gate Mode Flag:**
   - Controlled by `PREMISE_CHECK_VERDICT_TRACING=required|optional`.
   - When `required`, fails closed (Sub-option 1). When `optional`, falls back to local recording with loud warning (Sub-option 2).

## Open questions

- **Decision 1: Overall failure mode.** Which policy option should govern telemetry failure across the framework: Option 1 (Loud Non-Blocking), Option 2 (Hard Blocking), or Option 3 (Configurable Surface-Gated)?
  - _Recommendation:_ Adopt Option 3 (Configurable Surface-Gated). Autonomous headless workers in containers operate without human oversight and must fail closed to ensure complete trace capture; interactive and local sessions benefit from fail-loud non-blocking behavior so developer experimentation and ad-hoc troubleshooting never deadlock on telemetry network hiccups.
- **Decision 2: Report verification verdict gate behavior.** When tracing is unconfigured or span export fails, should the verdict gate fail closed (blocking the session) or allow local fallback disarming with a loud warning?
  - _Recommendation:_ Adopt Sub-option 2 (Local Fallback Recording with Loud Session Warning). Blocking a session from asking questions or stopping because an external OTel collector is down creates an unrecoverable deadlock. Emitting a loud stderr warning while writing the verdict record locally preserves local provenance without stranding the user.
- **Decision 3: Credential injection in cloud sessions.** Should cloud environments fail closed until the network secret format agrees with the upstream auth gateway, or should cloud sessions run in loud non-blocking mode in the interim?
  - _Recommendation:_ Run cloud sessions in loud non-blocking mode with explicit session start warnings until network secret authentication is validated, preventing broken sessions while secrets are tuned.
