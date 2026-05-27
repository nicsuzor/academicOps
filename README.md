# academicOps

**Core value**: You can delegate execution to AI without delegating judgment. academicOps provides the structural guarantees that academic integrity is maintained — even when the human isn't paying close attention.

An automation framework for academic work, built as a Claude Code / Gemini CLI plugin.

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
│    TASK SYSTEM     │   │      SKILLS        │   │   SESSION HOOKS   │
│                    │   │                    │   │                    │
│  capture ideas     │   │  /daily   /aops    │   │  load context     │
│  track work        │   │  /plan    /learn   │   │  autocommit       │
│  search context    │   │  /qa      /email   │   │  sync state       │
│  connect knowledge │   │  /pull    /sleep   │   │  capture session  │
│                    │   │  + domain skills   │   │                    │
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

## Four layers

### 1. Task management (the foundation)

Hierarchical task graph with semantic search, powered by a Rust MCP server (`pkb-search`). Everything flows through it — task capture, knowledge storage, memory, context recovery.

Tasks are stored as markdown files within the `data/tasks/` directory of your knowledge base (`$ACA_DATA`). The workflow typically follows: `inbox/` -> `active/` -> `completed/` -> `archived/`.

```
PROJECT  →  EPIC  →  TASK  →  ACTION
```

Goals are linked to projects via the `goals: []` metadata field (many-to-many), not via the tree hierarchy.

### 2. Skills (how work gets done)

Skills are Claude Code / Gemini CLI extensions that know how to do specific things.

**Core skills** (non-fungible — framework operations):

| Skill                | Purpose                                              |
| -------------------- | ---------------------------------------------------- |
| `/plan`              | Effectual planning, decomposition, graph maintenance |
| `/aops`              | Institutional memory, framework coordination         |
| `/daily`             | Daily notes, briefing, progress sync                 |
| `/pull` `/q` `/dump` | Task queue lifecycle                                 |
| `/remember`          | Persist knowledge to PKB                             |
| `/sleep`             | Periodic consolidation, graph maintenance            |
| `/email`             | Email triage and task capture                        |

**Quality skills** (the QA pipeline — from instruction design through verification to post-hoc review):

| Skill            | When to use                                                                |
| ---------------- | -------------------------------------------------------------------------- |
| `/craft`         | Before deploying instructions — reviews for shallow-execution defects      |
| `/design-rubric` | Before building user-facing work — designs fitness criteria on the spec    |
| `/dogfood`       | Testing instructions — delegates to a contextless agent, observes friction |
| `/verify`        | After work is done — judgment-based QA against the spec's fitness rubric   |
| `/learn`         | After a session — forensic transcript review, files GitHub issues          |
| `/issue-sweep`   | Periodically — triages open issues, creates fix-epics                      |
| `/trend-review`  | Periodically — longitudinal analysis across many sessions                  |

The quality skills form a pipeline: `/craft` ensures instructions are excellent before agents execute them. `/design-rubric` ensures specs define what excellence looks like for users. `/dogfood` tests instructions against a real contextless agent. `/verify` checks the delivered artifact. `/learn` reviews transcripts after the fact and files issues. `/issue-sweep` triages those issues into fix-epics.

**Domain skills** (fungible — retire when better external tools exist):

| Skill      | Purpose                                            |
| ---------- | -------------------------------------------------- |
| `/analyst` | Research data analysis (dbt, Streamlit)            |
| `/pdf`     | PDF generation with academic typography            |
| `/extract` | General extraction and ingestion (incl. doc-to-md) |
| `/diagram` | Diagrams — Mermaid or Excalidraw (`style` param)   |

### 3. Session infrastructure (hooks)

Hooks make every session framework-aware without manual setup:

- **SessionStart**: loads principles, pulls latest state
- **UserPromptSubmit hints**: inject context-map pointers
- **PreToolUse gates**: hydration, enforcer (periodic compliance), custodiet (workflow discipline), policy enforcer (destructive-command block)
- **PostToolUse**: orchestrator-boundary detection (brain only), warn-tier checks, autocommit
- **Stop gates**: QA + handover discipline before session ends
- **Transcript capture**: records sessions for reflection
- **Cross-device sync**: git-based, runs on cron

