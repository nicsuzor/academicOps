# academicOps

**Core value**: You can delegate execution to AI without delegating judgment. academicOps provides the structural guarantees that academic integrity is maintained — even when the human isn't paying close attention.

An automation framework for academic work, built as a Claude Code plugin.

## How it works

```
                    ┌─────────────────────────────────┐
                    │         YOUR NORMAL WORK         │
                    │  research · writing · teaching   │
                    └──────────────┬──────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
┌─────────▼─────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
│    TASK SYSTEM     │   │      SKILLS        │   │  AGENT JUDGMENT    │
│                    │   │                    │   │                    │
│  capture ideas     │   │  /daily  /decompose│   │  premise (pauli)   │
│  track work        │   │  /learn  /remember │   │  rules (rbg)       │
│  search context    │   │  /pull   /verify   │   │  quality (marsha)  │
│  connect knowledge │   │  + domain skills   │   │  sign-off (human)  │
│                    │   │                    │   │                    │
└─────────┬──────────┘   └─────────┬──────────┘   └─────────┬──────────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │    LEARN AS YOU GO      │
                      │                        │
                      │  notice friction  ───► /learn
                      │  file findings   ───► PKB task
                      │  fix instructions ───► better next time
                      │                        │
                      └────────────┬───────────┘
                                   │
                      ┌────────────▼───────────┐
                      │   ASYNC QUALITY (GitHub) │
                      │                        │
                      │  PR ► lint ► review     │
                      │  ► merge prep ► human   │
                      │  approval ► merge       │
                      └────────────────────────┘
```

The framework improves as a side-effect of doing normal work. When agents hit friction, they file it via `/learn`. Findings become tasks. Tasks get prioritised. Instructions get better. The system compounds.

For the full picture — every component, exactly **what triggers movement between them**, and where the security / review / QA mechanisms sit — see the flow-and-trigger map: [`specs/FLOW-MAP.md`](specs/FLOW-MAP.md).

## Five parts

Strip away the tooling and academicOps reduces to five things, each holding up the one after it.

### 1. PKB — task and knowledge server

A hierarchical task graph with semantic search, served by a Rust MCP server (`pkb-search`). Everything flows through it: task capture, knowledge storage, memory, context recovery.

Tasks are markdown files under `data/tasks/` in your knowledge base (`$ACA_DATA`): `inbox/` → `active/` → `completed/` → `archived/`.

```
PROJECT  →  EPIC  →  TASK  →  ACTION
```

Goals link to projects via the `goals: []` metadata field (many-to-many), not the tree hierarchy.

| Type          | Storage                             | Purpose                              |
| ------------- | ----------------------------------- | ------------------------------------ |
| **Knowledge** | `$ACA_DATA` markdown + vector index | Searchable knowledge base            |
| **Tasks**     | PKB task graph                      | Work tracking with dependencies      |
| **Memory**    | PKB memories                        | Generalizable patterns and learnings |

`$ACA_DATA` is the personal knowledge base — human-readable markdown in git, with the PKB server providing semantic search over vector embeddings.

### 2. Axioms — rules that must never be breached

A small, fixed set of universal rules bind every agent, on every surface, with no ad-hoc exceptions: `halt-on-failure`, `honest-epistemics`, `data-boundaries`, `evidence-immutable`, `full-observability`, and a dozen more — each targeting a _class_ of failure, never a single instance. The full set, with the reasoning behind each, is the actual law: [`.agents/AXIOMS.md`](.agents/AXIOMS.md) (`.agents/rules/` holds per-axiom mirror files, not the consolidated source).

Axioms describe what must never happen. They don't enforce themselves — that's part 3.

### 3. Enforcement — a minimal in-session hook, backed by a PR-time review pipeline

An earlier version of this framework ran a ~40-mechanism in-session gate pyramid — turn-based compliance counters, blocking Stop gates with per-gate mode config, a dedicated `GateConfig` engine. **That engine has been retired in full** (see [`specs/enforcement/enforcement.md`](specs/enforcement/enforcement.md), the current authoritative account). Enforcement's centre of gravity today is the task-graph boundary (claim → execute → release — a convention agents follow, not code that checks it) plus agent judgment at review time, backed by a real, code-checked PR pipeline.

