# aops

Execution and QA: james for collaborative work, marsha for QA, sara for
unattended dispatch, adversary for red-team review, plus the workflow/template
library and skills shared across agents. Ida (the strategic face) and pauli
(memory, the PKB) now ship as their own plugins -- see `plugins/ida` and
`plugins/pkb`.

## How it works

Dispatch happens **by task id**, never by handing freshly-composed text to a
worker as a prompt. The executor's first act is to read the brief cold from the
task, which is what makes the brief bind rather than restate the reasoning that
produced it.

Routing and composition are different jobs. **Routing** picks which template a
class of work follows; the universal templates live in `workflows/` and any agent reads
them directly. **Composition** assembles a full process for work released for
dispatch, happens only inside `brief`, and draws on all three template tiers as
one namespace -- a PKB template composes exactly like a shipped one.

Everything that mutates the PKB routes through `pkb:pauli` by instruction rather
than by tool grant: james, marsha and rbg all omit `tools`, so each inherits its
parent's full effective set including the PKB MCP namespace.

## What it provides

### Agents

| Agent       | Does                                                                                          |
| ----------- | --------------------------------------------------------------------------------------------- |
| `james`     | Collaborative execution -- fans out beneath itself, checks what comes back, reports to `ida`. |
| `marsha`    | QA -- judgement-based review of an artifact against its goal, not a compliance checklist.     |
| `sara`      | Unattended dispatch -- collates released work and reports results without the user present.   |
| `adversary` | Red-team review of a document, plan, proposal, or PR.                                         |

### Skills

| Skill              | Does                                                                                                                                      |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `decompose`        | Expand one situated objective into sub-objectives, decision branches, prerequisites, and alternate paths. Stops before implementation.    |
| `brief`            | Work out the process, size at the forks, set acceptance criteria, write the brief a cold executor is judged against. `inbox` to `queued`. |
| `strategize`       | The thinking pass for "plan this" and "what next" -- fix the altitude, test the plan, route each piece to the stage that owns it.         |
| `pull`             | Claim a queued task, execute it, record the result on the task, and hand over.                                                            |
| `dump`             | Session exit -- save and push work, release claimed tasks with a report, and emit a final handover.                                       |
| `craft`            | The authoring standard and quality gate for any instruction text an agent will read.                                                      |
| `workflow-library` | List, read, add, edit, and retire the workflow templates `brief` composes from -- the only surface that sees all three tiers.             |
| `workflow-create`  | Turn a process the user has just been through and approved into a reusable template.                                                      |
| `strategic-review` | Multi-agent review of a document, plan, proposal, or PR -- rbg, pauli and marsha in parallel, reconciled into one verdict.                |
| `session-trace`    | Export one session's OpenTelemetry spans from the Phoenix span store and read them as evidence.                                           |
| `verify`           | Judgement-based QA pass -- does this artifact meet its goal and serve its user?                                                           |
| `polecat`          | Assigns a task to a team of agents in a detached, isolated container.                                                                     |
| `agy`              | A generic, multi-purpose agent backed by full-featured flagship Gemini models.                                                            |

There are no slash commands; every entry point is a skill.

### Templates

`workflows/` is the universal tier of the process-template library, and `workflows/archive/`
holds retired templates. The other two tiers -- project-local `$CWD/.agents/templates/` and PKB
documents carrying `type: template` -- live outside this plugin.

### Hooks

| Handler                | Event(s)                                                                  | Does                                                                           |
| ---------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `session_start`        | `SessionStart`                                                            | Reports session metadata, staleness warnings, and injected context files.      |
| `rule_against_hearsay` | `PostToolBatch`                                                           | Reminds a supervisor profile that a subagent's report is not evidence.         |
| `be_quiet`             | `PostToolBatch`                                                           | Reminds `aops:ida` to strip her reply to load-bearing content before speaking. |
| `honest_output`        | `SubagentStart`                                                           | Reminds agents to present substantiating evidence with their claims.           |
| tracer handlers        | `UserPromptSubmit`/`PreToolUse`/`PostToolUse`/`PostToolUseFailure`/`Stop` | OpenTelemetry span emission via `claude_code_tracer` / `agy_tracer`.           |

Ida's premise-check gate (arm/verdict/refuse) now ships from `plugins/ida`. PKB
search on `UserPromptSubmit` now ships from `plugins/pkb`.

## Depends on

- `lib/hooks/`, injected into `hooks/` at build time (`manifest/plugin.toml`).
