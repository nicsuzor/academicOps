## 2026-08-06T12:43:00Z

<USER_REQUEST>
You are Explorer 3 for Phase 0 Survey.
Your working directory is `/workspace/.agents/teamwork_preview_explorer_phase0_3/`. Create this directory if it doesn't exist.

Read `/workspace/.agents/ORIGINAL_REQUEST.md` carefully.

Your Focus: OpenTelemetry (OTEL) Telemetry & Tracing (Requirement R3).
Investigate:
1. `lib/polecat/env_contract.py` and `lib/polecat/cli.py`: Where and how are `OTEL_RESOURCE_ATTRIBUTES` configured? How to inject `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`?
2. `plugins/rbg/hooks/evaluator_otel_trace.py` and `lib/hooks/dispatch.py`: How are hooks registered and dispatched? Where are tool plumbing errors (`unknown_tool`, missing MCP) and agent idle/timeout events handled? How should OTEL exception/span events be emitted?
3. `SendMessage` & `SubagentStop` tool plumbing: Where are `SendMessage` tool calls processed? How to instrument parent/target span linkage? Where is `SubagentStop` handled, and how to check for unsent output?
4. Existing telemetry tests: What tests exist for OTEL tracing in the repo?

Perform all necessary code analysis, verify exact line numbers and functions.
Write your complete findings and handoff report to `/workspace/.agents/teamwork_preview_explorer_phase0_3/handoff.md`.
Include your progress in `/workspace/.agents/teamwork_preview_explorer_phase0_3/progress.md`.
When finished, send a message to parent orchestrator referencing your handoff report.
</USER_REQUEST>
