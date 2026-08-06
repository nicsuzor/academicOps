# Handoff Report: Challenger 1 — Empirical Stress Test of Milestone R3

## Verdict: REJECT

---

## 1. Observation

### 1.1 Test Suite Execution
- Running the existing pytest suite:
  ```bash
  /home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
  ```
  Result: `252 passed, 9 skipped in 11.37s`.

- Running the adversarial stress test suite (`/workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py`):
  ```bash
  /home/worker/.venv/bin/pytest -v /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py
  ```
  Result: `3 failed, 7 passed in 1.22s`.

### 1.2 Identified Bugs & Verbatim Output

#### Bug 1: `format_otel_resource_attributes()` duplicates keys when `existing` contains duplicate entries
- **File**: `lib/polecat/env_contract.py:145-156`
- **Code snippet**:
  ```python
  145:     result_pairs = []
  146:     updated_keys = set()
  147:     for k, v in pairs:
  148:         if k in updates:
  149:             result_pairs.append(f"{k}={updates[k]}")
  150:             updated_keys.add(k)
  151:         else:
  152:             if v != "":
  153:                 result_pairs.append(f"{k}={v}")
  154:             else:
  155:                 result_pairs.append(k)
  ```
- **Test execution & output**:
  ```python
  existing = "polecat.session_id=old_s1,polecat.session_id=old_s2,env=prod"
  res = format_otel_resource_attributes(existing=existing, session_id="new_s", project="proj1", task_id="task1")
  ```
  `AssertionError: Expected polecat.session_id to appear once, got 2: polecat.session_id=new_s,polecat.session_id=new_s,env=prod,polecat.project=proj1,polecat.task_id=task1`

#### Bug 2: `format_otel_resource_attributes()` produces stray comma `","` on malformed empty key-value inputs
- **File**: `lib/polecat/env_contract.py:128-132, 151-152`
- **Code snippet**:
  ```python
  128:             if "=" in item:
  129:                 k, v = item.split("=", 1)
  130:                 pairs.append((k.strip(), v.strip()))
  131:             else:
  132:                 pairs.append((item.strip(), ""))
  ...
  151:         else:
  152:             if v != "":
  153:                 result_pairs.append(f"{k}={v}")
  154:             else:
  155:                 result_pairs.append(k)
  ```
- **Test execution & output**:
  ```python
  res_malformed = format_otel_resource_attributes(existing=", ,, = ,=")
  ```
  `AssertionError: Expected empty string for malformed empty pairs, got ','`

#### Bug 3: `detect_tool_plumbing_error()` fails to inspect `ctx.tool_calls` on `PostToolBatch` events
- **File**: `plugins/rbg/hooks/evaluator_otel_trace.py:254-275`
- **Code snippet**:
  ```python
  254: def detect_tool_plumbing_error(ctx: HookContext) -> tuple[str, str] | None:
  255:     raw = ctx.raw or {}
  256:     err_type = raw.get("error_type") or raw.get("error_code")
  257:     err_msg = raw.get("error_message") or raw.get("error") or ""
  258: 
  259:     if err_type in ("unknown_tool", "missing_mcp"):
  260:         return str(err_type), str(err_msg or err_type)
  261: 
  262:     if ctx.tool in ("unknown_tool", "missing_mcp"):
  263:         return ctx.tool, str(err_msg or ctx.tool)
  ...
  ```
- **Test execution & output**:
  ```python
  ctx_batch = HookContext(
      client="claude",
      event="PostToolBatch",
      tool="",
      tool_calls=({"tool_name": "unknown_tool", "error": "Tool unknown_tool not found"},),
      raw={"tool_calls": [{"tool_name": "unknown_tool", "error": "Tool unknown_tool not found"}]}
  )
  err = evaluator_otel_trace.detect_tool_plumbing_error(ctx_batch)
  ```
  `AssertionError: detect_tool_plumbing_error failed to detect unknown_tool in PostToolBatch tool_calls!`
  `PostToolBatch plumbing error detection result: None`