Each runtime mechanism, its hook event, scope, and cost-ladder tier is tracked in [specs/ENFORCEMENT-MAP.md](specs/ENFORCEMENT-MAP.md) — the operative SSoT for enforcement. Mechanisms move down the cost ladder (L0–L7) when evidence shows they were over-broad, and up when evidence shows lower tiers failing (Design Principle #6). For the design rationale (pipeline view, pyramid view, evidence loop) see [specs/enforcement/enforcement.md](specs/enforcement/enforcement.md).

### 4. Async quality assurance (GitHub)

GitHub is the coordination layer. PRs run through automated review before human approval.

```
PR opened → lint + typecheck + tests → agent review → merge prep → human approval → merge
```

## Features × Targets

| Feature Category           |   Claude CLI    |  Desktop Code   |     Cowork      |   Gemini CLI    |   Antigravity   |     Polecat     |    MCP-only     |
| :------------------------- | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: |
| **Skills: core (13)**      | ✅ (unverified) | ✅ (unverified) | ⚠ (unverified)  | ✅ (unverified) | ? (unverified)  | ✅ (unverified) | ? (unverified)  |
| **Skills: cowork ext (5)** | ? (unverified)  | ? (unverified)  | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ? (unverified)  | ? (unverified)  |
| **Skills: tools-only**     | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) | ? (unverified)  | ✅ (unverified) | ? (unverified)  |
| **Slash commands**         | ✅ (unverified) | ✅ (unverified) | ⚠ (unverified)  | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ✗ (unverified)  |
| **Named agents**           | ✅ (unverified) | ✅ (unverified) | ⚠ (unverified)  | ✅ (unverified) | ? (unverified)  | ✅ (unverified) | ? (unverified)  |
| **Hooks (lifecycle)**      | ✅ (unverified) | ✅ (unverified) | ✗ (unverified)  | ✅ (unverified) | ✗ (unverified)  | ✗ (unverified)  | ✗ (unverified)  |
| **Gates / classifiers**    | ✅ (unverified) | ✅ (unverified) | ⚠ (unverified)  | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ? (unverified)  |
| **MCP: PKB**               | ✅ (unverified) | ⚠ (unverified)  | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) |
| **MCP: Outlook (omcp)**    | ✅ (unverified) | ✅ (unverified) | ? (unverified)  | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ✅ (unverified) |
| **MCP: Zotero (zotmcp)**   | ✅ (unverified) | ✅ (unverified) | ? (unverified)  | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ✅ (unverified) |
| **MCP: Discord**           | ? (unverified)  | ? (unverified)  | ? (unverified)  | ? (unverified)  | ? (unverified)  | ? (unverified)  | ✅ (unverified) |
| **MCP: computer-use**      | ✅ (unverified) | ✅ (unverified) | ✅ (unverified) | ? (unverified)  | ? (unverified)  | ? (unverified)  | ? (unverified)  |
| **Background jobs**        | ✗ (unverified)  | ✗ (unverified)  | ? (unverified)  | ✗ (unverified)  | ? (unverified)  | ✅ (unverified) | ✗ (unverified)  |

**Legend**: ✅ Supported · ⚠ Partial · ✗ N/A · ? Unknown · (unverified) status: unverified

### Per-target install

#### Claude Code CLI

```bash
# Placeholder for T2
```

#### Claude Desktop Code

```bash
# Placeholder for T3
```

#### Claude Code Cowork

```bash
# Placeholder for T4
```

#### Gemini CLI

```bash
# Placeholder for T5
```

#### Antigravity

```bash
# Placeholder for T6
```

#### Polecat / GHA workers

```bash
# Placeholder for T7
```

#### Standalone MCP-only

```bash
# Placeholder for T8
```

## Design principles

1. **Qualitative over quantitative** — evaluate fitness-for-purpose, not compliance with templates
2. **Delegate agency** — specify WHAT and WHY, not HOW
3. **Fail-fast** — no defaults, no silent failures
4. **Minimal** — fight bloat. A working simple system beats an elegant complex one
5. **Components earn their keep** — assessed against: used voluntarily? reduces friction? agents understand it? survives neglect?
6. **Graduated enforcement** — start with instructions, escalate only when evidence shows lower levels failing
7. **Anti-bloat** — before creating anything new, check if an existing thing already does it. Two okay things are worse than one good thing.
8. **Recusal — don't legislate from your own case** (AXIOMS § A17) — the agent that just experienced a failure is forensically authoritative but normatively recused from proposing the framework change motivated by it. Framework-change work is split in two:
   - **Incident phase** (`/learn`, `/retro`): facts, root-cause category, the rule already in place at the time (if any), and an impact statement. **No "suggested axiom", no "add a gate", no remediation.** Recency exposure is bias; the report does not propose its own remedy.
   - **Review phase** (`/issue-sweep`): a separate, detached context reads incident reports against `specs/ENFORCEMENT-MAP.md` and the axiom set, and is the only phase allowed to author rule changes — defaulting to the cheapest sufficient level (L0/L1 propagation), escalating only when the cost-benefit threshold (≥3 cited recurrences) is satisfied.

   The evidence base for framework change is _recurrence_, not the salience of the most recent incident. A future incident register (rule ↔ mechanism ↔ incident report) will formalise this; until it lands, the detached reviewer relies on `gh issue list` and row-by-row ENFORCEMENT-MAP review.

