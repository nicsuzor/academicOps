# Handoff Report: Explorer 3 — OpenTelemetry (OTEL) Telemetry & Tracing (Requirement R3)

## Summary
This report presents the findings of Explorer 3's read-only investigation into Requirement R3 (OpenTelemetry Telemetry & Tracing) across `lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, `lib/hooks/dispatch.py`, tool plumbing (`SendMessage` and `SubagentStop`), and existing test suites.

---

## 1. Observation

### Item 1: `OTEL_RESOURCE_ATTRIBUTES` Configuration & Injection
- **`lib/polecat/env_contract.py` lines 24–41**: `TELEMETRY_ENV` defines 16 environment variables:
  ```python
  TELEMETRY_ENV = (
      "CLAUDE_CODE_ENABLE_TELEMETRY",
      "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
      "ANTIGRAVITY_ENABLE_TELEMETRY",
      "OTEL_METRICS_EXPORTER",
      "OTEL_LOGS_EXPORTER",
      "OTEL_TRACES_EXPORTER",
      "OTEL_EXPORTER_OTLP_ENDPOINT",
      "OTEL_EXPORTER_OTLP_PROTOCOL",
      "OTEL_RESOURCE_ATTRIBUTES",
      "OTEL_LOG_USER_PROMPTS",
      "OTEL_LOG_RAW_API_BODIES",
      "OTEL_LOG_TOOL_DETAILS",
      "OTEL_LOG_ASSISTANT_RESPONSES",
      "OTEL_METRIC_EXPORT_INTERVAL",
      "OTEL_LOGS_EXPORT_INTERVAL",
      "OTEL_TRACES_EXPORT_INTERVAL",
  )
  ```
- **`lib/polecat/cli.py` lines 202–217**: `resolve_telemetry(config)` reads operator config:
  ```python
  def resolve_telemetry(config):
      telemetry = config.get("telemetry") or {}
      env = {}
      if telemetry.get("endpoint"):
          env["BETA_TRACING_ENDPOINT"] = str(telemetry["endpoint"])
          env["OTEL_EXPORTER_OTLP_ENDPOINT"] = str(telemetry["endpoint"])
      if telemetry.get("resource_attributes"):
          env["OTEL_RESOURCE_ATTRIBUTES"] = str(telemetry["resource_attributes"])
      return env
  ```
- **`lib/polecat/cli.py` lines 1189, 1174–1259**: `run()` resolves session parameters:
  - Line 1189: `session_id = session_name or f"session-{uuid.uuid4().hex[:8]}"`
  - Option arguments: `project` (`--project`/`-p`), `task` (`--task`/`-t`).
  - Lines 1256–1259: `env` is populated with container variables:
    ```python
    env["AOPS_POLECAT_CONTAINER"] = "1"
    env["POLECAT_CREW_NAME"] = session_id
    env["AOPS_SESSION_STATE_DIR"] = container_session_path
    env["AOPS_HOOK_LOG_PATH"] = f"{container_session_path}/polecat-session-hooks.jsonl"
    ```
- Currently, `polecat.session_id`, `polecat.project`, and `polecat.task_id` are NOT injected into `OTEL_RESOURCE_ATTRIBUTES`.

