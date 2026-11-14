# james

Standalone in-session coordinator and subagent supervision plugin for Claude Code and Antigravity (`agy`). Runs the `/supervise` model across any repository with PKB MCP access, retaining full OpenTelemetry session tracing and startup setup without prompt-hydration or hearsay-gating hooks.

## Skills

| Skill | Description |
| - | - |
| `supervise` | Coordinate multi-stage or repository-scoped work in-session with PKB access, three-tier workflow composition, subagent fan-out, incremental pushes, and handover. |
| `pull` | Claim and execute an already-decomposed queued PKB task to completion and hand over via `/dump`. |
| `dump` | Commit work, mint retroactive tasks when needed, capture durable facts, release claimed tasks, and emit the handover report. |
| `dialectical-review` | Coordinate parallel multi-lens dialectical review (`pauli`, `rbg`, `marsha`) supervised by `james`. |
| `premise-check` | Format evidence-backed reports in Chained Toulmin Argdown and record checker verdicts via `verdict.py --judged-file`. |
| `workflow-library` | Manage and resolve composable workflow templates across Project, PKB, and Universal tiers. |

## Subagents

| Agent | Role |
| - | - |
| `james` | Lead executor and dialectical review supervisor. |
| `marsha` | Qualitative quality and excellence reviewer across live rendered outputs. |
| `pauli` | PKB custodian, strategic fit reviewer, and targeted read-only GitHub query specialist. |
| `rbg` | Compliance reviewer across universal axioms, project rules, data boundaries, and enforcement principles. |

## Hooks

- `SessionStart`: Injects session metadata, `CORE.md`, the `premise-check` pointer, telemetry configuration checks, credential isolation in `CLAUDE_ENV_FILE`, and `AOPS_SESSION_ID` export.
- **OTel tracing & observability**: `claude_code_tracer`, `agy_tracer`, `emit_debug_span`, `telemetry_diagnostic_handler`, and `mcp_caller_session` (`_session` injection on `pkb` / `services` MCP calls). No hearsay gates or `UserPromptSubmit` PKB search hydration hooks are wired.