The entire in-session hook surface is one 131-line script, [`aops/hooks/router.py`](aops/hooks/router.py), wired to four Claude Code events via [`aops/templates/hooks.template.json`](aops/templates/hooks.template.json):

- **SessionStart** — copies a fixed allowlist of env vars (`AOPS_SESSIONS`, `PKB_MCP_URL`, GitHub tokens, …) into the session; does not load axioms and does not query PKB state. Axioms are baked in separately, at build/install time (`scripts/build.py` → `dist/aops-claude/axioms.jsonl` → merged into `~/.claude/settings.json` by `scripts/install_automode.py`).
- **UserPromptSubmit** — injects the static template [`aops/templates/ida-hydrate.md`](aops/templates/ida-hydrate.md) as `additionalContext` on every prompt. It's a reminder, not a routing decision — nothing here calls a skill or hook-blocks anything.
- **Stop** / **SubagentStop** — inject static reminder templates (`ida-reminder.md`, `deliverable-verify-reminder.md`) unless `stop_hook_active` is already set. The `"decision": "block"` line is present in the code but commented out — there is no verdict, no FULL/LITE tier, nothing that can actually stop an agent from exiting.
- **PostToolUse** — no hook registered for this event at all. There is no boundary detection and no autocommit in the current build.

Real enforcement instead runs after the session, as regular CI on the PR — checked by GitHub Actions, not a claim in a doc:

| Workflow                                                                                                 | Trigger                               | What it actually runs                                                                 |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------- |
| `lint.yml`                                                                                               | push/PR                               | `ruff check` / `ruff format --check`, MCP-name normalization, ruleset-alignment check |
| `pytest.yml`, `typecheck.yml`                                                                            | push/PR                               | `pytest`, `basedpyright`                                                              |
| `rbg-review.yml`                                                                                         | PR labeled `request-rbg-review`       | Claude reviews the diff against `.agents/rules/*.md` and posts inline comments        |
| `agent-enforcer.yml`, `agent-qa.yml` (Marsha), `agent-mechanic.yml`, `agent-pre-admission-responder.yml` | reusable, called from other workflows | each assembles a persona prompt and runs `claude-code-action`                         |
| `.github/rulesets/pr-review-and-merge.yml`                                                               | branch ruleset on `dev`               | requires the human approval click before merge                                        |

Two things worth knowing if you're relying on this table: `pr-pipeline.yml` — the file the name implies holds the orchestration — is currently an empty stub (a comment pointing at a spec, no jobs). And `agent-qa.yml` sparse-checks out `aops-pkb/agents/marsha.md`, a path that doesn't exist in this repo (the real file is `aops/agents/marsha.md`) — that job would fail its own fail-fast check on a real run. `pauli` (design-intent review) has no CI wiring at all; it exists only as a persona file and in this doc.

Axioms and project rules that DO apply during a session live in `.agents/AXIOMS.md` (framework) and `.agents/rules/` (project) — read by the agent as instructions, not enforced by a hook.

A project extends this under its own `.agents/` directory:

- **`.agents/rules/`** — project-specific rules loaded as binding constraints
- **`.agents/workflows/`** — project-specific workflows supplementing the global index
- **`.agents/INDEX.md`** — plain-text index of project documentation, to aid discovery

### 4. Task pipeline and Polecat — from a prompt to a dispatched worker

The intended shape of a task's life is six stages — `hydrate → situate → decompose → brief → execute → evaluate` — coordinated only through the PKB graph (a task's frontmatter + body is the message bus; no stage calls another directly). `hydrate` and `situate` build a task node out of a raw prompt; `decompose` (pauli) breaks it into a subtask DAG with review steps built in; `brief` composes a self-contained delegation brief per subtask at dispatch time (the identity that writes a brief never executes it); `execute` runs it; `evaluate` (`/verify` or `/strategic-review`) judges the emitted evidence against the brief's rubric, not by re-running the work.

