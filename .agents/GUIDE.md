# academicOps Agent Field Guide & Repository Map

> **Authoritative Context Document for AI Agents and Developers**\
> **Last Updated**: July 2026\
> **Location**: [`.agents/GUIDE.md`](file:///Users/suzor/src/academicOps/.agents/GUIDE.md)

---

## 1. Executive Summary & Core Philosophy

**academicOps** is an automation and coordination framework for academic operations, research, teaching, and administrative workflows. Built primarily as a suite of plugins for **Claude Code** (and compatible platforms like Google Antigravity), its founding axiom is:

> _"You can delegate execution to AI without delegating judgment."_

### Core Architectural Tenets

1. **Human Acceptance Criteria**: The human requester defines the _what_ and _why_ and sets acceptance criteria.
2. **Agent Execution & Qualitative Review**: Autonomous workers execute subtasks, but distinct qualitative review agents ([`pauli`](file:///Users/suzor/src/academicOps/specs/agents/pauli.md), [`rbg`](file:///Users/suzor/src/academicOps/specs/agents/rbg.md), [`marsha`](file:///Users/suzor/src/academicOps/specs/agents/marsha.md), [`james`](file:///Users/suzor/src/academicOps/specs/agents/james.md)) judge design intent, rule compliance, and quality.
3. **The Learning Flywheel**: Operational friction triggers `/learn` recommendations. Friction reports become PKB tasks, which get prioritized and resolved via `/issue-sweep`, continuously improving system instructions and skills.
4. **Dual Head Architecture**:
   - **Ida**: Interactive research co-working head (methodology, analysis, paper writing, unit coordination).
   - **Junior**: Infrastructure, dispatch, background coordination, and cross-project agent management head.

---

## 2. Modular Package Topology

Per [v0.5 Modular Topology Spec](file:///Users/suzor/src/academicOps/specs/packaging/v0.5-modular-topology.md), the repository is split into distinct, decoupled packages:

| Directory                                                             | Package Name            | Role & Contents                                                                                                                                                                                                                                                 |
| :-------------------------------------------------------------------- | :---------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`aops/`](file:///Users/suzor/src/academicOps/aops)                   | `aops` (Core)           | Core framework runtime: `router.py` hook script, Polecat container executor, core persona definitions (`pauli`, `rbg`, `marsha`, `james`, `ida`), core commands (`/bump`, `/learn`), and skills (`dispatch`, `handover`, `pull`, `strategic-review`, `verify`). |
| [`aops-tools/`](file:///Users/suzor/src/academicOps/aops-tools)       | `aops-tools`            | Domain-specific research skills: `analyst` (dbt/Streamlit pipelines), `pdf` (academic typesetting), `extract` (doc-to-md ingestion), `diagram` (Mermaid/Excalidraw), `peer-review`, `deep-research`, `style`, `new-project`, `python-viz`, `streamlit`, `dbt`.  |
| [`aops-jr/`](file:///Users/suzor/src/academicOps/aops-jr)             | `aops-jr`               | Coordinator & dispatch plugin: `junior` subagent, dispatch workflows, background task management, and polecat container helpers. Has its own `pyproject.toml`.                                                                                                  |
| [`aops-pkb/`](file:///Users/suzor/src/academicOps/aops-pkb)           | `aops-pkb`              | Personal Knowledge Base (PKB) integration skills: `hydrate`, `situate`, `decompose`, `brief`, `remember`, `graph-maintenance`. Commands: `/q`.                                                                                                                  |
| [`aops-cowork/`](file:///Users/suzor/src/academicOps/aops-cowork)     | `aops-cowork`           | Self-contained marketplace distribution wrapper for Cowork sessions.                                                                                                                                                                                            |
| [`aops-ts/`](file:///Users/suzor/src/academicOps/aops-ts)             | `aops-ts`               | Opt-in Tailscale networking hook plugin for cloud/remote sessions.                                                                                                                                                                                              |
| [`reflexes-cope/`](file:///Users/suzor/src/academicOps/reflexes-cope) | `reflexes-cope`         | Experimental/in-session advisory policy & reflex hooks. Has its own `pyproject.toml`.                                                                                                                                                                           |
| [`.agents/`](file:///Users/suzor/src/academicOps/.agents)             | Repository Agent Rules  | Project-local context and binding constraints for agents working _on_ the academicOps codebase itself (`CORE.md`, `AXIOMS.md`, `rules/`).                                                                                                                       |
| [`specs/`](file:///Users/suzor/src/academicOps/specs)                 | Specifications (SSoT)   | The canonical source of truth for design intent, workflow diagrams, enforcement specs, and agent charters.                                                                                                                                                      |
| [`scripts/`](file:///Users/suzor/src/academicOps/scripts)             | Build & Install Tooling | Python and shell scripts for assembling dist artifacts (`build.py`), automode installation (`install_automode.py`), and dev environment setup.                                                                                                                  |
| [`tests/`](file:///Users/suzor/src/academicOps/tests)                 | Pytest Test Suite       | Test harness covering hooks, router dispatch, manifest validation (`test_plugin_manifests.py`), and polecat container execution.                                                                                                                                |

---

## 3. Core Task Lifecycle & Review Agents

### The Six-Stage Task Lifecycle

Work is driven through a 6-stage lifecycle using the PKB task graph as the asynchronous message bus:

```
┌───────────┐     ┌───────────┐     ┌─────────────┐
│  hydrate  │ ──► │  situate  │ ──► │  decompose  │
└───────────┘     └───────────┘     └──────┬──────┘
                                           │
┌───────────┐     ┌───────────┐     ┌──────▼──────┐
│ evaluate  │ ◄── │  execute  │ ◄── │    brief    │
└───────────┘     └───────────┘     └─────────────┘
```

1. **Hydrate**: Takes an raw inbound ask or prompt and enriches it with full PKB and workflow context.
2. **Situate**: Transforms the hydrated ask into exactly one well-connected task node on the PKB graph (marked `needs_decomposition`).
3. **Decompose** (_Pauli_): Breaks situated epic into an unexploded subtask DAG and attaches required review dependencies (`pauli`, `rbg`, `marsha`).
4. **Brief**: Composes a 7-element delegation brief (intent, scoped context, limits, autonomy, acceptance criteria, evidence contract, effort type) for the immediate next subtask.
5. **Execute**: Worker (Polecat container or subagent) executes the task based on the brief.
6. **Evaluate** (`/verify` / `/strategic-review`): Review agents judge emitted evidence against the brief's acceptance criteria without re-running the work.

### Qualitative Review Persona Roster

- **`james` (The Orchestrator)**: Synthesizes multi-agent reviews and resolves conflicting verdicts into one actionable judgment.
- **`pauli` (The Logician & Memory Custodian)**: Controls PKB graph hygiene, strategic decomposition, design-intent reviews (`/design-rubric`), and memory skills (`/remember`, `/dump`, `/daily`, `/sleep`).
- **`rbg` (Ruth, The Judge)**: Strict enforcer of universal axioms (`.agents/AXIOMS.md`) and project rules (`.agents/rules/`).
- **`marsha` (The QA Reviewer)**: Verifies deliverables against original user intent and evidence contracts.

---

## 4. Build, Packaging & Distribution Infrastructure

### Master Build System (`scripts/build.py` & `Makefile`)

Building is executed via `python3 scripts/build.py` or `make build`. Output is assembled under `dist/`:

- **Claude Code Targets** (`dist/*-claude`):
  - Uses `.claude-plugin/plugin.json`.
  - Places hooks in `hooks/hooks.json`.
  - Generates `axioms.jsonl` containing all `trigger: always_on` rules, which `scripts/install_automode.py` merges directly into `~/.claude/settings.json`.
- **Google Antigravity Targets** (`dist/*-antigravity`):
  - Uses `plugin.json` at root.
  - Automatically translates slash commands (`commands/*.md`) into native skills at `skills/cmd-<name>/SKILL.md`.
  - Copies axiom files directly to `rules/*.md`.
- **Cowork Target** (`dist/cowork`):
  - Assembles a self-contained directory marketplace (`academicOps-cowork`) to prevent reset issues in remote Cowork sessions.
  - Processes `<!-- cowork:only --> ... <!-- /cowork:only -->` markdown blocks.

---

## 5. Inconsistencies, Workarounds, Duplication & Missing Gaps

During our thorough repository audit, several discrepancies, legacy artifacts, and missing references were identified. Agents must be aware of these when navigating or modifying the codebase:

### 1. Broken Documentation & Missing MOC

- **Issue**: [`.agents/CORE.md`](file:///Users/suzor/src/academicOps/.agents/CORE.md#L11) states `Specs: specs/INDEX.md (MOC) — read this first when scoping any change`.
- **Reality**: `specs/INDEX.md` **does not exist** in the repository. The actual specification directory relies on subdirectory indexing (e.g. `specs/FLOW-MAP.md`, `specs/enforcement/enforcement.md`, `specs/packaging/v0.5-modular-topology.md`).

### 2. Missing `task-lifecycle` Skill

- **Issue**: [README.md](file:///Users/suzor/src/academicOps/README.md#L119) documents that slash commands `/dispatch` and `/pull` invoke `Skill(skill="task-lifecycle", ...)`.
- **Reality**: The `task-lifecycle` skill does not exist anywhere in `aops/skills/`, `aops-pkb/skills/`, or `.agents/skills/`. As noted in `README.md`, both commands are currently broken.

### 3. Missing Slash Command `/plan`

- **Issue**: Referenced across interactive workflow documentation and slash command lists.
- **Reality**: No command file `plan.md` exists in `aops/commands/` or `aops-pkb/commands/`.

### 4. Polecat CLI Shrink & Unimplemented Subcommands

- **Issue**: Older specs and docs reference `polecat crew`, `start`, `finish`, `nuke`, and `swarm` subcommands.
- **Reality**: `aops/polecat/cli.py` was refactored down from 5,734 lines to a minimal 334-line implementation (`cli_lite.py`). Currently, it exposes **only** the `run` subcommand. Worktree isolation, automatic PKB task claiming, and automatic PR creation are not implemented in the current CLI.

### 5. Retired In-Session Enforcement Engine vs. Reality

- **Issue**: Historical specs (`specs/enforcement/hook-gate-system.md`) document a complex 40-mechanism in-session gate pyramid with blocking `Stop` gates and a dedicated `GateConfig` engine.
- **Reality**: Per [specs/enforcement/enforcement.md](file:///Users/suzor/src/academicOps/specs/enforcement/enforcement.md), the gate pyramid is retired. In-session hook logic is stripped down to [`aops/hooks/router.py`](file:///Users/suzor/src/academicOps/aops/hooks/router.py) (131 lines), `PostToolUse` is unhooked, and `Stop` hook blocking is commented out. True enforcement has shifted entirely to GitHub Actions CI (`lint.yml`, `pytest.yml`, `typecheck.yml`, `rbg-review.yml`). Note that `.github/workflows/pr-pipeline.yml` is currently an empty stub.

### 6. Retired Script Drift

- **Issue**: Older installation guides referenced `scripts/install.py`.
- **Reality**: `scripts/install.py` has been retired because it drifted out of sync with the modular package layout. Local installation must be done via `make install-dev` (which runs `scripts/build.py` and `scripts/install_automode.py`).

### 7. Build System Platform Workarounds

- **AGY MCP Path Workaround**: In `scripts/build.py`, Antigravity targets require absolute path expansion using `bash -c` and `~` because `antigravity-cli#390` fails to resolve `${extensionPath}` and executes MCP servers from the workspace `cwd`.
- **AGY Router Hook Unquoting**: Router hook commands in `hooks.json` are modified during Antigravity builds to strip quotes around script paths because AGY executes commands via `argv` array without shell expansion.

### 8. Duplication of Axioms and Rules

- Axioms are stored as markdown files in [`.agents/rules/`](file:///Users/suzor/src/academicOps/.agents/rules), indexed in [`.agents/AXIOMS.md`](file:///Users/suzor/src/academicOps/.agents/AXIOMS.md), and mirrored under [`aops/axioms/`](file:///Users/suzor/src/academicOps/aops/axioms). Care must be taken when updating axioms to maintain single-source-of-truth consistency across build outputs.

---

## 6. Practical Field Guide & Rules for Future Agents

When working on the **academicOps** repository, agents must adhere to the following rules:

### A. Pre-Flight Checklist Before Scoping Changes

1. Check [`.agents/CORE.md`](file:///Users/suzor/src/academicOps/.agents/CORE.md) and [`.agents/rules/`](file:///Users/suzor/src/academicOps/.agents/rules/) for project-specific binding rules.
2. Read relevant specs under [`specs/`](file:///Users/suzor/src/academicOps/specs) (e.g. `specs/FLOW-MAP.md`, `specs/enforcement/enforcement.md`, `specs/packaging/v0.5-modular-topology.md`).

### B. Project Routing Constraint (`rename-impossible`)

When creating or updating tasks in the PKB:

- Use the correct `project` field: `mem` (PKB code/graph), `aops` (framework/skills/hooks/polecat), `qut` (teaching/unit ops).
- **CRITICAL**: The task ID prefix is permanently bound at task creation time (e.g., `mem-abc123`). `update_task` cannot rename an existing task ID!

### C. Native Edit Rule (Strict Halt Invariant)

- **NEVER** use bash heredocs, `python3 -c`, `sed -i`, or `awk` to edit tracked files.
- Always use native file edit tools (`replace_file_content`, `write_to_file`, `multi_replace_file_content`).

### D. Verification & Testing Requirements

- Run `uv run pytest tests/` or `uv run pytest aops/` to verify python code changes.
- Run `python3 scripts/build.py` to ensure build scripts assemble valid plugins without errors.

### E. Session Handover & Friction Logging

- **Leave a loose thread**: Always create/file the next PKB task before ending a turn or finishing a phase so work is never dropped.
- **Log friction unilateral**: When hitting tool limits, ambiguous specs, or broken paths, recommend the `/learn` slash command immediately to log friction.
