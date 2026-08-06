## 2026-08-06T12:57:06Z
<USER_REQUEST>
You are Worker 3 for Milestone R2: Persistence Verification & Defaults.
Your working directory is `/workspace/.agents/teamwork_preview_worker_r2/`. Create this directory if it doesn't exist.

Read `/workspace/.agents/ORIGINAL_REQUEST.md` carefully. Also read the Phase 0 Explorer 2 handoff report at `/workspace/.agents/teamwork_preview_explorer_phase0_2/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. `lib/polecat/cli.py`:
   - Implement `_verify_transcript_created(session_dir: Path)` helper which checks `.jsonl` transcript existence and counts line events (`event_count`).
   - Call transcript verification prior to writing `run.json`.
   - Update `write_run_record()` to populate `transcript_path`, `transcript_bytes`, and `event_count` in `run.json`.
   - If transcript is 0 bytes or missing (for agent commands `claude`/`agy`), set `status = "degraded"` and append `{"what": "transcript_missing", "why": "..."}` to `degraded[]`.
2. `lib/polecat/env_contract.py`:
   - Add `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to `CONTAINER_SET_ENV` so container invocations set it by default.
3. `tests/polecat/`:
   - Add unit tests in `tests/polecat/test_run_record.py` and `tests/polecat/test_container_config.py` asserting transcript metadata structure, degraded transcript state, and default agent teams env var propagation.
   - Update opt-in E2E container transcript persistence test (`@pytest.mark.e2e`) in `tests/polecat/test_transcript_persistence.py` to assert the new metadata fields.
4. Run tests: Execute `/home/worker/.venv/bin/pytest tests/polecat/` to verify all tests pass.

Write your changes, test results, and handoff report to `/workspace/.agents/teamwork_preview_worker_r2/handoff.md`.
Maintain progress in `/workspace/.agents/teamwork_preview_worker_r2/progress.md`.
When finished, send a message to parent orchestrator.
</USER_REQUEST>
