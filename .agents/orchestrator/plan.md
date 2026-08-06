# Project Plan — Transcript Generation, Launcher Mechanics & OTEL Telemetry Improvements

## Overview
Implement robust transcript discovery, launcher persistence verification, OpenTelemetry (OTEL) tracing, and a 4-tier transcript artifact system across `lib/py/transcripts/`, `lib/polecat/cli.py`, `lib/polecat/env_contract.py`, and framework hook layers in `academicOps`.

## Milestones & Phasing

### Phase 0: Survey & Initial Exploration
- Spawn 3 parallel `teamwork_preview_explorer` agents to map the codebase, analyze current tests, and verify exact locations/contracts of targeted files.
- Produce unified `PROJECT.md` Feature Inventory & Architecture map.

### Phase 1: Milestone R1 — Discovery & Launcher Path Sanitization
- `lib/py/transcripts/runner.py`: Recursive globbing (`rglob`) for `.jsonl` files excluding `subagents/` and `-hooks.jsonl`.
- `lib/polecat/cli.py`: Sanitize `project` and `session_name` strings.
- Gate: Explorer -> Worker -> Reviewer -> Challenger -> Auditor

### Phase 2: Milestone R2 — Symmetrical Persistence Verification & Environment Defaults
- `lib/polecat/cli.py`: `_verify_transcript_created()` check before writing `run.json`, metadata logging, degraded status handling.
- `lib/polecat/env_contract.py`: Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- `tests/polecat/`: E2E container transcript persistence test `@pytest.mark.e2e`.
- Gate: Explorer -> Worker -> Reviewer -> Challenger -> Auditor

### Phase 3: Milestone R3 — OTEL Telemetry Tracing & Error Instrumentation
- `lib/polecat/env_contract.py` & `lib/polecat/cli.py`: Inject `polecat.session_id`, `polecat.project`, `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES`.
- `plugins/rbg/hooks/evaluator_otel_trace.py` & `lib/hooks/dispatch.py`: Instrument `unknown_tool`, missing MCP, agent idle/timeout events.
- Instrument `SendMessage` parent/target span linkage and check `SubagentStop` for unsent output.
- Gate: Explorer -> Worker -> Reviewer -> Challenger -> Auditor

### Phase 4: Milestone R4 — 4-Tier Transcript System & Renderer Hardening
- `lib/py/transcripts/domain/renderer.py` & `domain/view.py`: Render `.controller.md`, `.full.md`, `.md`, `.html`.
- Escape XML/HTML special characters in outputs/prompts.
- Collapsible `<details><summary>` wrapping for large tool outputs.
- `adapters/claude.py`: Subagent sidechain inlining & unlinked subagent fallback.
- Inter-agent message deduplication, `controller_tokens` vs `subagent_tokens` separation.
- Non-contiguous `step_index` handling without false data-loss warnings.
- Gate: Explorer -> Worker -> Reviewer -> Challenger -> Auditor

### Phase 5: Milestone R5 — Testing, Commit, Push & PR Creation
- Run full pytest test suite (`tests/transcripts/`, `tests/polecat/`, all pytest suites).
- Commit changes to git branch, push to remote, open Pull Request.
- Notify Sentinel / Parent.

## Verification & Quality Gates
- Every iteration must pass unit, integration, and E2E tests.
- Every milestone requires 2 Reviewers (APPROVE), 2 Challengers (APPROVE), and 1 Auditor (CLEAN).
