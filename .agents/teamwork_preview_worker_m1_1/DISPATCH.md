## 2026-08-06T22:32:42Z

You are a Worker agent for Milestone 1 (R1. Email Triage Workflow Component, `aops_7ea0f95f`).
Working directory: /workspace/.agents/teamwork_preview_worker_m1_1/

Scope:
Read /workspace/ORIGINAL_REQUEST.md, /workspace/.agents/orchestrator/PROJECT.md, and survey report in /workspace/.agents/teamwork_preview_explorer_survey_1/handoff.md.

Task:

1. Create /workspace/plugins/pkb/workflows/wf-email-triage.md as a reusable `wf-*` component with frontmatter:
   `id: wf-email-triage`, `kind: obligation`, `permalink: wf-email-triage`, `requires: [task-tracking]`.
2. Update /workspace/plugins/pkb/workflows/INDEX.md to route and list `[[wf-email-triage]]`.
3. Create unit test /workspace/tests/test_wf_email_triage.py verifying frontmatter schema, permalink, file location, and inclusion in `dist/` artifacts after build.
4. Run `uv run python -m build.build` and `uv run pytest tests/test_wf_email_triage.py` to confirm implementation and test pass.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Maintain progress.md in your working directory and write handoff.md upon completion. Send a message to parent when done.
