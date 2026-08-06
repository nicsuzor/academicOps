# Handoff Report: Worker 4 (gen2) — Milestone R3 Fixes

## 1. Observation

All 4 issues identified during Milestone R3 Iteration 1 Gate Verification have been resolved and verified.

### 1.1 Fix 1: `format_otel_resource_attributes()` Duplicate Key Bug
- **File**: `lib/polecat/env_contract.py:109-160`
- **Observation**: Previously, iterating over `pairs` parsed from `existing` would append `f"{k}={updates[k]}"` for each occurrence of key `k` without checking if `k` was already processed, resulting in duplicate attributes when `existing` contained repeated keys (e.g. `polecat.session_id=old_s1,polecat.session_id=old_s2`).
- **Fix Implemented**: Updated `format_otel_resource_attributes()` to maintain a `seen_keys` set while iterating through `pairs` and `updates`. Keys present in `seen_keys` are skipped, ensuring that any key (including duplicate occurrences in `existing`) is updated/emitted exactly once.

### 1.2 Fix 2: `format_otel_resource_attributes()` Stray Comma Bug
- **File**: `lib/polecat/env_contract.py:124-138`
- **Observation**: Malformed empty pairs in `existing` like `","` or `"="` produced empty key strings `k = ""` which were appended to `result_pairs`, leading to stray commas or leading/trailing commas (e.g. `","`).
- **Fix Implemented**: Added explicit validation `if not k: continue` after stripping keys and values when parsing `existing`. In addition, updated optional parameter checks to ignore empty/blank string inputs (`str(val).strip() != ""`), preventing empty keys or stray commas from being generated.

### 1.3 Fix 3: `detect_tool_plumbing_error()` Missing `PostToolBatch` `ctx.tool_calls` Inspection
- **File**: `plugins/rbg/hooks/evaluator_otel_trace.py:274-294`
- **Observation**: `detect_tool_plumbing_error(ctx)` only checked `ctx.tool` and `ctx.raw` top-level keys. Batch tool execution events (`PostToolBatch`) place individual tool execution records inside `ctx.tool_calls` with `ctx.tool == ""`, causing `unknown_tool` and `missing_mcp` plumbing errors inside batch executions to be silently ignored.
- **Fix Implemented**: Updated `detect_tool_plumbing_error(ctx)` to inspect `ctx.tool_calls` (and `raw["tool_calls"]`) when `ctx.event == "PostToolBatch"`, `ctx.tool` is empty, or `tool_calls` are present. It iterates over batch calls and checks for `unknown_tool` or `missing_mcp` error types, tool names, or error messages.

### 1.4 Fix 4: Resolution of Duplicate Function Definition (ruff F811)
- **File**: `plugins/rbg/hooks/evaluator_otel_trace.py:205-239`, `474-530`
- **Observation**: `sink_for()` had a truncated definition at line 205-239 and a second definition at line 489, causing `ruff` lint error `F811 Redefinition of unused sink_for from line 205`.
- **Fix Implemented**: Removed the truncated `sink_for` definition at line 205, kept `_get_tracer()` cleanly in place, and consolidated the full function implementation with complete docstrings into a single `sink_for` definition. `ruff check` now reports 0 errors ("All checks passed!").

---

## 2. Logic Chain

1. **Deduplication in `format_otel_resource_attributes()`**:
   By using `seen_keys = set()`, any key present in `pairs` is processed at its first appearance. If it exists in `updates`, the updated key-value pair is appended and `seen_keys.add(k)` is recorded; subsequent occurrences of `k` in `pairs` hit `if k in seen_keys: continue` and are discarded. Unseen update keys are then appended once at the end. This guarantees exact 1-occurrence property for every resource attribute key.

2. **Malformed Pair Handling in `format_otel_resource_attributes()`**:
   Splitting `"="` yields `k = ""` and `v = ""`. Checking `if not k: continue` filters out all empty-key entries during parsing. Furthermore, when `session_id`, `project`, or `task_id` are empty strings, `str(val).strip() != ""` prevents adding blank update entries. `result_pairs` contains only non-empty, valid key-value pairs, eliminating stray commas.

3. **`PostToolBatch` Plumbing Error Detection**:
   In Claude Code, `PostToolBatch` events set `ctx.tool = ""` and pack tool calls into `ctx.tool_calls = ({"tool_name": "unknown_tool", ...}, ...)`. By extending `detect_tool_plumbing_error` to iterate over `ctx.tool_calls` and inspect `tool_name`, `error_type`, `error_code`, `error`, and `tool_error`, batch plumbing errors are detected and returned as `(error_type, error_message)` to emit OTEL exception spans.

4. **Lint Resolution**:
   Consolidating the duplicate `sink_for` into a single function definition with docstrings resolves `F811` and eliminates dead code.

---

## 3. Caveats

- No caveats. All changes are minimal, genuine implementations directly addressing the 4 root causes identified during iteration 1 gate verification.

---

## 4. Conclusion

All 4 issues are completely fixed. The code passes all static lint checks (`ruff check`), all unit tests (`pytest tests/polecat/ tests/test_cope.py`), and all Challenger 1 adversarial tests (`pytest test_adversarial_r3.py`) with a 100% pass rate.

---

## 5. Verification Method

Independent forensic auditor / challenger verification:

1. **Run Unit Tests**:
   ```bash
   /home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py
   ```
   *Expected Output*: `252 passed, 9 skipped`

2. **Run Challenger 1 Adversarial Tests**:
   ```bash
   /home/worker/.venv/bin/pytest -v /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py
   ```
   *Expected Output*: `10 passed`

3. **Run Ruff Lint Check**:
   ```bash
   /home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py lib/polecat/env_contract.py
   ```
   *Expected Output*: `All checks passed!`
