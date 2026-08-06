## 2026-08-06T12:42:54Z

<USER_REQUEST>
You are Explorer 2 for Phase 0 Survey.
Your working directory is `/workspace/.agents/teamwork_preview_explorer_phase0_2/`. Create this directory if it doesn't exist.

Read `/workspace/.agents/ORIGINAL_REQUEST.md` carefully.

Your Focus: Polecat Launcher Mechanics, Persistence Verification & Defaults (Requirements R1 and R2).
Investigate:
1. `lib/polecat/cli.py`: Inspect how `project` and `session_name` strings are handled and where sanitization is needed to prevent directory hierarchy corruption. Where should `_verify_transcript_created()` be added prior to writing `run.json`? How is `run.json` created, and how should metadata (`transcript_path`, `transcript_bytes`, `event_count`) and degraded status (`transcript_missing` in `degraded[]`) be structured?
2. `lib/polecat/env_contract.py`: Where should `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` be set by default? What environment variables and contracts are defined here?
3. `tests/polecat/`: Examine existing tests under `tests/polecat/`. How can we re-introduce an opt-in E2E container transcript persistence test (`@pytest.mark.e2e`)?

Perform all necessary code analysis, verify exact line numbers and functions.
Write your complete findings and handoff report to `/workspace/.agents/teamwork_preview_explorer_phase0_2/handoff.md`.
Include your progress in `/workspace/.agents/teamwork_preview_explorer_phase0_2/progress.md`.
When finished, send a message to parent orchestrator referencing your handoff report.
</USER_REQUEST>
