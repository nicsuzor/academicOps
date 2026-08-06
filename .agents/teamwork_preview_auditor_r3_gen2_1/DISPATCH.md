## 2026-08-06T13:16:49Z
<USER_REQUEST>
You are the Forensic Auditor for Milestone R3 Iteration 2 (OTEL Telemetry Tracing & Error Instrumentation Fixes).
Your working directory is `/workspace/.agents/teamwork_preview_auditor_r3_gen2_1`.
Read `/workspace/.agents/ORIGINAL_REQUEST.md` (Requirement R3) and Worker 4 gen2's report at `/workspace/.agents/teamwork_preview_worker_r3_gen2/handoff.md` before beginning.

Task: Perform forensic integrity verification on all code modified in Milestone R3 Iteration 2 (`lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, `lib/hooks/dispatch.py`).

Integrity Forensics Checks:
1. Check for hardcoded test expectations, dummy implementations, or false positive assertions.
2. Verify that `format_otel_resource_attributes`, tool error recording, `SendMessage` span linkage, and `SubagentStop` unsent output checks execute real logic without short-circuiting or mock bypasses.
3. Verify that ruff lint checks pass cleanly (`/home/worker/.venv/bin/ruff check plugins/rbg/hooks/evaluator_otel_trace.py lib/polecat/env_contract.py`).
4. Run pytest `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` and verify test execution validity.

Deliver your verdict (CLEAN or INTEGRITY_VIOLATION) in `/workspace/.agents/teamwork_preview_auditor_r3_gen2_1/handoff.md` and send a completion message.
</USER_REQUEST>
