# BRIEFING — 2026-08-06T23:16:30Z

## Mission
Fix 4 issues in OTEL Telemetry Tracing & Error Instrumentation for Milestone R3 and ensure 100% pass rate on unit tests and Challenger 1 adversarial tests.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: /workspace/.agents/teamwork_preview_worker_r3_gen2
- Original parent: f7a35942-8a06-48ea-ac09-2f9e931a7a41
- Milestone: R3

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- Fix 4 specific issues in `lib/polecat/env_contract.py` and `plugins/rbg/hooks/evaluator_otel_trace.py`.
- Ensure all tests pass 100% (unit tests + adversarial tests).
- Resolve ruff F811 lint error.

## Current Parent
- Conversation ID: f7a35942-8a06-48ea-ac09-2f9e931a7a41
- Updated: 2026-08-06T23:16:30Z

## Task Summary
- **What to build**: Fix format_otel_resource_attributes duplicate key bug, stray comma bug, PostToolBatch plumbing error detection, and ruff F811 duplicate sink_for definition.
- **Success criteria**: pytest tests/polecat/ tests/test_cope.py passes (252 passed, 9 skipped), pytest test_adversarial_r3.py passes (10 passed), ruff check passes.
- **Interface contracts**: lib/polecat/env_contract.py and plugins/rbg/hooks/evaluator_otel_trace.py.
- **Code layout**: lib/polecat, plugins/rbg/hooks.

## Key Decisions Made
- Updated `format_otel_resource_attributes()` to use `seen_keys` tracking for deduplication and filter empty keys.
- Updated `detect_tool_plumbing_error()` to iterate through `ctx.tool_calls` when `ctx.event == "PostToolBatch"` or `ctx.tool` is empty.
- Consolidated duplicate `sink_for()` in `evaluator_otel_trace.py` to fix ruff F811 lint error.

## Artifact Index
- /workspace/.agents/teamwork_preview_worker_r3_gen2/DISPATCH.md — Dispatch instructions
- /workspace/.agents/teamwork_preview_worker_r3_gen2/BRIEFING.md — Briefing memory
- /workspace/.agents/teamwork_preview_worker_r3_gen2/handoff.md — Handoff report

## Change Tracker
- **Files modified**: `lib/polecat/env_contract.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`
- **Build status**: PASS (252 passed, 9 skipped unit tests; 10 passed adversarial tests; ruff clean)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (100%)
- **Lint status**: PASS (0 errors)
- **Tests added/modified**: Verified against adversarial test suite

## Loaded Skills
None