## Memory architecture

| Type          | Storage                             | Purpose                              |
| ------------- | ----------------------------------- | ------------------------------------ |
| **Knowledge** | `$ACA_DATA` markdown + vector index | Searchable knowledge base            |
| **Tasks**     | PKB task graph                      | Work tracking with dependencies      |
| **Memory**    | PKB memories                        | Generalizable patterns and learnings |

`$ACA_DATA` is the personal knowledge base — human-readable markdown in git, with a Rust MCP server providing semantic search over vector embeddings.

## Installation

Distribution repository: https://github.com/nicsuzor/aops

```bash
# Set your knowledge base directory
export ACA_DATA="$HOME/brain"
```

**Claude Code**:

```bash
command claude plugin marketplace add nicsuzor/aops
```

**Gemini CLI**:

```bash
(command gemini extensions uninstall aops-core || echo not installed) && \
  command gemini extensions install git@github.com:nicsuzor/aops.git --consent --auto-update --pre-release
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

Gates are runtime quality checks that fire during sessions. They catch common failure modes — exiting without committing, claiming "done" without verification, scope drift in long sessions.

| Gate        | What it catches                                             | Default |
| ----------- | ----------------------------------------------------------- | ------- |
| `ida`       | Honesty / criterion-substitution check before stopping      | `warn`  |
| `handover`  | Exiting without committing, updating tasks, or reflecting   | `warn`  |
| `qa`        | Claiming "done" without running verification                | `warn`  |
| `enforcer`  | Scope drift / compliance in long-running sessions           | `warn`  |
| `hydration` | Context injection on user prompts (reserved, not yet gated) | `off`   |

Each gate runs in one of three modes: **`warn`** (reminds the agent but doesn't block), **`block`** (stops the agent until the condition is met), or **`off`** (disabled).

#### How to configure gates

There are three ways to configure gates, depending on how you run your sessions:

**1. `polecat.yaml`** — for polecat-managed sessions (autonomous workers and crew). This is the primary configuration file:

```yaml
# $AOPS_SESSIONS/polecat.yaml
session_defaults:
  gates:
    handover: warn      # warn | block | off
    qa: warn
    enforcer: warn
    ida: warn
    hydration: off
    enforcer_threshold: 50   # write ops between enforcer checks

# Override per session type
run_defaults:             # autonomous polecat workers
  gates:
    handover: block       # workers must hand over before exiting
    enforcer: block
    enforcer_threshold: 30

crew_defaults: {}         # interactive crew sessions (inherits session_defaults)
```

See [`polecat/defaults/polecat.yaml.example`](polecat/defaults/polecat.yaml.example) for the full schema.

**2. Environment variables** — for direct CLI sessions (Claude Code or Gemini on your machine). The plugin's built-in defaults apply automatically; override individual gates by setting environment variables in your shell:

```bash
export HANDOVER_GATE_MODE=off       # skip handover for quick interactive chats
export ENFORCER_GATE_MODE=block     # stricter compliance checking
```

The full list: `HANDOVER_GATE_MODE`, `QA_GATE_MODE`, `ENFORCER_GATE_MODE`, `IDA_GATE_MODE`, `HYDRATION_GATE_MODE`, `ENFORCER_TOOL_CALL_THRESHOLD`.

3. Per-directory overrides - to change gate behaviour for a specific project, set the environment variables in your shell environment. Note: on Mac/WSL host, environment variables set in CLI settings env blocks do not reliably reach the hooks. See GATES.md for technical details.

For the detailed gate reference (state machines, triggers, debugging), see [`aops-core/GATES.md`](aops-core/GATES.md).

## Development setup

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync                    # install dependencies
make install-hooks         # activate pre-commit hooks
```

Or use `make install-dev` to build, install the plugin locally, and activate hooks in one step.

Run `./scripts/format.sh` manually before committing if pre-commit hooks aren't firing.

## Testing and release

```bash
uv run pytest                              # fast unit tests (default, CI)
make build                                 # build Docker image
uv run pytest -m slow -n 0 --timeout=300   # container e2e + live session tests
```

Before releasing, build the image and run slow tests on a Docker-capable host. Releases are cut via release-please PRs on `main`.

## Project configuration

Projects customise the framework by adding files to a `.agents/` directory:

- **`.agents/rules/`** — Project-specific rules loaded as binding constraints
- **`.agents/workflows/`** — Project-specific workflows supplementing the global index
- **`.agents/context-map.json`** — Maps project documentation to topics for just-in-time context injection