### Item 2: Hook Registration, Dispatching, Error Instrumentation & OTEL Emission
- **`lib/hooks/dispatch.py` lines 98–110, 309–353**: `dispatch.py` is invoked as `dispatch.py <client> <event>`:
  - Supported wire events map to canonical events via `to_canonical()`: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolBatch`, `Stop`, `SubagentStop`.
  - Self-loop guard `is_continuation()` (lines 121–140) suppresses `Stop`/`SubagentStop` re-entries carrying `stop_hook_active`.
  - `_load_handlers()` (lines 178–199) dynamically loads handlers registered in `hooks/handlers.py`'s `HANDLERS` dictionary.
  - Handlers are filtered by `only_on_clients`, executed via `_run_handler()`, and merged via `_merge()` (disposition priority: `REFUSE` > `BLOCK` > `ADVISE`).
  - Renderers (`_render_claude`, `_render_agy`) output the JSON payload.
- **`plugins/rbg/hooks/evaluator_otel_trace.py` lines 143–316**:
  - Emits OTEL spans for RBG rule evaluations to `COPE_EVALUATOR_OTEL_TRACE_PATH` using `FileSpanExporter` and `SimpleSpanProcessor`.
  - Span tracer name: `academicops.rbg.evaluator`; Resource service name: `rbg-evaluator`.
  - Parent context extraction (lines 149–203): `_extract_parent_context()` reads W3C `TRACEPARENT` and `TRACESTATE` from environment.
  - Span status mapping (lines 303–306): `span.set_status(Status(StatusCode.ERROR, description=...))` if `outcome.error` is present.

### Item 3: `SendMessage` & `SubagentStop` Tool Plumbing
- **`lib/hooks/dispatch.py` line 110**: `SubagentStop` is registered as a canonical stop event (`STOP_EVENTS = ("Stop", "SubagentStop")`).
- **`plugins/orchestrate/hooks/handlers.py` line 93**: `SubagentStop` runs `honest_output(ctx)`.
- **`plugins/orchestrate/hooks/handlers.py` line 80**: `rule_against_hearsay(ctx)` checks `ctx.tool_calls` for `Agent` tool calls on `PostToolBatch`.
- `SendMessage` tool calls arrive as tool execution events (`ctx.tool == "SendMessage"` or inside `ctx.tool_calls` on `PostToolBatch` / `PostToolUse`).
- Currently, `SendMessage` does not instrument OTEL parent/target span linkage, and `SubagentStop` does not inspect `ctx.raw` for unsent output state.

### Item 4: Existing OTEL Telemetry Tests
- **`tests/test_telemetry_otel_e2e.py`**: `@pytest.mark.otel_e2e` end-to-end test (`test_native_otel_export_reaches_a_real_collector`). Starts `otel/opentelemetry-collector-contrib:latest` Docker container, sets 15-var `TELEMETRY_ENV` contract, executes a real `claude` session, and asserts `claude_code.*` metrics and `resourceSpans` reach the collector.
- **`tests/test_cope.py` lines 1083–1334**: 14 unit tests covering `evaluator_otel_trace.py`:
  - Resolution (`resolve()`, environment overrides, `CLAUDE_PLUGIN_OPTION_...`).
  - Span generation (one span per rule, OK/ERROR statuses, attributes, duration).
  - Parent context extraction (`TRACEPARENT`/`TRACESTATE` parsing vs fallback fresh root).
  - Sweep ID matching across JSON Lines trace and OTel spans.
  - Dual sink independence & fail-open behavior.
- **`tests/polecat/test_container_config.py` lines 342–360**: Tests `resolve_telemetry({})` and `telemetry:` YAML config resolution.

---

## 2. Logic Chain

1. **`OTEL_RESOURCE_ATTRIBUTES` Injection Logic**:
   - `env_contract.py` defines `TELEMETRY_ENV` including `"OTEL_RESOURCE_ATTRIBUTES"`.
   - In `cli.py`, `run()` receives `session_id`, `project`, and `task`.
   - `OTEL_RESOURCE_ATTRIBUTES` follows standard OTEL key=value comma-separated format (`key1=val1,key2=val2`).
   - Therefore, a helper function `format_otel_resource_attributes(existing, session_id, project, task_id)` should parse any existing attributes string, merge/inject `polecat.session_id=session_id`, `polecat.project=project` (if set), and `polecat.task_id=task_id` (if set), and update `env["OTEL_RESOURCE_ATTRIBUTES"]` before `_build_docker_argv` is called.

2. **Tool Error & Idle/Timeout OTEL Instrumentation Logic**:
   - `dispatch.py` normalizes all incoming client hook payloads into `HookContext`.
   - In `PostToolUse` / `PreToolUse` / `PostToolBatch`, tool execution errors (such as `unknown_tool` or missing MCP tool failures) present in `ctx.raw` or `ctx.tool_calls`.
   - In `Stop` / `SubagentStop`, idle or timeout status flags present in `ctx.raw`.
   - In `evaluator_otel_trace.py` (or a helper module invoked during hook dispatch), OTEL spans should be emitted when these errors/events occur:
     - For `unknown_tool` or missing MCP: record OTEL exception (`span.record_exception(...)`) and set status `StatusCode.ERROR`.
     - For agent idle/timeout: emit span `agent.idle` or `agent.timeout` with appropriate attributes.

3. **`SendMessage` & `SubagentStop` Instrumentation Logic**:
   - `SendMessage` tool calls convey inter-agent communication (parent agent -> subagent).
   - Linking parent and target spans requires extracting `TRACEPARENT` from `HookContext` / environment and creating an OTEL span for `SendMessage` with attributes `parent_agent`, `target_agent`, `session_id`, establishing parent/target span linkage.
   - `SubagentStop` fires when a subagent finishes. Inspecting `ctx.raw` (or transcript state) for unsent output (output generated but not sent back via `SendMessage` to parent) allows detecting orphaned subagent results and emitting appropriate OTEL error/warning spans.

4. **Test Suite Coverage Logic**:
   - `tests/test_telemetry_otel_e2e.py` tests container-level native OTel export against an OTLP collector.
   - `tests/test_cope.py` tests hook-level OTLP JSON span generation.
   - `tests/polecat/test_container_config.py` tests launcher telemetry config resolution.
   - New tests must be added to `tests/polecat/test_container_config.py` (for `polecat.*` resource attribute injection) and `tests/test_cope.py` or a new hook test module (for tool plumbing errors, `SendMessage` span linkage, and `SubagentStop` unsent output checks).

---

## 3. Caveats

- **Read-Only Scope**: This report is produced under read-only investigation constraints. No framework code or test files were modified.
- **Claude Code Native Telemetry Limitations**: Native Claude Code OTEL export relies on closed-source CLI behavior (`CLAUDE_CODE_ENABLE_TELEMETRY`, `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA`, `OTEL_TRACES_EXPORTER=otlp`). Hook-level OTel tracing (`evaluator_otel_trace.py`) operates independently via `FileSpanExporter` in OTLP JSON format.

---

## 4. Conclusion

Requirement R3 implementation requires concrete additions in four areas:

1. **`lib/polecat/env_contract.py` & `lib/polecat/cli.py`**:
   - Add `format_otel_resource_attributes()` helper to `env_contract.py` (or `cli.py`).
   - In `cli.py` `run()`, inject `polecat.session_id`, `polecat.project` (when non-empty), and `polecat.task_id` (when non-empty) into `env["OTEL_RESOURCE_ATTRIBUTES"]`.
   - Also ensure `FORWARDED_ENV` forwards host `OTEL_RESOURCE_ATTRIBUTES` into container environment.

2. **`plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`**:
   - Add OTEL exception recording (`span.record_exception(...)`, `StatusCode.ERROR`) for tool plumbing errors (`unknown_tool`, missing MCP) in `evaluator_otel_trace.py` / hook handlers.
   - Add span emission for agent idle/timeout events on `Stop` / `SubagentStop`.

3. **`SendMessage` & `SubagentStop` Plumbing**:
   - Instrument `SendMessage` tool call handling with OTEL parent/target span linkage via `TRACEPARENT` propagation.
   - Instrument `SubagentStop` handling to inspect `ctx.raw` for unsent output and record status/warning spans when unsent output is detected.

4. **Telemetry Tests**:
   - Extend `tests/polecat/test_container_config.py` to verify `polecat.session_id`, `polecat.project`, and `polecat.task_id` injection into `OTEL_RESOURCE_ATTRIBUTES`.
   - Extend `tests/test_cope.py` to test `unknown_tool` OTEL exception emission, `SendMessage` span linkage, and `SubagentStop` unsent output checks.

---

## 5. Verification Method

### Test Execution Commands
- Run OTEL unit tests:
  ```bash
  uv run pytest tests/test_cope.py -k otel
  ```
- Run polecat container config tests:
  ```bash
  uv run pytest tests/polecat/test_container_config.py
  ```
- Run OTEL E2E collector test (opt-in, requires Docker):
  ```bash
  uv run pytest -m otel_e2e tests/test_telemetry_otel_e2e.py -v
  ```
- Run full test suite:
  ```bash
  make test
  ```

### Invalidation Conditions
- `OTEL_RESOURCE_ATTRIBUTES` in container does not contain `polecat.session_id=<session_id>`.
- Tool execution failures (`unknown_tool`) do not generate `StatusCode.ERROR` or OTEL exception events.
- `SendMessage` tool calls do not preserve parent trace context.
