# aops

Execution and quality assurance plugin for academicOps. Provides agents (`james`, `marsha`, `sara`), composable workflow templates, operational skills, and verification hooks.

## Architecture

- **Task-ID Dispatch**: Executors receive briefs via task IDs rather than inlined prompts, grounding execution in durable graph state.
- **Workflow Tiers**: Templates resolve across Project (`$CWD/.agents/templates/`), PKB (`type: template`), and Universal (`workflows/`) tiers.
- **PKB Mutation**: Graph mutations route through `pkb:pauli`.

## Capabilities

### Agents

| Agent    | Role                                                                    |
| -------- | ----------------------------------------------------------------------- |
| `james`  | Collaborative execution -- parallel coordination and verified delivery. |
| `marsha` | Substantive QA -- runtime execution and excellence review.              |
| `sara`   | Task execution supervisor -- workflow brief preparation and dispatch.   |

### Core Skills

| Skill              | Purpose                                                                                       |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `decompose`        | Expand an objective into an abstract graph of sub-objectives and decision branches.           |
| `brief`            | Reify an objective into dispatch-ready tasks with workflow templates and acceptance criteria. |
| `pull`             | Claim a queued PKB task, coordinate execution, validate deliverables, and hand over.          |
| `dump`             | Finalize a session -- commit work, release claimed tasks, and emit handover report.           |
| `verify`           | Rigorous quality review evaluating artifacts against acceptance criteria and fitness rubrics. |
| `strategic-review` | Multi-agent parallel review (`rbg`, `pauli`, `marsha`) reconciled into one verdict.           |
| `workflow-library` | Inspect, preview, add, edit, and retire composable workflow templates across tiers.           |
| `workflow-create`  | Convert an approved execution transcript into a reusable workflow template.                   |
| `session-trace`    | Export and analyze Phoenix OpenTelemetry spans to audit tool calls, errors, and spend.        |
| `polecat`          | Launch autonomous workers in detached container environments.                                 |
| `agy`              | Headless CLI wrapper executing tasks on Gemini models via Antigravity.                        |
| `craft`            | Authoring standard and quality gate for agent instructions and definitions.                   |

### Hooks

| Handler                | Event               | Function                                                               |
| ---------------------- | ------------------- | ---------------------------------------------------------------------- |
| `session_start`        | `SessionStart`      | Emits session metadata and active context.                             |
| `rule_against_hearsay` | `PostToolBatch`     | Reminds supervisors to verify subagent claims against primary sources. |
| `be_quiet`             | `PostToolBatch`     | Instructs agents to deliver succinct executive briefings.              |
| `honest_output`        | `SubagentStart`     | Enforces evidence contract and basis tagging.                          |
| tracer handlers        | Tool and Turn hooks | Emits OpenTelemetry spans to Phoenix.                                  |
