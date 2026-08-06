# Forensic Audit Report: Milestone R3 — OTEL Telemetry Tracing & Error Instrumentation

**Work Product**: Milestone R3 (`lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, `lib/hooks/dispatch.py`, `tests/polecat/test_container_config.py`, `tests/test_cope.py`)  
**Profile**: General Project  
**Verdict**: INTEGRITY_VIOLATION  

---

## 1. Observation

- **`lib/polecat/env_contract.py` & `lib/polecat/cli.py`**:
  `format_otel_resource_attributes` properly parses and merges `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`. `cli.py` invokes this helper before launching container processes.
- **`plugins/rbg/hooks/evaluator_otel_trace.py`**:
  Helper functions `detect_tool_plumbing_error`, `record_tool_plumbing_error`, `detect_agent_idle_timeout`, `record_agent_idle_timeout`, `record_send_message`, and `record_subagent_stop` implement OpenTelemetry tracing.
- **`lib/hooks/dispatch.py`**:
  `_instrument_otel_events` integrates OTEL tracing into hook execution.
- **Pytest Execution**:
  `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` passed with 252 passed and 9 skipped.
- **Lint Verification / Code Corruption Check**:
  Running `/home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py` revealed a critical lint error and structural flaw:
  `F811 Redefinition of unused sink_for from line 205`
  Direct inspection of `plugins/rbg/hooks/evaluator_otel_trace.py` showed that lines 205–239 contain a truncated `def sink_for(...)` function definition:
  ```python
  205: def sink_for(
  206:     config: Config | None,
  ...
  238:     if config is None:
  239:         return None
  240: 
  241: def _get_tracer(config: Config):
  ```
  `def sink_for` is then redefined at line 489. This leaves a dead, truncated function definition in the source file.

---

## 2. Logic Chain

1. **Check 1: Hardcoded test expectations, dummy implementations, or false positive assertions**:
   - Result: **PASS**. Source code uses dynamic dictionary parsing and real OpenTelemetry SDK objects (`TracerProvider`, `SimpleSpanProcessor`, `FileSpanExporter`).
2. **Check 2: Real logic execution verification**:
   - Result: **PASS**. `format_otel_resource_attributes`, tool plumbing error recording, SendMessage span linkage with W3C traceparent propagation, and SubagentStop unsent output checks execute real logic.
3. **Check 3: Pytest execution validity**:
   - Result: **PASS**. Command `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` completed with 252 passed, 9 skipped.
4. **Check 4: Leftover temporary files, lint issues, or unintended side effects**:
   - Result: **FAIL**. `ruff` check identified error `F811` in `plugins/rbg/hooks/evaluator_otel_trace.py` due to a truncated function definition at line 205 and a redefinition at line 489.

Under the Integrity Forensics framework, if ANY check fails, the verdict must be `INTEGRITY_VIOLATION` and the work product must be rejected.

---

## 3. Caveats

- The core functional logic and unit tests pass when executed, but the source file `plugins/rbg/hooks/evaluator_otel_trace.py` carries a syntax/structural defect due to the duplicated and truncated function definition.

---

## 4. Conclusion

**Verdict**: **INTEGRITY_VIOLATION**

Milestone R3 is rejected due to a failure on Check 4 (Lint and code structure verification). `plugins/rbg/hooks/evaluator_otel_trace.py` contains a duplicate, truncated function definition (`sink_for` at line 205 vs line 489), causing lint error `F811`.

---

## 5. Verification Method

To independently verify this finding:
1. Run ruff on the modified file:
   ```bash
   /home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py
   ```
   Observed output: `F811 Redefinition of unused sink_for from line 205`
2. View lines 205–241 of `plugins/rbg/hooks/evaluator_otel_trace.py` to confirm the truncated function body.
