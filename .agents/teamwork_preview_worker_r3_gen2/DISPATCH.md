## 2026-08-06T23:14:00Z

<USER_REQUEST>
You are Worker 4 (gen2) for Milestone R3 (OTEL Telemetry Tracing & Error Instrumentation Fixes).
Your working directory is `/workspace/.agents/teamwork_preview_worker_r3_gen2`.
Read `/workspace/.agents/ORIGINAL_REQUEST.md` (Requirement R3), `/workspace/.agents/teamwork_preview_challenger_r3_1/handoff.md`, and `/workspace/.agents/teamwork_preview_auditor_r3_1/handoff.md` before starting.

Task: Fix the 4 issues identified during Milestone R3 Iteration 1 Gate Verification:

1. `format_otel_resource_attributes()` duplicate key bug:
   In `lib/polecat/env_contract.py`, fix `format_otel_resource_attributes()` to deduplicate key occurrences in `existing` string. When updating keys (or parsing existing attributes), track seen/updated keys so that duplicate keys in `existing` are updated once and not duplicated in the output string.

2. `format_otel_resource_attributes()` stray comma bug:
   In `lib/polecat/env_contract.py`, fix `format_otel_resource_attributes()` handling of empty or malformed pairs (e.g. `","` or `"="`). Ensure that empty keys are ignored and no stray commas or trailing/leading commas are output.

3. `detect_tool_plumbing_error()` missing `PostToolBatch` `ctx.tool_calls` check:
   In `plugins/rbg/hooks/evaluator_otel_trace.py`, update `detect_tool_plumbing_error(ctx)` to inspect `ctx.tool_calls` when `ctx.event == "PostToolBatch"` or `ctx.tool` is empty, detecting `unknown_tool` and `missing_mcp` error types or tool names within batch tool executions.

4. Resolve duplicate function definition (ruff F811):
   In `plugins/rbg/hooks/evaluator_otel_trace.py`, remove/consolidate the duplicate `sink_for` definition (line 205 vs 489) to resolve ruff lint error `F811`.

5. Verification:
   Run unit tests: `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py`
   Run Challenger 1 adversarial tests: `/home/worker/.venv/bin/pytest /workspace/.agents/teamwork_preview_challenger_r3_1/test_adversarial_r3.py`
   Ensure all tests pass 100%.

Deliver your handoff report to `/workspace/.agents/teamwork_preview_worker_r3_gen2/handoff.md` and send a completion message when finished.
</USER_REQUEST>
