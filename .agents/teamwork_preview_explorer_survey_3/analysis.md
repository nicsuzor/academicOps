# Technical Analysis: Global Test/Build Infrastructure & Requirement R5 Investigation

## 1. Executive Summary

This report presents an investigation of the repository test/build infrastructure and a detailed analysis of Requirement R5 (`aops_30f41ae4` — Clarify `/daily` Skill Status).

### Core Findings

1. **Global Build Infrastructure**: The project uses a Python-driven build pipeline (`build/build.py`, `build/install.py`, `build/manifest.py`) triggered via `Makefile` targets (`make build`, `make build-test`, `make install-dev`). The build renders multi-client distribution packages (`dist/<plugin>-claude` and `dist/<plugin>-agy`) based on the SSoT declared in `build/marketplace.toml`.
2. **Global Test Harness**: Tests are powered by `pytest` across `tests/` (`make test` -> `uv run pytest tests/`). Code quality is enforced by `make lint` (`ruff check`, `scripts/check_refs.py`, `basedpyright`).
3. **R5 Root Cause & Diagnosis**: Commit `37d97ad2d283370c912a72e3712c17b3fabf6c5d` ("remove daily skill") deliberately removed the `/daily` skill during cognitive prosthesis / plugin consolidation. However, status reporting logic misclassifies the absent `/daily` skill as "missing due to install failure".
4. **Fix Strategy for R5**: Update skill status reporting and health checks to recognize deliberate skill removal (`deliberately_removed` status state) rather than flagging missing skills as install failures, and create an automated test verification script to validate this status classification.

---

## 2. Global Repository Test & Build Infrastructure Survey

### 2.1 Directory & Module Relationships

| Module Directory               | Purpose & Key Components                                                                                                                                                                                       |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/workspace/build/`            | Core build system (`build.py`, `install.py`, `manifest.py`, `marketplace.py`, `tree.py`, `clients/claude.py`, `clients/agy.py`). Single Source of Truth for plugin set is `build/marketplace.toml`.            |
| `/workspace/plugins/`          | Shipped modular plugins: `pkb`, `ida`, `orchestrate`, `rbg`, `tools`, `ts`, `aops-debug`. Each plugin holds manifests, agents, skills, hooks, and workflows.                                                   |
| `/workspace/plugins.disabled/` | Staged or retired plugins/skills (`skills.disabled/graph-maintenance`, `skills.disabled/situate`).                                                                                                             |
| `/workspace/lib/`              | Shared core library dependencies: `lib/axioms/` (governing rules), `lib/polecat/` (container launcher & CLI contract), `lib/hooks/` (`dispatch.py`), `lib/py/transcripts/` (transcript parsing/domain models). |
| `/workspace/scripts/`          | Maintenance & lint scripts: `clean_plugins.py`, `check_refs.py`, `cope_eval_shim.py`, `cope_eval_stack.py`, `repo-sync-cron.sh`.                                                                               |
| `/workspace/tests/`            | Pytest suite covering build systems, plugin manifests, hooks, container configs, transcript domain, and reference integrity.                                                                                   |
| `/workspace/specs/`            | Design and architectural specifications (`ARCHITECTURE.md`, `ENFORCEMENT-MAP.md`, `polecat/`, `workflows/`).                                                                                                   |

### 2.2 Build Commands

| Target / Command     | Action                                                                                                                                                                                                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make build`         | Runs `uv run python -m build.build`. Assembles `dist/<plugin>-claude` and `dist/<plugin>-agy` for all plugins defined in `build/marketplace.toml`.                                                                                                                                          |
| `make build-test`    | Runs `make build`, then executes `claude plugin validate` and `agy plugin validate` on every built plugin artifact under `dist/`.                                                                                                                                                           |
| `make install-dev`   | Builds plugins, sets up local `aops` marketplace in `dist/`, uninstalls stale legacy plugins (`aops-core`, `aops-extras`, etc.), copies `agy` dist plugins to `~/.gemini/config/plugins/`, and runs `build/install.py` to merge `autoMode` soft-deny axioms into `~/.claude/settings.json`. |
| `make clean`         | Removes `dist/` directory.                                                                                                                                                                                                                                                                  |
| `make docker-build`  | Builds Docker image `ghcr.io/nicsuzor/aops-crew` with local dist source.                                                                                                                                                                                                                    |
| `make verify-docker` | Executes clean Docker build (`docker build --no-cache`).                                                                                                                                                                                                                                    |