**What's actually wired today, not what's planned:** `hydrate` fires automatically — every prompt gets a static reminder injected by the `UserPromptSubmit` hook (see [Enforcement](#3-enforcement--a-minimal-in-session-hook-backed-by-a-pr-time-review-pipeline) above). `/q` → `situate` works (`aops/commands/q.md` → `Skill(skill="situate")`). `decompose` exists as a skill (`aops/skills/decompose/SKILL.md`) but is **not** a registered slash command — it's reachable only via an explicit `Skill()` call from another flow. `/dispatch` and `/pull` both call `Skill(skill="task-lifecycle", ...)`, and that skill **does not exist in this repo** — both commands are currently broken (tracked in PKB as `aops-polecat-architecture-gap`). `/plan` has no command file at all.

Polecat (`aops-jr/polecat/cli.py`, 334 lines) is what actually spins up a containerized worker, but as of this week it's mid-rebuild: the previous 5,734-line CLI and its supporting modules (`manager.py`, `claim.py`, `finalize.py`, `pkb_bridge.py`, and others) were deleted outright, and the file at `aops-jr/polecat/cli.py` today is a minimal replacement (`cli_lite.py`, renamed). It exposes exactly one subcommand, `run` — there is no `crew`, `start`, `finish`, `nuke`, or `swarm`. `run` reads `polecat.yaml` only for the Docker image and project path, builds a `docker run` command that bind-mounts the host repo directly (no per-task worktree isolation), and execs it. It does **not** resolve gate posture from `crew_defaults`/`run_defaults`, does **not** claim or release a PKB task, and does **not** file a PR — none of that logic exists in the current code; `claim_task`/`release_task` remain a documented convention (`specs/enforcement/task-contract.md`), not a checked one. See [`INSTALL.md`](INSTALL.md#polecat-installation) to install it.

### 5. Full observability — recorded, end to end

Every material action — file edits, tool calls, gate verdicts, subagent dispatches — leaves a trace an auditor can read: session transcripts, hooks JSONL logs, git commits, PRs. Nothing counts as done unless a third party could reconstruct the path from input to output. This is the `full-observability` axiom, held up by the same enforcement mechanisms as everything else in this list — not a bolt-on feature.

## Skills (how work gets done)

Skills are Claude Code extensions that know how to do specific things, split into two groups because a researcher installing this plugin mostly needs the first for their own work, while the second runs the framework's own self-improvement loop.

**User-facing core** (the commands a researcher actually reaches for in their own work):

| Skill        | Purpose                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------ |
| `/daily`     | Daily notes, briefing, progress sync                                                       |
| `/dump`      | Session exit — bail (default), `full` (canonical close), or `pause` (hand back mid-flight) |
| `/plan` `/q` | Effectual planning, decomposition, and task capture                                        |
| `/project`   | Scaffold a research project repo with smart defaults                                       |
| `/remember`  | Persist knowledge to PKB                                                                   |
| `/pull`      | Claim the next queued task and run it inline                                               |

**Framework governance** (installed, but not marketed as researcher-facing daily tools — governs the framework's own quality and development process):

| Skill               | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `/aops`             | Institutional memory, framework coordination                                         |
| `/craft`            | Reviews instructions for shallow-execution defects before deployment                 |
| `/design-rubric`    | Designs fitness criteria on the spec, before user-facing work is built               |
| `/dogfood`          | Delegated instruction testing — commissions contextless execution, observes friction |
| `/strategic-review` | Multi-agent adversarial review of a document, plan, or pull request                  |
| `/supervisor`       | Delegate-and-verify supervision loop, from a single epic to a portfolio release      |
| `/triage`           | Corpus triage — retro (transcripts), trend (longitudinal), sweep (issue triage)      |
| `/verify`           | Judgment-based QA against the spec's fitness rubric                                  |

**Domain skills** (fungible — retire when better external tools exist):

| Skill      | Purpose                                            |
| ---------- | -------------------------------------------------- |
| `/analyst` | Research data analysis (dbt, Streamlit)            |
| `/pdf`     | PDF generation with academic typography            |
| `/extract` | General extraction and ingestion (incl. doc-to-md) |
| `/diagram` | Diagrams — Mermaid or Excalidraw (`style` param)   |

## Design principles

1. **Qualitative over quantitative** — evaluate fitness-for-purpose, not compliance with templates
2. **Delegate agency** — specify WHAT and WHY, not HOW
3. **Fail-fast** — no defaults, no silent failures
4. **Minimal** — fight bloat. A working simple system beats an elegant complex one
5. **Components earn their keep** — assessed against: used voluntarily? reduces friction? agents understand it? survives neglect?
6. **Graduated enforcement** — start with instructions, escalate only when evidence shows lower levels failing
7. **Anti-bloat** — before creating anything new, check if an existing thing already does it. Two okay things are worse than one good thing.
8. **Don't over-fit to one incident** — the evidence base for a framework change is _recurrence_, not the salience of the most recent failure. `/learn` files the forensic facts of an incident; a separate, detached pass (`/issue-sweep`) later weighs accumulated reports and decides whether a rule change is warranted. A single salient incident shouldn't drive a framework change that doesn't generalise.

## Installation

Distribution repository: https://github.com/nicsuzor/academicOps

**Requirements**:

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
- GitHub CLI (`gh`) for artifact retrieval
- Docker (optional, for sandboxing/testing)

**Quick Install** (`@dist` pins the published distribution branch):

```bash
command claude plugin marketplace add nicsuzor/academicOps@dist
```

## Configuration

The framework works out of the box after installation. Sensible defaults apply — all quality gates warn (agents see reminders without being blocked) and project repos are auto-discovered by convention.

### Environment variables

Set these in your shell profile (`~/.zshenv`, `~/.bashrc`, or equivalent):

| Variable              | Purpose                                                | Default                         |
| --------------------- | ------------------------------------------------------ | ------------------------------- |
| `ACA_DATA`            | Your personal knowledge base root                      | Required (no default)           |
| `AOPS_SESSIONS`       | Sessions repo (holds `polecat.yaml` registry)          | `$POLECAT_HOME/sessions`        |
| `AOPS_SRC_DIR`        | Default search root for project repos                  | `~/src`                         |
| `PKB_MCP_URL`         | Endpoint for the PKB MCP server                        | (local stdio fallback)          |
| `AOPS_POLECAT_CONFIG` | Explicit path to `polecat.yaml` (skips env resolution) | (resolved via `$AOPS_SESSIONS`) |

The project registry lives in `$AOPS_SESSIONS/polecat.yaml`. Path resolution is convention-based (`$AOPS_SRC_DIR/<repo>`); for off-convention repos, add a `paths:` entry to `$POLECAT_HOME/local.yaml`:

```yaml
# $POLECAT_HOME/local.yaml
paths:
  brain: ${ACA_DATA}
  myproject: /opt/work/myproject
```

### Gates (quality checks)

`aops-jr/polecat/defaults/polecat.yaml.example` still documents a `session_defaults` / `run_defaults` / `crew_defaults` gate schema (`exit_reflection`, `ida`, `hydration`, each `warn`/`block`/`off`), and this doc used to list matching env vars (`EXIT_REFLECTION_GATE_MODE`, `IDA_GATE_MODE`, `HYDRATION_GATE_MODE`). As of the current build, **nothing reads either one** — `aops-jr/polecat/cli.py` never looks at a `gates:` key, and none of those env var names appear anywhere in the hook script (`aops/hooks/router.py`) or elsewhere in source. There is no gate-mode config to set today; see [Enforcement](#3-enforcement--a-minimal-in-session-hook-backed-by-a-pr-time-review-pipeline) above for what actually runs. The config file is left in place because it's the intended shape of a gate-resolution layer that hasn't been rebuilt yet, not because it's live.