### 1.3 Confirmed Passing Subsystems
- **OTEL Trace Path Fault Tolerance**: When `COPE_EVALUATOR_OTEL_TRACE_PATH` points to an uncreatable directory (`NotADirectoryError`) or a read-only directory (`0o555`), `dispatch._instrument_otel_events` catches exceptions and fails open without crashing hook dispatch.
- **Traceparent Linkage & Fallback**: `record_send_message` safely handles missing and corrupted `TRACEPARENT` env values (e.g. `invalid-traceparent`, `00-0000...-00`), falling back to fresh valid W3C traceparents.
- **Nested Subagent Span Linkage**: Subagent chains correctly preserve parent trace ID across `SendMessage` calls.
- **SubagentStop Unsent Output Handling**: Unsent output detection and large unsent output payloads (e.g., 5MB string) write safely into OTLP JSON trace files without process failure.

---

## 2. Logic Chain

1. **Observations 1.1 & 1.2 (Bug 1)**: `format_otel_resource_attributes` parses existing key-value pairs into a list `pairs`. During iteration over `pairs`, if key `k` is present in `updates`, it appends `f"{k}={updates[k]}"` to `result_pairs` without checking if `k` has already been updated. When `existing` contains duplicate keys (e.g. `polecat.session_id=old1,polecat.session_id=old2`), the function appends `polecat.session_id=new_s` twice, producing invalid duplicate attributes in `OTEL_RESOURCE_ATTRIBUTES`.
2. **Observations 1.1 & 1.2 (Bug 2)**: When `existing` contains malformed empty pairs like `"="`, `item.split("=", 1)` yields `k=""` and `v=""`. Since `v == ""`, the `else` branch appends `k` (which is `""`) to `result_pairs`. `result_pairs` becomes `["", ""]`. Calling `",".join(["", ""])` produces `","`, corrupting `OTEL_RESOURCE_ATTRIBUTES` with a stray comma.
3. **Observations 1.1 & 1.2 (Bug 3)**: Claude Code emits `PostToolBatch` events where `ctx.tool` is empty (`""`) and tool execution records are placed in `ctx.tool_calls`. `_instrument_otel_events` in `lib/hooks/dispatch.py:343-349` checks `ctx.tool_calls` for `SendMessage`, but `detect_tool_plumbing_error()` in `plugins/rbg/hooks/evaluator_otel_trace.py` only inspects `ctx.tool` and `ctx.raw` top-level keys. As a result, any tool plumbing error (`unknown_tool` or `missing_mcp`) occurring inside a batch tool execution (`PostToolBatch`) is completely missed and fails to emit an OTEL exception span.

---

## 3. Caveats

- **Scope Limit**: The review-only constraint strictly prohibits modifying the implementation code.
- **Environment**: All tests were executed in the provided Linux container environment using Python 3.12.13 and OpenTelemetry SDK libraries.

---

## 4. Conclusion

**Verdict: REJECT**

Milestone R3 fails empirical stress testing due to 3 defects in attribute formatting and tool plumbing error detection:
1. `format_otel_resource_attributes()` duplicates keys when `existing` contains duplicate keys.
2. `format_otel_resource_attributes()` outputs stray commas when `existing` contains empty/malformed pairs.
3. `detect_tool_plumbing_error()` omits checking `ctx.tool_calls`, silently missing tool plumbing errors on `PostToolBatch` events.

---

## 5. Verification Method

Run the adversarial stress test suite to reproduce all 3 failures:
```bash
/home/worker/.venv/bin/pytest -v /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py
```
Expected output:
- `FAILED test_format_otel_duplicate_keys`
- `FAILED test_format_otel_malformed_and_empty`
- `FAILED test_post_tool_batch_plumbing_error_detection`

Run existing test suite:
```bash
/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
```
Expected output: `252 passed, 9 skipped`.
