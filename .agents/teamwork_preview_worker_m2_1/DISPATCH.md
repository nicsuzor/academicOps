## 2026-08-06T12:37:05Z

You are a Worker agent for Milestone 2 (R2. Fix Dangling Plugin References, `aops_4bc0dfea`).
Working directory: /workspace/.agents/teamwork_preview_worker_m2_1/

Scope:
Read /workspace/ORIGINAL_REQUEST.md, /workspace/.agents/orchestrator/PROJECT.md, and survey report in /workspace/.agents/teamwork_preview_explorer_survey_1/handoff.md.

Task:

1. Verify that there are 0 dangling `/email` slash command references across all source plugins (`plugins/`) and distribution build outputs (`dist/`).
2. Create unit test /workspace/tests/test_dangling_email_refs.py that scans all markdown/text files in `plugins/` and `dist/` to assert zero dangling `/email` slash command references exist.
3. Run `uv run python -m build.build` and `uv run pytest tests/test_dangling_email_refs.py` to confirm implementation and test pass.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Maintain progress.md in your working directory and write handoff.md upon completion. Send a message to parent when done.
