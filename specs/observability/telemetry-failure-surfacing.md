---
title: Telemetry failure surfacing and session gating
status: draft
---

# Telemetry failure surfacing and session gating

Defines how OpenTelemetry emitters across all execution surfaces detect, report, and handle missing configuration, authorization rejections, and export errors, ensuring zero silent telemetry failures while providing explicit policy choices for session gating.

## User stories

### US-1 Immediate visibility on unconfigured telemetry endpoints

As an operator or agent running in any execution environment, I want immediate, conspicuous notification when OpenTelemetry tracing is unconfigured, so that a session never operates under the false assumption that its activity is being captured in Phoenix.

- **AC-1.1** Given an execution surface where OpenTelemetry tracing is supported, when a session initializes without a trace endpoint configured (`GENAI_ENGINE_TRACE_ENDPOINT` and `OTEL_EXPORTER_OTLP_ENDPOINT` unset or empty), then the emitter writes a conspicuous warning notice to standard error, and the session initialization hook injects a diagnostic notice into the active session context.
- **AC-1.2** Given an unconfigured tracer during tool execution or hook evaluation, when the tracer evaluates configuration, then it surfaces the unconfigured state through explicit diagnostic logs rather than returning a silent no-op.
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

### US-4 Verification and testability

As a developer maintaining telemetry emitters, I want every failure condition across every emitter covered by automated tests and reproduction runs, so that regressions to silent failure modes are caught before release.

- **AC-4.1** Automated unit and integration tests assert that each emitter produces visible standard error or session context output across all three failure cases: unconfigured endpoint, HTTP 401/403 authorization rejection, and network/collector error.
- **AC-4.2** Integration tests assert that unconfigured or failing telemetry never suppresses diagnostic output or exits with silent code 0 without user/session notification.

## Design

### Emitter Inventory and Failure Reporting Matrix

The framework encompasses eight distinct telemetry emitters across client sessions, container dispatch, server processes, and CI runners:

| Emitter | Service Name | Implementation Path | Case 1: Unconfigured Endpoint | Case 2: Export Refused (HTTP 401/403) | Case 3: Export Error (Timeout / 5xx) |
| :- | :- | :- | :- | :- | :- |
| **Claude Code Hook Tracer** | `aops-claude-hooks` | `plugins/ida/hooks/claude_code_tracer.py` | **User sees:** Stderr warning on first hook call naming missing endpoint.<br>**Session sees:** Injected context warning on `SessionStart` / turn 1: `WARNING: OpenTelemetry tracing unconfigured`.<br>**When:** Session start and first tool invocation. | **User sees:** Stderr error naming endpoint and HTTP 401/403 rejection.<br>**Session sees:** Post-tool diagnostic notice on export refusal.<br>**When:** Immediately upon failed HTTP POST. | **User sees:** Stderr warning with exception class, endpoint, and timeout duration.<br>**Session sees:** Post-tool diagnostic notice on repeated failure.<br>**When:** Immediately after bounded 2s timeout. |
| **Antigravity Hook Tracer** | `aops-agy-hooks` | `plugins/ida/hooks/agy_tracer.py` | **User sees:** Stderr warning on `PreInvocation` when endpoint unset.<br>**Session sees:** Injected `SYSTEM_MESSAGE` warning: `WARNING: OpenTelemetry tracing unconfigured`.<br>**When:** Session start (`PreInvocation`). | **User sees:** Stderr error with HTTP 401/403 and target URL.<br>**Session sees:** Diagnostic notification in session context.<br>**When:** Immediately upon failed HTTP POST. | **User sees:** Stderr warning with network error details.<br>**Session sees:** Diagnostic notice on connection error.<br>**When:** Immediately after bounded 2s timeout. |
| **Premise-Check Verdict Span** | `aops-verdict-hooks` | `plugins/ida/hooks/premise_check_verdict.py` | **User sees:** Explicit error output naming missing OTel configuration.<br>**Session sees:** Refusal exception details when evaluating verdict.<br>**When:** During `record_verdict` execution. | **User sees:** Stderr error with HTTP 401/403 response details.<br>**Session sees:** Refusal exception stating export authorization failure.<br>**When:** During `record_verdict` span export. | **User sees:** Stderr error detailing timeout or network fault.<br>**Session sees:** Refusal exception stating span export failed.<br>**When:** During `record_verdict` span export. |
| **CI OpenTelemetry Hooks** | `academicOps` | `scripts/ci_otel_hooks.py` | **User sees:** Workflow step output and GitHub Actions `::notice::` or `::warning::` annotation: `GENAI_ENGINE_TRACE_ENDPOINT unset; run untraced`.<br>**Session sees:** N/A (CI headless).<br>**When:** CI job setup step (`build_settings`). | **User sees:** Workflow annotation and step stderr: `OTel export refused (HTTP 401/403)`.<br>**Session sees:** Marker file entry.<br>**When:** Job teardown and hook execution. | **User sees:** Workflow annotation: `OTel export failed (timeout/error)`.<br>**Session sees:** Marker file entry.<br>**When:** Job teardown and hook execution. |
| **Evaluation Trace Emitter** | `rbg-evaluator` | `plugins/rbg/hooks/evaluator_otel_trace.py` | **User sees:** Stderr notice once per evaluation sweep when path unset.<br>**Session sees:** N/A (evaluator runs out of band).<br>**When:** First evaluation sweep. | **User sees:** Stderr error on file/endpoint write permission rejection.<br>**Session sees:** N/A.<br>**When:** Span write attempt. | **User sees:** Stderr error on file I/O or serialization failure.<br>**Session sees:** N/A.<br>**When:** Span write attempt. |
| **PKB MCP Server** | `pkb` | `src/otel/mod.rs` (in `mem`) | **User sees:** Server startup log warning or container stderr: `Tracing endpoint not configured`.<br>**Session sees:** N/A (server-side).<br>**When:** Server startup initialization. | **User sees:** Server error log: `Span export refused: 401/403`.<br>**Session sees:** N/A.<br>**When:** Tool execution span export. | **User sees:** Server error log: `Span export failed: connection timeout`.<br>**Session sees:** N/A.<br>**When:** Batch export flush. |
| **Container Dispatch MCP** | `polecat-mcp` | `containers/nicwin/polecat-mcp/telemetry.py` | **User sees:** Service stderr log on initialization: `No OTel endpoint configured`.<br>**Session sees:** Tool response metadata indicates untraced dispatch.<br>**When:** Dispatcher daemon startup. | **User sees:** Service stderr error on HTTP 401/403 from collector.<br>**Session sees:** Dispatch span export failure in service logs.<br>**When:** Container run span export. | **User sees:** Service stderr error on connection timeout/refusal.<br>**Session sees:** Dispatch span export failure in service logs.<br>**When:** Container run span export. |
| **Client Native Exporters** | `claude-native` / `antigravity` | Harness native configuration | **User sees:** Harness diagnostic logs (e.g. `~/.claude/logs/` or agy logs).<br>**Session sees:** N/A.<br>**When:** Harness startup and turn completion. | **User sees:** Client network log entries reporting HTTP 401/403.<br>**Session sees:** N/A.<br>**When:** Harness native export flush. | **User sees:** Client network log entries reporting timeout or connection refusal.<br>**Session sees:** N/A.<br>**When:** Harness native export flush. |

### Invariants and Telemetry Contracts

1. **Zero Silence Invariant**: Under no circumstance does any telemetry emitter silently swallow a missing configuration or export error into a no-op or debug log. Every failure must produce visible stderr output and, on interactive surfaces, an injected session context notice.
2. **Secret Scrubbing**: Diagnostics output to stderr, logs, or session context must redact authorization tokens, passwords, and service keys (`GENAI_ENGINE_API_KEY`, `CF-Access-Client-Secret`, `Bearer ...`). Only hostnames, endpoints, and HTTP status codes are emitted.
3. **Bounded Latency**: Exporters must enforce a strict connection and request timeout not exceeding 2 seconds (`_EXPORT_TIMEOUT_S = 2`). Export failures must not cause unbuffered multi-second blocking of user interaction or tool turns.

### Verification Mapping

