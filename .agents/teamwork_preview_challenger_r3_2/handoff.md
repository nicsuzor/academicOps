# Handoff Report: Challenger 2 — Milestone R3 (OTEL Telemetry Tracing & Error Instrumentation)

## 1. Observation

- **`format_otel_resource_attributes()` (`lib/polecat/env_contract.py` & `lib/polecat/cli.py`)**:
  - Implementation accepts `existing`, `session_id`, `project`, and `task_id`.
  - Merges and formats resource attributes into comma-separated `key=value` string.
  - Verified edge cases:
    - Existing attributes without `polecat.` prefix are preserved.
    - Existing `polecat.` keys are updated in-place without duplicate keys or reordering unrelated keys.
    - Valueless keys (e.g. `standalone_flag`) are preserved cleanly.
    - Leading/trailing whitespace and empty string items (e.g. `a=1,, b=2`) are sanitized.
    - Numeric inputs (`session_id=12345`) are stringified without error.
    - Default invocation `format_otel_resource_attributes()` returns `""`.
  - `cli.py` invokes this helper during `run()`, injecting `polecat.session_id`, `polecat.project`, and `polecat.task_id` into container environment `OTEL_RESOURCE_ATTRIBUTES`.

- **OTEL Event Recording (`plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`)**:
  - `detect_tool_plumbing_error(ctx)` accurately detects `unknown_tool` and `missing_mcp` across various `HookContext` payload structures (`raw["error_type"]`, `raw["error_code"]`, `ctx.tool`, `raw["error"]`, `raw["tool_error"]`).
  - `record_tool_plumbing_error(...)` emits `tool.error.<error_type>` spans to OTLP JSON destination, records exception events (`span.record_exception(...)`), and sets `StatusCode.ERROR`.
  - `record_subagent_stop(...)` inspects `SubagentStop` events:
    - When `has_unsent_output` is True: sets `warning: unsent_output_detected` attribute, records exception event, and sets `StatusCode.ERROR`.
    - When clean: sets `StatusCode.OK`.
  - `record_agent_idle_timeout(...)` instruments:
    - `idle`: sets `StatusCode.OK`.
    - `timeout`: sets `StatusCode.ERROR` and records `TimeoutError` exception.
  - `dispatch.py` triggers `_instrument_otel_events(ctx)` automatically on every non-continuation hook invocation.

- **`SendMessage` Linkage & Traceparent Propagation**:
  - `record_send_message(ctx)` extracts W3C `TRACEPARENT` from environment if present.
  - Generates a new `propagated_traceparent` (`00-<trace_id>-<span_id>-01`) retaining the parent `trace_id`.
  - Emits span `agent.send_message` with `parentSpanId` linked to parent span, and sets `parent_agent`, `target_agent`, and `propagated_traceparent` attributes.
  - Unset `TRACEPARENT` gracefully initializes a fresh root span and returns a valid `propagated_traceparent`.

- **Pytest Suite & Adversarial Test Suite Execution**:
  - Existing test suite executed: `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` passed (252 passed, 9 skipped in 11.26s).
  - Custom adversarial unit test suite `/workspace/.agents/teamwork_preview_challenger_r3_2/test_adversarial_r3.py` executed: 5/5 test suites passed.
  - Custom dispatch integration test suite `/workspace/.agents/teamwork_preview_challenger_r3_2/test_dispatch_otel_integration.py` executed: passed.

---

## 2. Logic Chain

1. **Resource Attribute Parsing & In-Place Merge**:
   - `format_otel_resource_attributes` parses existing key-value pairs into a tuple list `(key, value)`.
   - Iterates through existing pairs; if a key matches one of `polecat.session_id`, `polecat.project`, or `polecat.task_id`, the new value replaces the old value while retaining position.
   - Any new polecat attributes not in `existing` are appended at the end.
   - Empirical test `test_format_otel_resource_attributes()` confirmed correct handling across all edge cases (nulls, empty items, whitespace, numeric values, overrides).

2. **Tool Plumbing & Subagent Error Instrumentation**:
   - `detect_tool_plumbing_error` checks error codes and message strings in `ctx.raw` and `ctx.tool`.
   - `record_tool_plumbing_error` uses OpenTelemetry python SDK to create `tool.error.<type>` spans, record exception events, and set `StatusCode.ERROR` (OTLP code 2).
   - `record_subagent_stop` checks `ctx.raw` for unsent output fields. On detection, it attaches warning attributes, records an exception event, and sets `StatusCode.ERROR`.
   - Empirical OTLP JSON parsing in `test_tool_plumbing_errors()` and `test_subagent_stop_unsent_output()` confirmed that spans written to disk contain exact OTLP JSON schema elements (`status.code == 2`, `events[0].name == "exception"`, `warning == "unsent_output_detected"`).

3. **Context Extraction & Traceparent Propagation**:
   - `record_send_message` uses `opentelemetry.trace.propagation.tracecontext.TraceContextTextMapPropagator` to extract existing parent trace context from `TRACEPARENT`.
   - The resulting span inherits `trace_id` and sets `parentSpanId` to the parent span ID.
   - `span.get_span_context()` retrieves the newly generated `span_id` to construct `new_traceparent = f"00-{trace_id:032x}-{span_id:016x}-01"`.
   - Empirical verification in `test_send_message_linkage()` confirmed that `parentSpanId` matches `TRACEPARENT` in environment and `propagated_traceparent` retains the trace ID.

4. **Framework Dispatch Integration**:
   - `dispatch.py` calls `_instrument_otel_events(ctx)` prior to handler execution.
   - End-to-end execution via `test_dispatch_otel_integration.py` verified that sending a `PreToolUse` `SendMessage` payload through `dispatch.py` creates OTLP JSON spans on disk as expected.

---

## 3. Caveats

- Hook-level OTEL tracing requires `COPE_EVALUATOR_OTEL_TRACE_PATH` to be set in the environment; when unset, tracing fails open without error (intended fail-open design).
- Native OpenTelemetry Python SDK components (`opentelemetry.trace`, `opentelemetry.exporter.otlp.json.file`) must be available in python environment (verified present in `/home/worker/.venv`).

---

## 4. Conclusion

Verdict: **APPROVE**

Milestone R3 (OTEL Telemetry Tracing & Error Instrumentation) is fully implemented, conforms to all specifications in `ORIGINAL_REQUEST.md`, and passed all empirical unit, integration, and adversarial stress tests.

---

## 5. Verification Method

Run the following commands to independently verify:

1. Execute the main test suite:
   ```bash
   /home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
   ```
   Expected: 252 passed, 9 skipped.

2. Execute the adversarial test harness:
   ```bash
   /home/worker/.venv/bin/python /workspace/.agents/teamwork_preview_challenger_r3_2/test_adversarial_r3.py
   ```
   Expected: All 5 test suites pass cleanly.

3. Execute the dispatch integration test:
   ```bash
   /home/worker/.venv/bin/python /workspace/.agents/teamwork_preview_challenger_r3_2/test_dispatch_otel_integration.py
   ```
   Expected: `PASS: dispatch.py OTEL integration test passed successfully!`.
