# aops

Review, QA, and dispatch: three reviewing agents, the machinery that reconciles them into one verdict, and the container runner that executes the work that verdict authorises.

```mermaid
flowchart TD
    U([user request]) --> IDA["ida<br/>(plugins/ida)"]
    IDA -->|delegates anything substantive| J["james<br/>agents/james.md"]

    J --> SR["skills/strategic-review/SKILL.md<br/>premise test, then fan out"]
    SR --> R1["rbg<br/>agents/rbg.md<br/>axioms/ + $CWD/.agents/rules/ + $ACA_DATA/.agents/rules/"]
    SR --> R2["marsha<br/>agents/marsha.md<br/>skills/verify/SKILL.md — runs it"]
    SR --> R3["pauli<br/>(plugins/pkb) — strategy, architectural fit"]

    R1 --> INT
    R2 --> INT
    R3 --> INT["james interrogates<br/>reject scope drift · send back evidence-free reports · iterate"]

    INT --> V{"synthesised verdict<br/>APPROVE · MINOR CHANGES · REVISE · REJECT"}
    V -->|APPROVE / MINOR CHANGES| BACK["verdict + required changes<br/>returned to ida"]
    V -->|REVISE / REJECT| BRIEF["finding wired into the task graph<br/>fix subtask, or re-dispatch with the brief amended"]

    BRIEF --> D["skills/dispatch/SKILL.md<br/>claim epic · check dependencies · brief · route"]
    D -->|needed now| TEAM["in-session agent team"]
    D -->|substantial repo work| PC["polecat/cli.py run<br/>isolated clone → container → skills/pull"]

    PC --> W["worker: skills/pull/SKILL.md<br/>claim · execute · verify · skills/dump"]
    W --> SIDE["evidence + output URL on the task<br/>delivery guard: no uncommitted, no unpushed"]
    SIDE --> D
    TEAM --> D
    D -->|every unit terminal| BACK
    BACK --> IDA

    H1["SessionStart hook<br/>telemetry report + credential scoping"] -.-> PC
    H2["Stop hook<br/>answer-evidence.md"] -.-> W
    H3["SubagentStop hook<br/>answer-evidence.md"] -.-> W
    H4["PreToolUse hook<br/>headless-interactive-prompt.md<br/>refuses a prompt no one can answer"] -.-> W
```

James never talks to the user; ida does. James never sits inside the dispatch → review → reconcile loop; workers return evidence and he ranks and narrates the outcome.

## What this plugin provides

### Agents

| Agent    | File               | Role                                                                                                      |
| -------- | ------------------ | --------------------------------------------------------------------------------------------------------- |
| `james`  | `agents/james.md`  | Commissions the review lenses, interrogates them, synthesises one verdict. Also routes work to a surface. |
| `marsha` | `agents/marsha.md` | Judges whether an artifact is outstanding. Runs it. `PASS` / `FAIL` / `REVISE`.                           |
| `rbg`    | `agents/rbg.md`    | Judges rule compliance across three rule sources. Silent unless she finds a violation.                    |

### Skills

| Skill              | File                               | Purpose                                                                              |
| ------------------ | ---------------------------------- | ------------------------------------------------------------------------------------ |
| `strategic-review` | `skills/strategic-review/SKILL.md` | Fan out three reviewers, apply the premise test, reconcile into one verdict.         |
| `verify`           | `skills/verify/SKILL.md`           | Marsha's QA pass: forcing checks, halt triggers, verification report.                |
| `dispatch`         | `skills/dispatch/SKILL.md`         | The only pathway to a polecat container. Claim, brief, route, verify by side-effect. |
| `pull`             | `skills/pull/SKILL.md`             | The worker contract: claim a queued task, execute it, record the result.             |
| `dump`             | `skills/dump/SKILL.md`             | Session exit — bail, full, partial, or pause.                                        |

### Hooks

| Event          | Handler                                   | Message                                         | Effect                                                                                                                                      |
| -------------- | ----------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `SessionStart` | `session_start`                           | `session-start.md`, `session-start-isolated.md` | Reports telemetry configuration; scopes credentials for a container session. Reports only — sets nothing.                                   |
| `PreToolUse`   | `refuse_interactive_prompt_when_headless` | `headless-interactive-prompt.md`                | Refuses an interactive prompt in a headless session. The only hook in the framework that blocks a call.                                     |
| `SubagentStop` | `present_checkable_evidence`              | `answer-evidence.md`                            | Reminds the stopping subagent to present its answer with checkable evidence. The output reaches the agent that is stopping, not its parent. |
| `Stop`         | `present_checkable_evidence`              | `answer-evidence.md`                            | Reminds an agent to present its answer with checkable evidence.                                                                             |