| Criterion | Condition | Observable Verification Check |
| :- | :- | :- |
| **AC-1.1** | Unset endpoint on session start | Run test harness with `GENAI_ENGINE_TRACE_ENDPOINT` unset; verify stderr contains warning banner and `SessionStart` hook injects unconfigured warning into context. |
| **AC-1.2** | Unset endpoint during tool hook | Run `claude_code_tracer.py pre_tool` with unset endpoint; verify stderr warning is emitted and exit code is non-silent. |
| **AC-1.3** | Unset endpoint in CI | Execute `scripts/ci_otel_hooks.py` with unset endpoint; assert `::notice::` or `::warning::` is written to stdout. |
| **AC-2.1** | HTTP 401/403 on export | Mock exporter with HTTP 403 Forbidden response; assert stderr contains `ERROR: OTel span export refused (HTTP 403)` with endpoint URL. |
| **AC-2.2** | Session context notification on 403 | Mock HTTP 403 during active turn; assert diagnostic notification is returned in hook response or session notice. |
| **AC-2.3** | Throttling repeated 403 warnings | Mock repeated HTTP 403 responses across 10 tool calls; assert stderr logs initial failure with diagnostic details and throttles duplicate messages without latency spikes. |
| **AC-3.1** | Network timeout / connection error | Point endpoint to non-routable IP; assert stderr logs connection failure with error type and elapsed time within 2 seconds. |
| **AC-3.2** | Collector 5xx server error | Mock exporter with HTTP 503 Service Unavailable; assert stderr logs HTTP 503 and collector error text. |
| **AC-3.3** | Bounded export timeout | Measure elapsed time on unreachable endpoint; assert total export duration does not exceed 2.5 seconds. |

## Enforcement pyramid pass

Following `specs/enforcement/enforcement.md`, mechanisms for ensuring telemetry failure visibility are evaluated from least-invasive to most-invasive:

1. **`doctrine only`**:
   - _Proposal:_ Declare in documentation and principles that "telemetry problems must never fail silently."
   - _Evaluation:_ Insufficient on its own. Telemetry emitters execute in low-level runtime processes, hooks, and network boundaries where doctrine has no operational mechanism to prevent silent exceptions or no-op returns.
2. **`instructions` (`suggestion` → `advisory` → `imperative` → `absolute`)**:
   - _Proposal:_ Instruct agents to verify whether their session is actively exporting spans to Phoenix.
   - _Evaluation:_ Insufficient. Agents cannot inspect whether external HTTP POST requests succeeded or whether environment variables were dropped by the host container before session launch.
3. **`JIT injection`**:
   - _Proposal:_ When an emitter detects an unconfigured endpoint, HTTP 401/403 rejection, or persistent export failure, inject an explicit warning notice into the session's active context via `SessionStart`, `UserPromptSubmit`, or post-tool hook outputs.
   - _Evaluation:_ Highly effective for session awareness. The agent learns immediately that its audit trail is broken, preventing the false premise that work is being traced.
4. **`structural` (`warning` → `friction` → `block` → `protection`)**:
   - _`warning`:_ Emitters write prominent error diagnostics to standard error on every failed configuration or export attempt.
   - _`friction` / `block`:_ Hooks fail with non-zero exit codes or refuse tool calls when telemetry is failing, preventing untraced work from proceeding.
   - _Evaluation:_ Stderr warnings are the required baseline across all surfaces. Whether to escalate from `warning` to `block` is a major policy choice set out below.
5. **`process` (`required gate`)**:
   - _Proposal:_ The premise-check verdict gate requires a confirmed OpenTelemetry span export before allowing a verdict to disarm the hearsay gate.
   - _Evaluation:_ Currently active in `plugins/ida/hooks/premise_check_verdict.py`. When tracing is unconfigured, this gate fails closed, creating a deadlock in environments lacking tracing variables.
6. **`post-hoc` (`observability` → `proactive detection`)**:
   - _Proposal:_ Periodic sweeps or monitoring daemons check Phoenix trace ingestion by session ID and alert on sessions missing traces.
   - _Evaluation:_ Complementary, but reactive: does not solve real-time failure visibility during the session.

_Outcome of Pyramid Pass:_ JIT injection and structural warnings are mandatory to satisfy the Zero Silence invariant. The decision whether to escalate to structural blocking is set out as policy options below.

## Policy options: blocking versus non-blocking

The fundamental tension is whether telemetry failure should **halt session execution** (fail-closed, guaranteeing zero untraced work at the expense of availability) or **alert loudly while allowing work to proceed** (fail-open for progress, fail-loud for awareness).

### Option 1: Loud Non-Blocking (Fail-Loud / Fail-Open for Progress)

