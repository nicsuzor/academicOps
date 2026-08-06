## 2026-08-06T23:10:17Z
You are Reviewer 1 for Milestone R3 (OTEL Telemetry Tracing & Error Instrumentation).
Your working directory is `/workspace/.agents/teamwork_preview_reviewer_r3_1`.
Read `/workspace/.agents/ORIGINAL_REQUEST.md` (Requirement R3) and Worker 4's report at `/workspace/.agents/teamwork_preview_worker_r3/handoff.md` before beginning.

Task: Review the implementation of Milestone R3 across:
- `lib/polecat/env_contract.py` & `lib/polecat/cli.py`: Injection of `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`.
- `plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`: Instrumentation of tool errors (`unknown_tool`, missing MCP), agent idle/timeout events, `SendMessage` span linkage, and `SubagentStop` unsent output checks.
- Unit tests in `tests/polecat/test_container_config.py` and `tests/test_cope.py`.

Requirements:
1. Examine code changes for correctness, edge cases, error handling, and performance.
2. Execute build/test suite using `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py`.
3. Provide your verdict: APPROVE or REQUEST_CHANGES in your handoff report (`/workspace/.agents/teamwork_preview_reviewer_r3_1/handoff.md`) and send a completion message.
