## 2026-08-06T12:45:32Z

<USER_REQUEST>
You are Worker 1 for Milestone R1: Discovery & Launcher Path Sanitization.
Your working directory is `/workspace/.agents/teamwork_preview_worker_r1/`. Create this directory if it doesn't exist.

Read `/workspace/.agents/ORIGINAL_REQUEST.md` carefully. Also read the Phase 0 Explorer handoff reports at `/workspace/.agents/teamwork_preview_explorer_phase0_1/handoff.md` and `/workspace/.agents/teamwork_preview_explorer_phase0_2/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. `lib/py/transcripts/runner.py`: Refactor `find_session_files()` to search recursively using `rglob("*.jsonl")` (or `glob("**/*.jsonl")`) for session files across `$AOPS_SESSIONS/logs/`, `~/.claude/projects/`, and agy directories. Ensure paths matching `subagents/` subdirectories (e.g. `"subagents" in p.parts`) or `-hooks.jsonl` files are strictly filtered out.
2. `lib/polecat/cli.py`: Implement input sanitization for `project` and `session_name` inputs (e.g. `_sanitize_path_component()`) to prevent directory hierarchy corruption, path traversal (`..`, `/`, `\`), or invalid container name characters before path and container name resolution occurs in `run()`.
3. Tests: Write comprehensive unit tests in `tests/transcripts/test_polecat_discovery.py` and `tests/polecat/test_workspace_isolation.py` (or `tests/polecat/test_cli_sanitization.py`) verifying recursive discovery at depths != 4, exclusion of `subagents/` and `-hooks.jsonl`, and sanitization of malicious/malformed project/session_name inputs.
4. Run tests: Execute pytest (`/home/worker/.venv/bin/pytest tests/transcripts/ tests/polecat/`) to verify all existing and new tests pass cleanly.

Write your changes, test results, and handoff report to `/workspace/.agents/teamwork_preview_worker_r1/handoff.md`.
Maintain progress in `/workspace/.agents/teamwork_preview_worker_r1/progress.md`.
When finished, send a message to parent orchestrator.
</USER_REQUEST>
