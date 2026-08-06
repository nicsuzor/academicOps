# Forensic Audit Report — Milestone R3 Iteration 2 (OTEL Telemetry Tracing & Error Instrumentation Fixes)

**Work Product**: `lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, `lib/hooks/dispatch.py`
**Profile**: General Project
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)
**Verdict**: CLEAN

---

## 1. Observation

A full forensic audit was performed across all source files modified in Milestone R3 Iteration 2:

1. **Source Code Verification & Prohibited Pattern Checks**:
   - `lib/polecat/env_contract.py`: `format_otel_resource_attributes()` (lines 109-167) parses existing attribute pairs, filters empty key tokens (`if not k: continue`), updates session, project, and task ID attributes, and deduplicates keys using a `seen_keys` set to enforce 1-occurrence semantics without any hardcoded outputs or short-circuiting.
   - `plugins/rbg/hooks/evaluator_otel_trace.py`:
     - `detect_tool_plumbing_error(ctx)` (lines 218-260) inspects top-level error fields, tool names, and batch tool calls (`PostToolBatch` `ctx.tool_calls`) for `unknown_tool` or `missing_mcp`.
     - `record_tool_plumbing_error()` (lines 263-302) constructs OTEL exception spans with `StatusCode.ERROR`.
     - `record_send_message()` (lines 363-416) extracts recipient targets, links parent/target spans, generates W3C traceparent headers (`00-<trace_id>-<span_id>-01`), and attaches `propagated_traceparent`.
     - `record_subagent_stop()` (lines 418-472) inspects `has_unsent_output`, creates `agent.subagent_stop` spans, and records warning exceptions when unsent output is present.
   - `lib/hooks/dispatch.py`: `_instrument_otel_events()` (lines 325-359) dispatches OTEL instrumentation hooks dynamically across all 4 telemetry categories.
   - `lib/polecat/cli.py`: `_sanitize_path_component()` (lines 805-816) and `run` command invoke resource attribute formatting and transcript evidence checks authentically.

2. **Static Analysis Check**:
   - Command: `/home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py lib/polecat/env_contract.py`
   - Output: `All checks passed!` (0 errors).

3. **Test Suite Verification**:
   - Command: `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py`
   - Result: `252 passed, 9 skipped in 11.59s`.
   - Command: `/home/worker/.venv/bin/pytest -v /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py`
   - Result: `10 passed in 1.34s`.

---

## 2. Logic Chain

1. **Empirical Verification of Logic**:
   Inspection of `format_otel_resource_attributes()` confirms that duplicate keys in `existing` are deduplicated and overridden by updated parameters. Stray/empty keys are cleanly skipped via `if not k: continue`.
   `detect_tool_plumbing_error()` iterates over batch tool calls when `ctx.event == "PostToolBatch"` or `ctx.tool` is empty, closing the detection gap for batch tool plumbing errors.
   `record_send_message()` and `record_subagent_stop()` utilize standard `opentelemetry.trace` APIs to produce valid OTLP JSON spans.
   No facade implementations, hardcoded returns, or mock bypasses exist in any of the modified target functions.

2. **Lint & Test Pass Validation**:
   `ruff check` verifies zero syntax or unused import/redefinition issues (resolving the earlier F811 `sink_for` duplicate definition).
   `pytest` execution succeeds with 252 passed tests in the main suite and 10/10 passed in the challenger adversarial suite, confirming functional correctness.

---

## 3. Caveats

No caveats. All checks were empirically run and independently verified.

---

## 4. Conclusion

The work product delivered in Milestone R3 Iteration 2 is **CLEAN**. There are zero integrity violations, zero hardcoded false positives, and all implementation logic functions authentically.

---

## 5. Verification Method

To independently verify this audit result:

1. **Ruff Lint Check**:
   ```bash
   /home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py lib/polecat/env_contract.py
   ```
   *Expected Output*: `All checks passed!`

2. **Pytest Unit Test Suite**:
   ```bash
   /home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
   ```
   *Expected Output*: `252 passed, 9 skipped`

3. **Challenger Adversarial Test Suite**:
   ```bash
   /home/worker/.venv/bin/pytest -v /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py
   ```
   *Expected Output*: `10 passed`
