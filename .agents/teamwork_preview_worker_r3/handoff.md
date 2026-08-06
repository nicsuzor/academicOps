# Handoff Report: Worker 4 — OTEL Telemetry Tracing & Error Instrumentation (Milestone R3)

## 1. Observation

- **`lib/polecat/env_contract.py` & `lib/polecat/cli.py`**: Added `format_otel_resource_attributes(existing, session_id, project, task_id)` helper function to `env_contract.py` (re-exported in `cli.py`). In `cli.py` `run()`, `env["OTEL_RESOURCE_ATTRIBUTES"]` is updated before launching container, injecting `polecat.session_id=session_id`, `polecat.project=project` (if set), and `polecat.task_id=task_id` (if set).
- **`plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`**:
  - Implemented `detect_tool_plumbing_error(ctx)` and `record_tool_plumbing_error(ctx, error_type, error_message, config)` to record OTEL exception events via `span.record_exception(...)` and set `StatusCode.ERROR` for tool plumbing failures (`unknown_tool`, missing MCP).
  - Implemented `detect_agent_idle_timeout(ctx)` and `record_agent_idle_timeout(ctx, event_type, details, config)` to record agent idle/timeout events on `Stop` / `SubagentStop`.
  - Implemented `record_send_message(ctx, target_agent, parent_agent, config)` to link parent and target spans via W3C `TRACEPARENT` propagation and emit `agent.send_message` spans with `parent_agent` and `target_agent` attributes.
  - Implemented `record_subagent_stop(ctx, has_unsent_output, unsent_content, config)` to inspect `SubagentStop` events for unsent output, recording warning attributes (`warning: unsent_output_detected`), exception events, and `StatusCode.ERROR` when unsent output is present.
  - Integrated `_instrument_otel_events(ctx)` into `dispatch.py` main execution path.
- **`plugins/rbg/hooks/handlers.py`**:
  - Restored `HANDLERS` dictionary entries for `PreToolUse`, `UserPromptSubmit`, `Stop`, and `SubagentStop`.
- **Unit Tests**:
  - Added resource attribute injection unit tests in `tests/polecat/test_container_config.py` (`test_format_otel_resource_attributes_merges_session_project_task`, `test_format_otel_resource_attributes_handles_empty_existing_and_optional_fields`, `test_format_otel_resource_attributes_overrides_existing_polecat_keys`, `test_run_injects_polecat_otel_resource_attributes`).
  - Added OTEL instrumentation unit tests in `tests/test_cope.py` (`test_otel_tool_plumbing_error_recording`, `test_otel_send_message_span_linkage`, `test_otel_subagent_stop_unsent_output_check`, `test_otel_agent_idle_timeout_recording`).

---

## 2. Logic Chain

1. **Resource Attributes Injection**:
   - `format_otel_resource_attributes` parses existing key-value pairs from `OTEL_RESOURCE_ATTRIBUTES`, merges/updates `polecat.session_id`, `polecat.project`, and `polecat.task_id`, and formats back to standard OTEL comma-separated key=value format.
   - `cli.py`'s `run()` function invokes this helper so inner agent processes inherit container execution context.

2. **Tool Plumbing & Stop Event Instrumentation**:
   - `evaluator_otel_trace.py` exposes helper functions (`record_tool_plumbing_error`, `record_send_message`, `record_subagent_stop`, `record_agent_idle_timeout`) backed by OTLP JSON `FileSpanExporter` using `SimpleSpanProcessor`.
   - `dispatch.py` normalizes incoming client events into `HookContext` and automatically triggers `_instrument_otel_events(ctx)` when `COPE_EVALUATOR_OTEL_TRACE_PATH` is configured.
   - `record_send_message` extracts W3C `TRACEPARENT` from environment, links the span context, and formats the new `propagated_traceparent` for subagents.
   - `record_subagent_stop` checks `ctx.raw` for unsent output markers, recording error status and exception events on unsent output.

3. **Test Suite Verification**:
   - All tests in `tests/polecat/` and `tests/test_cope.py` pass cleanly (252 passed, 9 skipped).

---

## 3. Caveats

- **Optional Environment Enablement**: Hook-level OTEL tracing requires `COPE_EVALUATOR_OTEL_TRACE_PATH` to be configured in environment (fail-open when unset).

---

## 4. Conclusion

Milestone R3 is fully implemented across all 4 specified files and thoroughly tested with genuine unit test suites. All requirements are satisfied.

---

## 5. Verification Method

- Run pytest across polecat and cope test suites:
  ```bash
  /home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
  ```
  Expected output: 252 passed, 9 skipped.