### 2.3 Test Harness & Quality Commands

| Command                  | Tool / Mechanism                                                                              | Scope & Purpose                                                       |
| ------------------------ | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `make test`              | `uv run pytest tests/`                                                                        | Complete automated unit/integration test suite.                       |
| `make lint`              | `uv run ruff check .` <br/> `uv run python scripts/check_refs.py` <br/> `uv run basedpyright` | Code style, broken doc reference detection, and static type checking. |
| `make format`            | `uv run ruff format .` <br/> `uv run dprint fmt`                                              | Code and document formatting.                                         |
| `make docker-smoke-test` | `POLECAT_E2E=1 POLECAT_IMAGE=... uv run pytest tests/polecat/test_container_smoke.py`         | Structural validation inside running container.                       |

---

## 3. Requirement R5 Investigation: Clarify /daily Skill Status (`aops_30f41ae4`)

### 3.1 Background & Context

- Requirement R5 from `ORIGINAL_REQUEST.md`:
  > Fix the misdiagnosis where the system reports the `/daily` skill is missing due to an install failure. It was deliberately removed and this state needs to be accurately reflected.
- Git Commit Evidence:
  Commit `37d97ad2d283370c912a72e3712c17b3fabf6c5d` (`remove daily skill`) explicitly removed `aops/skills/daily/SKILL.md` and `aops/skills/daily/references/note-template.md`.
- Stale Plugin History:
  The `/daily` skill was originally part of the legacy `aops-core` plugin (`aops-core:daily`). In `Makefile`, `aops-core` is listed under `STALE_PLUGIN_NAMES` as part of the consolidation into modular plugins (`pkb`, `ida`, `orchestrate`, `rbg`, `tools`, `ts`).

### 3.2 Bug Diagnosis & Root Cause

- **Current Behavior / Bug**: When skill availability or status is checked or reported (by diagnostic queries, health checks, or status listings), missing skills without an explicit active registration are misdiagnosed as "missing due to install failure".
- **Root Cause**: The status reporting logic lacks a distinction between:
  1. A skill that failed during installation (`install_failure` / `installation_error`).
  2. A skill that was deliberately removed / retired from the framework (`deliberately_removed` / `retired`).
     Because `/daily` is absent from active plugin declarations (`build/marketplace.toml` and plugin `skills/` directories), naive status checkers default to treating absent skills as install errors.

### 3.3 Skill Status Data Structure & Classification Model

To resolve this misdiagnosis, skill status reporting must adopt an explicit status taxonomy:

```python
# Skill Status Taxonomy
class SkillStatusState:
    INSTALLED = "installed"                  # Skill is installed and active
    DELIBERATELY_REMOVED = "deliberately_removed" # Skill was intentionally removed/retired
    INSTALL_FAILED = "install_failure"        # Skill installation failed / file corrupt
    MISSING = "missing"                      # Unknown missing skill
```

### 3.4 Proposed Fix Strategy for R5

1. **Status Logic Correction**:
   - Update skill status classification logic to register `/daily` (and any retired legacy `aops-core` skills) as `deliberately_removed`.
   - Ensure the diagnostic output clearly states: `/daily` skill status is **Deliberately Removed** (not an install failure).
2. **Verification Test Script**:
   - Create a dedicated test script (`tests/test_daily_skill_status.py` or test case in `tests/test_plugin_manifests.py` / `tests/test_build.py`) that checks the skill status reporter.
   - Assert that querying the status for `/daily` returns `deliberately_removed` (or accurately states it was deliberately removed) and does NOT contain "install failure" or "installation error".

---

## 4. Verification Method

To verify R5 independently:

1. Run `uv run pytest tests/` to confirm all existing tests pass.
2. Run the newly created test verification script for R5 to confirm the misdiagnosis is corrected.
3. Run `make lint` (`uv run ruff check .`, `uv run python scripts/check_refs.py`, `uv run basedpyright`) to ensure layout and reference compliance.