Three of the four are advisory: nothing blocks on a rule verdict. `PreToolUse` blocks, and only on a capability fact — a headless session has no human to answer `AskUserQuestion`, so the call cannot return and the session hangs until it times out. A session is headless when any of `NONINTERACTIVE`, `CI`, `AOPS_POLECAT_CONTAINER`, or `CLAUDE_CODE_NON_INTERACTIVE` is `1`. Every other tool passes untouched, and so do these tools in a session with someone in it. `lib/hooks/result.py` holds the rule for when a refusal is legitimate; a handler that has an opinion about compliance returns an advisory instead.

Wording lives in `hooks/messages/` and is editable without touching code.

On agy, only `Stop` fires, as `PostInvocation`. agy has no session-level hook event of any kind, so `SessionStart` cannot fire there. It does have a `PreToolUse`, but its payload names the tool differently from Claude Code's, which `lib/hooks/context.py` is the only thing that reads — so the refusal stays Claude-only until that payload can be parsed, and wiring it sooner would ship a hook that fires and cannot see the tool it is judging. See `lib/hooks/clients.py`.

### Container runner

`polecat/cli.py` runs an agent CLI inside an isolated container: a per-session standalone git clone (never a shared checkout), a read-only staging mount for per-session settings, and a delivery guard that refuses to report success while the workspace has uncommitted changes or unpushed commits. `polecat/entrypoint.sh` configures git and the scoped credential helper inside the container, then execs the agent.

## Configuration

Nothing here has a default. Every value arrives from the environment or from the operator's `polecat.yaml`; a missing required value is a loud failure.

| Variable                                          | Read by                                                 | Purpose                                                                                                                            |
| ------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `POLECAT_HOME`                                    | `polecat/cli.py`                                        | Cache root for isolated clones, staging, and session logs. Required, or `polecat_home` in the config file.                         |
| `POLECAT_IMAGE`                                   | `polecat/cli.py`                                        | Container image reference. Required, or `docker.image` in the config file.                                                         |
| `AOPS_POLECAT_CONFIG`                             | `polecat/cli.py`                                        | Path to the config file. Falls back to `polecat.yaml` under `AOPS_SESSIONS`.                                                       |
| `AOPS_SESSIONS`                                   | `polecat/cli.py`                                        | Session-log root, and the config file's default location.                                                                          |
| `POLECAT_STAGING_BASE`                            | `polecat/cli.py`                                        | Where the per-session staging directory is created.                                                                                |
| `POLECAT_AGENT_HOME`                              | `polecat/cli.py`                                        | Host directory holding the agent CLI's config. Unset means no credential is staged.                                                |
| `POLECAT_WORKER_MODEL`                            | `polecat/cli.py`                                        | Model written into the container's staged settings. Unset means the client decides.                                                |
| `POLECAT_PRINT_TIMEOUT`                           | `polecat/cli.py`                                        | Ceiling on a headless agy run. Unset means the CLI's own limit applies.                                                            |
| `AOPS_BOT_GH_TOKEN`                               | `cli.py`, `entrypoint.sh`, `lib/hooks/credentials.py`   | Repository access inside the container. The container refuses to start without it.                                                 |
| `AOPS_CC_OAUTH_TOKEN` / `CLAUDE_CODE_OAUTH_TOKEN` | `polecat/cli.py`                                        | Agent CLI authentication, forwarded into the container.                                                                            |
| `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`             | `entrypoint.sh`                                         | Commit identity. The container refuses to start without both — there is no default identity.                                       |
| `PKB_MCP_URL`, `PKB_MCP_TOOL_PREFIX`              | `polecat/cli.py`                                        | Knowledge-base MCP endpoint, forwarded into the container and used by the delivery guard to reopen a task closed without delivery. |
| `CLAUDE_ENV_FILE`                                 | `lib/hooks/credentials.py`                              | Scoped env file the `SessionStart` hook writes. Absent means no scoping is needed.                                                 |
| `ACA_DATA`                                        | `agents/rbg.md`                                         | User-scoped rule layer, `$ACA_DATA/.agents/rules/`. Absence is a missing layer, not an error.                                      |
| The OpenTelemetry contract                        | `lib/hooks/telemetry.py`, forwarded by `polecat/cli.py` | Reported at `SessionStart` and forwarded into containers. Never set here. Full list in `specs/ARCHITECTURE.md`.                    |

The plugin declares no `userConfig` fields.

## Depends on

- `lib/hooks/` — shared hook runtime (`dispatch.py`, `context.py`, `result.py`, `clients.py`, `messages.py`, `credentials.py`, `telemetry.py`), injected into `hooks/` at build time.
- `lib/axioms/` — injected into `axioms/` at build time; rbg's first rule source and the source of `axioms.jsonl`.
- `lib/doctrine/` — inlined into the agent files at build time via `@include`.
- `plugins/pkb` at runtime, for `pauli` (the third review lens, and the only writer to the knowledge base) and the task graph james dispatches against.
- Docker on the host that runs `polecat`.
