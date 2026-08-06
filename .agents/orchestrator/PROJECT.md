# Project: Transcript Generation, Launcher Mechanics & OTEL Telemetry Improvements

## Architecture
Target components and data flow:
- Transcript Discovery & Processing: `lib/py/transcripts/` (`runner.py`, `domain/renderer.py`, `domain/view.py`, `adapters/claude.py`)
- Polecat CLI & Container Mechanics: `lib/polecat/cli.py`, `lib/polecat/env_contract.py`, `tests/polecat/`
- OTEL Telemetry & Tracing: `lib/polecat/env_contract.py`, `lib/polecat/cli.py`, `plugins/rbg/hooks/evaluator_otel_trace.py`, `lib/hooks/dispatch.py`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Recursive globbing & filtering | `find_session_files()` uses `rglob('*.jsonl')`, excluding `subagents/` & `-hooks.jsonl` | R1 | ORIGINAL_REQUEST R1 |
| 2 | Launcher path sanitization | Sanitize `project` & `session_name` strings in `lib/polecat/cli.py` | R1 | ORIGINAL_REQUEST R1 |
| 3 | Symmetrical persistence verification | `_verify_transcript_created()` check before writing `run.json`, metadata logging, degraded status | R2 | ORIGINAL_REQUEST R2 |
| 4 | Agent Teams environment default | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `lib/polecat/env_contract.py` | R2 | ORIGINAL_REQUEST R2 |
| 5 | E2E persistence test | `@pytest.mark.e2e` test in `tests/polecat/` | R2 | ORIGINAL_REQUEST R2 |
| 6 | OTEL resource attributes injection | Inject `polecat.session_id`, `polecat.project`, `polecat.task_id` into `OTEL_RESOURCE_ATTRIBUTES` | R3 | ORIGINAL_REQUEST R3 |
| 7 | OTEL tool error instrumentation | Instrument `unknown_tool`, missing MCP, agent idle/timeout events | R3 | ORIGINAL_REQUEST R3 |
| 8 | OTEL SendMessage & SubagentStop tracing | Parent/target span linkage on `SendMessage`, check `SubagentStop` for unsent output | R3 | ORIGINAL_REQUEST R3 |
| 9 | 4-Tier transcript artifact system | Render `.controller.md`, `.full.md`, `.md`, `.html` | R4 | ORIGINAL_REQUEST R4 |
| 10| Special char escaping & collapsible tool outputs | Escape XML/HTML tags in tool outputs & prompts, wrap large outputs in `<details><summary>` | R4 | ORIGINAL_REQUEST R4 |
| 11| Subagent sidechain inlining & fallback | Fix sidechain inlining and fallback rendering for unlinked subagents in `adapters/claude.py` | R4 | ORIGINAL_REQUEST R4 |
| 12| Token accounting & step_index handling | Deduplicate message echoes, split `controller_tokens`/`subagent_tokens`, non-contiguous `step_index` | R4 | ORIGINAL_REQUEST R4 |
| 13| Full test suite, commit, push & PR | Run pytest across suite, commit to git branch, push to remote, open PR | R5 | ORIGINAL_REQUEST R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Phase 0: Survey | Codebase exploration and test mapping | none | DONE |
| 2 | Milestone R1 | Discovery & Launcher Sanitization | Phase 0 | DONE |
| 3 | Milestone R2 | Persistence Verification & Defaults | R1 | DONE |
| 4 | Milestone R3 | OTEL Instrumentation | R2 | DONE |
| 5 | Milestone R4 | 4-Tier Renderer Hardening | R3 | IN_PROGRESS |
| 6 | Milestone R5 | Verification, Commit, Push & PR | R4 | PLANNED |

## Interface Contracts
- `lib/py/transcripts/runner.py`: `find_session_files(session_dir: Path) -> List[Path]`
- `lib/polecat/cli.py`: `_verify_transcript_created(session_dir: Path) -> TranscriptMetadata`
- `lib/polecat/env_contract.py`: `OTEL_RESOURCE_ATTRIBUTES` formatting with `polecat.*` keys
- `lib/py/transcripts/domain/renderer.py`: render methods for all 4 output format tiers