- **Mechanics:**
  - When no endpoint is set, or when export fails with HTTP 401/403 or network errors, emitters write prominent, colored warnings to standard error and inject a diagnostic notice into the session context.
  - The session is allowed to proceed; tool calls and agent commands are not blocked.
  - The premise-check verdict gate detects the unconfigured or failing telemetry state: instead of raising a terminal `RuntimeError`, it logs a loud warning, records a local or untraced verdict record, and disarms the hearsay gate so the session can continue without deadlocking.
- **Consequences:**
  - _Pros:_ Sessions never deadlock due to telemetry infrastructure glitches, transient network outages, or missing credentials in third-party or cloud environments. Progress is never blocked by observability tooling.
  - _Cons:_ Untraced work can occur. If an operator ignores standard error warnings, entire sessions may complete without any trace records in Phoenix, permanently losing auditability.

### Option 2: Hard Blocking (Fail-Closed)

- **Mechanics:**
  - Missing endpoint configuration, HTTP 401/403 authorization rejection, or unresolvable export failure halts session startup or causes hook invocations to exit with a non-zero error code.
  - Tool calls and dispatches are strictly refused while telemetry is broken.
  - The premise-check verdict gate strictly fails closed: any failure to export a `premise_check_verdict` span leaves the hearsay gate armed, blocking peer messaging, question asking, and `Stop`.
- **Consequences:**
  - _Pros:_ Absolute guarantee that zero untraced work is ever performed. Complete auditability across the entire system.
  - _Cons:_ High operational fragility. Any transient Cloudflare Access glitch, network proxy failure, or unconfigured cloud container immediately stops all agent work. Ad-hoc, offline, or fork-based workflows are prohibited unless a mock collector is supplied.

### Option 3: Configurable Surface-Gated (Hybrid by Surface and Toggle)

- **Mechanics:**
  - Governed by an explicit configuration flag: `AOPS_TELEMETRY_FAILURE_MODE=block|warn` (defaulting to `block` in production container dispatch workers, and `warn` in interactive local sessions and CI runners).
  - In `block` mode, behaves as Option 2 (hard stop on any telemetry fault).
  - In `warn` mode, behaves as Option 1 (loud standard error banner, injected context notice, verdict gate permits local fallback recording with untraced annotation).
- **Consequences:**
  - _Pros:_ Protects autonomous worker runs where auditability is non-negotiable while preventing deadlocks in interactive human-in-the-loop sessions or lightweight developer environments.
  - _Cons:_ Adds a configuration branch and requires maintainers to understand which mode applies to each surface.

### Premise-Check Verdict Gate Specific Options

In a session where OpenTelemetry tracing is unconfigured or failing:

1. **Strictly Require Remote Span Export (Current Baseline):**
   - Attempting `record_verdict` raises `RuntimeError("premise_check_verdict: tracing is not configured")`.
   - Gate remains armed; agent cannot message peers, ask questions, or stop.
   - _Consequence:_ Complete deadlock in environments lacking telemetry endpoints (as observed in cloud sessions).
2. **Local Fallback Recording with Loud Session Warning:**
   - When tracing is unconfigured or export fails, `record_verdict` records the verdict to local session state with an `untraced: true` marker, emits a conspicuous warning to standard error, injects a warning into the session, and disarms the gate.
   - _Consequence:_ Resolves the deadlock completely; allows review workflows to proceed even when telemetry is degraded, while preserving local auditability on disk.
3. **Dedicated Premise-Check Gate Mode Flag:**
   - Controlled by `PREMISE_CHECK_VERDICT_TRACING=required|optional`.
   - When `required`, fails closed (Option 1). When `optional`, falls back to local recording with loud warning (Option 2).

## Open questions

- **Decision 1: Overall failure mode.** Which policy option should govern telemetry failure across the framework: Option 1 (Loud Non-Blocking), Option 2 (Hard Blocking), or Option 3 (Configurable Surface-Gated)?
- **Decision 2: Premise-check verdict gate behavior.** When tracing is unconfigured or span export fails, should the verdict gate fail closed (blocking the session) or allow local fallback disarming with a loud warning?
- **Decision 3: Cloudflare Access credential injection in cloud sessions.** Should cloud environments fail closed until the network secret format agrees with the Cloudflare Access app, or should cloud sessions run in loud non-blocking mode in the interim?
