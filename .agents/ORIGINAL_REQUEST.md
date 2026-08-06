# Original User Request

## 2026-08-06T12:42:03Z

<USER_REQUEST>
# Teamwork Project Prompt — Transcript Generation, Launcher Mechanics & OTEL Telemetry Improvements

Implement robust transcript discovery, launcher persistence verification, OpenTelemetry (OTEL) tracing, and a 4-tier transcript artifact system across `lib/py/transcripts/`, `lib/polecat/cli.py`, and framework hook layers in `academicOps`, fully tested and submitted via Pull Request.

Working Directory: /workspace
Integrity Mode: development

## Requirements

### R1. Flexible Transcript Path Discovery & Launcher Path Sanitization
- Update `lib/py/transcripts/runner.py` `find_session_files()` to match `.jsonl` files recursively (`rglob`) rather than fixed 4-depth globbing (`*/*/*/*.jsonl`). Filter out `subagents/` subdirectories and `-hooks.jsonl` files.
- Sanitize `project` and `session_name` strings in `lib/polecat/cli.py` to prevent directory hierarchy corruption from prompt option interception or unescaped characters.

### R2. Symmetrical Persistence Verification & Environment Defaults
- Add client-agnostic transcript verification (`_verify_transcript_created()`) in `lib/polecat/cli.py` prior to writing `run.json`.
- Record transcript metadata (`transcript_path`, `transcript_bytes`, `event_count`) in `run.json`. If 0 bytes or missing, flag `"transcript_missing"` in `degraded[]` and set `status: "degraded"`.
- Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` by default in `lib/polecat/env_contract.py`.
- Re-introduce an opt-in E2E container transcript persistence test (`@pytest.mark.e2e`) under `tests/polecat/`.

### R3. OTEL Telemetry Tracing & Error Instrumentation
- Inject `polecat.session_id`, `polecat.project`, and `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES` in `lib/polecat/env_contract.py` and `lib/polecat/cli.py`.
- Instrument tool plumbing errors (`unknown_tool`, missing MCP) and agent idle/timeout events in `plugins/rbg/hooks/evaluator_otel_trace.py` and `lib/hooks/dispatch.py` to emit OTEL exception/span events.
- Instrument `SendMessage` tool calls with parent/target span linkage, and check `SubagentStop` for unsent output.

### R4. 4-Tier Transcript System & Renderer Hardening
- Refactor `lib/py/transcripts/domain/renderer.py` and `domain/view.py` to emit 4 distinct output formats:
  1. `.controller.md` (Controlling Agent Full timeline)
  2. `.full.md` (Full Hierarchical tree with nested subagents)
  3. `.md` (Controlling Agent Concise with truncated tool outputs)
  4. `.html` (Interactive expandable HTML with `<details><summary>` blocks)
- Escape XML/HTML tags in tool outputs and prompts to prevent layout breakage.
- Fix subagent sidechain inlining and fallback rendering for unlinked subagents in `adapters/claude.py`.
- Deduplicate inter-agent message echoes and separate `controller_tokens` from `subagent_tokens` in token accounting.
- Treat `step_index` as non-contiguous sequence IDs to eliminate false data-loss warnings on sparse indices.

### R5. Verification, Commit, Push, and PR
- Run the full test suite (`pytest`) to ensure no regressions occur.
- Commit all changes to a new git branch, push to remote, and create a Pull Request.

## Acceptance Criteria

### Verification & Test Suite
- [ ] `pytest` runs cleanly across `tests/transcripts/` and `tests/polecat/`.
- [ ] Recursive globbing locates `.jsonl` session files deeper than 4 levels while excluding `subagents/` and `-hooks.jsonl`.
- [ ] `run.json` accurately logs transcript metadata and correctly marks `"degraded"` when zero bytes are written.

### Telemetry & Tracing
- [ ] Inner agents inherit Polecat container session attributes in `OTEL_RESOURCE_ATTRIBUTES`.
- [ ] Tool execution failures (`unknown_tool`) generate OTEL exception events.

### Renderer & Artifact Tiers
- [ ] Transcript generator produces all 4 tier files (`.controller.md`, `.full.md`, `.md`, `.html`).
- [ ] HTML/XML special characters in user prompts or tool outputs are properly executed/escaped without breaking renderer output.
- [ ] Large tool outputs are wrapped in native Markdown collapsible `<details><summary>` blocks.

### Delivery
- [ ] Code is cleanly committed and pushed to a git branch.
- [ ] Pull Request is opened with a description of the changes.
</USER_REQUEST>
