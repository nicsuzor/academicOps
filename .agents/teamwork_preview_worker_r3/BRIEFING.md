# BRIEFING — 2026-08-06T13:03:52Z

## Mission
Implement Milestone R3: OTEL Telemetry Tracing & Error Instrumentation across polecat CLI/env_contract, evaluator_otel_trace, and lib/hooks/dispatch.py, with comprehensive unit tests.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: /workspace/.agents/teamwork_preview_worker_r3
- Original parent: f7a35942-8a06-48ea-ac09-2f9e931a7a41
- Milestone: R3

## 🔒 Key Constraints
- Genuine implementation required (no hardcoding, facade outputs, or cheating).
- Must run `/home/worker/.venv/bin/pytest tests/polecat/ tests/test_cope.py` to confirm all tests pass cleanly.
- Must deliver handoff report to `/workspace/.agents/teamwork_preview_worker_r3/handoff.md` and message caller when finished.

## Current Parent
- Conversation ID: f7a35942-8a06-48ea-ac09-2f9e931a7a41
- Updated: 2026-08-06T13:03:52Z

## Task Summary
- **What to build**:
  1. `lib/polecat/env_contract.py` & `lib/polecat/cli.py`: helper `format_otel_resource_attributes` merging/injecting `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`. Update `run()` in `cli.py`.
  2. `plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`: Instrument tool plumbing errors (`unknown_tool`, missing MCP) with `span.record_exception(...)` and `StatusCode.ERROR`. Instrument idle/timeout events on `Stop` / `SubagentStop`.
  3. `SendMessage` & `SubagentStop` Plumbing: Link parent/target span (`TRACEPARENT` / span context) on `SendMessage`, inspect for unsent output on `SubagentStop` and record status/warning spans.
  4. Unit Tests in `tests/polecat/test_container_config.py` and `tests/test_cope.py`.
- **Success criteria**: All tests pass cleanly, no regressions, complete handoff report.

## Change Tracker
- **Files modified**:
  - `lib/polecat/env_contract.py`: added `format_otel_resource_attributes` helper
  - `lib/polecat/cli.py`: imported `format_otel_resource_attributes` and updated `run()` to inject `OTEL_RESOURCE_ATTRIBUTES`
  - `plugins/rbg/hooks/evaluator_otel_trace.py`: added OTEL instrumentation functions for tool plumbing errors, idle/timeout, SendMessage span linkage, and SubagentStop unsent output
  - `lib/hooks/dispatch.py`: added `_instrument_otel_events` to dispatch OTEL events automatically on hook calls
  - `plugins/rbg/hooks/handlers.py`: restored `HANDLERS` dictionary mapping
  - `tests/polecat/test_container_config.py`: added unit tests for `format_otel_resource_attributes` and container config OTEL resource attribute injection
  - `tests/test_cope.py`: added unit tests for tool error recording, SendMessage span linkage, SubagentStop unsent output, and idle/timeout events
- **Build status**: 252 passed, 9 skipped cleanly
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (252 passed, 9 skipped via pytest)
- **Lint status**: Clean
- **Tests added/modified**: 8 new unit tests across test_container_config.py and test_cope.py

## Loaded Skills
- None
