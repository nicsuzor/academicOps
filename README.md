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
│  capture ideas     │   │  /daily   /butler  │   │  load context     │
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

| Skill                    | Purpose                                              |
| ------------------------ | ---------------------------------------------------- |
| `/plan`                  | Effectual planning, decomposition, graph maintenance |
| `/butler`                | Institutional memory, framework coordination         |
| `/daily`                 | Daily notes, briefing, progress sync                 |
| `/learn`                 | Capture friction and failures, fix instructions      |
| `/qa`                    | Independent verification against acceptance criteria |
| `/pull` `/q` `/handover` | Task queue lifecycle                                 |
| `/remember`              | Persist knowledge to PKB                             |
| `/sleep`                 | Periodic consolidation, graph maintenance            |
| `/email`                 | Email triage and task capture                        |

**Domain skills** (fungible — retire when better external tools exist):

| Skill            | Purpose                                 |
| ---------------- | --------------------------------------- |
| `/analyst`       | Research data analysis (dbt, Streamlit) |
| `/pdf`           | PDF generation with academic typography |
| `/convert-to-md` | Batch document conversion               |
| `/excalidraw`    | Hand-drawn diagrams                     |
| `/flowchart`     | Mermaid flowchart generation            |

### 3. Session infrastructure (hooks)

Hooks make every session framework-aware without manual setup:

- **SessionStart**: loads principles, pulls latest state
- **Autocommit**: keeps PKB synced during work
- **Transcript capture**: records sessions for reflection
- **Cross-device sync**: git-based, runs on cron

### 4. Async quality assurance (GitHub)

GitHub is the coordination layer. PRs run through automated review before human approval.

```
PR opened → lint + typecheck + tests → agent review → merge prep → human approval → merge
```

## Design principles

1. **Qualitative over quantitative** — evaluate fitness-for-purpose, not compliance with templates
2. **Delegate agency** — specify WHAT and WHY, not HOW
3. **Fail-fast** — no defaults, no silent failures
4. **Minimal** — fight bloat. A working simple system beats an elegant complex one
5. **Components earn their keep** — assessed against: used voluntarily? reduces friction? agents understand it? survives neglect?
6. **Graduated enforcement** — start with instructions, escalate only when evidence shows lower levels failing
7. **Anti-bloat** — before creating anything new, check if an existing thing already does it. Two okay things are worse than one good thing.

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

## Development setup

```bash
git clone git@github.com:nicsuzor/academicOps.git && cd academicOps
uv sync                    # install dependencies
make install-hooks         # activate pre-commit hooks
```

Or use `make install-dev` to build, install the plugin locally, and activate hooks in one step.

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
