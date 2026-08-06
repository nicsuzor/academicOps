# Handoff Report: Reviewer 2 — Milestone R3 Review (OTEL Telemetry Tracing & Error Instrumentation)

## 1. Observation

- **`lib/polecat/env_contract.py`**: Added `format_otel_resource_attributes(existing, session_id, project, task_id)` (lines 109–159). It parses standard comma-separated key=value OTEL attribute strings and merges `polecat.session_id`, `polecat.project`, and `polecat.task_id` without corrupting existing user attributes.
- **`lib/polecat/cli.py`**: In `run()` (lines 1329–1334), `env["OTEL_RESOURCE_ATTRIBUTES"]` is dynamically formatted using sanitized `session_id`, `project`, and `task` parameters before container launch.
- **`plugins/rbg/hooks/evaluator_otel_trace.py`**:
  - Implemented `detect_tool_plumbing_error(ctx)` and `record_tool_plumbing_error(ctx, error_type, error_message, config)` (lines 254–317) to capture `unknown_tool` and `missing_mcp` errors, creating OTEL spans with exception events and `StatusCode.ERROR`.
  - Implemented `detect_agent_idle_timeout(ctx)` and `record_agent_idle_timeout(ctx, event_type, details, config)` (lines 319–375) to record `agent.idle` (StatusCode.OK) and `agent.timeout` (TimeoutError exception and StatusCode.ERROR) on `Stop` and `SubagentStop` events.
  - Implemented `record_send_message(ctx, target_agent, parent_agent, config)` (lines 378–431) to link spans using W3C `TRACEPARENT` propagation and output `agent.send_message` spans containing `target_agent`, `parent_agent`, and `propagated_traceparent` attributes.
  - Implemented `record_subagent_stop(ctx, has_unsent_output, unsent_content, config)` (lines 433–487) to inspect `SubagentStop` events, recording warning attribute (`warning: unsent_output_detected`), exception events, and `StatusCode.ERROR` when unsent output is present.
- **`lib/hooks/dispatch.py`**: Integrated `_instrument_otel_events(ctx)` (lines 325–360) directly into `main()`, executing automated instrumentation on every normalized hook event.
- **Test Suite Execution**: Executed `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py`. Output: **252 passed, 9 skipped in 11.30s**.

---

## 2. Logic Chain

1. **Verification of Resource Attribute Merging**:
   - `format_otel_resource_attributes` accurately handles `None`, empty string, existing attributes, and key overrides.
   - Container process execution receives proper `OTEL_RESOURCE_ATTRIBUTES` formatted env vars with `polecat.session_id`, `polecat.project`, and `polecat.task_id`.

2. **Verification of OTEL Tracing & Error Instrumentation**:
   - `evaluator_otel_trace.py` cleanly integrates OTLP JSON `FileSpanExporter` using `SimpleSpanProcessor`.
   - Tool plumbing errors (`unknown_tool`, `missing_mcp`) are accurately detected and recorded as spans with exception events.
   - W3C `TRACEPARENT` extraction and generation of `propagated_traceparent` correctly links parent-subagent message spans.
   - `SubagentStop` checks inspect for unsent content and correctly tag `StatusCode.ERROR` and `warning` attributes when output is left unsent.
   - Fail-open contract is maintained: unconfigured tracing or write failures on trace paths never crash the tool call or process.

3. **Integrity & Quality Check**:
   - Code changes contain no hardcoded test values, facade implementations, or bypassed verification steps.
   - All unit tests in `tests/polecat/test_container_config.py` and `tests/test_cope.py` pass cleanly.

---

## 3. Caveats

- **Fail-Open by Design**: OTLP file export is active when `COPE_EVALUATOR_OTEL_TRACE_PATH` is set in the environment. If unset, instrumentation calls return immediately without side effects.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone R3 is correctly implemented, robustly engineered, and fully verified by unit tests. All requirements specified in Requirement R3 are completely satisfied.

---

## 5. Verification Method

To independently verify the test suite:
```bash
/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
```
Expected result: `252 passed, 9 skipped`.
