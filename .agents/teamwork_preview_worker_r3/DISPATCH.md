## 2026-08-06T13:03:46Z
You are Worker 4 (Milestone R3 Implementation Worker).
Your working directory is `/workspace/.agents/teamwork_preview_worker_r3`.
Read `/workspace/.agents/ORIGINAL_REQUEST.md` (Requirement R3) and `/workspace/.agents/teamwork_preview_explorer_phase0_3/handoff.md` before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task: Implement Milestone R3 (OTEL Telemetry Tracing & Error Instrumentation) across `lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, and `lib/hooks/dispatch.py`.

Key Requirements:
1. `lib/polecat/env_contract.py` & `lib/polecat/cli.py`:
   - Inject `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`.
   - Add/update helper `format_otel_resource_attributes(existing, session_id, project, task_id)` in `env_contract.py` or `cli.py` to parse any existing attribute string, merge/inject `polecat.session_id=session_id`, `polecat.project=project` (if set), and `polecat.task_id=task_id` (if set).
   - In `cli.py` `run()`, update `env["OTEL_RESOURCE_ATTRIBUTES"]` before launching container.
2. `plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`:
   - Instrument tool plumbing errors (`unknown_tool`, missing MCP) with OTEL exception events (`span.record_exception(...)`) and `StatusCode.ERROR`.
   - Instrument agent idle/timeout events on `Stop` / `SubagentStop` events to emit appropriate OTEL spans/attributes.
3. `SendMessage` & `SubagentStop` Plumbing:
   - Instrument `SendMessage` tool calls with parent/target span linkage (propagating `TRACEPARENT`/span context).
   - Instrument `SubagentStop` event handling to inspect for unsent output and record status/warning spans when unsent output is detected.
4. Unit Tests & Verification:
   - Add unit tests in `tests/polecat/test_container_config.py` verifying `polecat.session_id`, `polecat.project`, and `polecat.task_id` injection into `OTEL_RESOURCE_ATTRIBUTES`.
   - Add unit tests in `tests/test_cope.py` verifying tool plumbing error instrumentation, `SendMessage` span linkage, and `SubagentStop` unsent output checks.
   - Run pytest using `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` to confirm all tests pass cleanly.

Deliver your handoff report to `/workspace/.agents/teamwork_preview_worker_r3/handoff.md` and send a completion message when finished.
