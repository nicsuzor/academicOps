# Init -- Project Scaffolding Procedure

Execute after discovery approval, using the user's choices for tooling and layout.

## Operating Principles

- **Check before creating**: Halt and prompt (or report in headless workflows) if the repository or PKB project node already exists -- never overwrite.
- **No rollback on partial failure**: Report what succeeded, what failed, and the exact retry command; log created assets for the final report.

## Step 1: Repository Setup

Check `gh repo view <org>/<name>` first; if absent, run `gh repo create <org>/<name> --<visibility> --clone && cd <name> && git checkout -B main`. For local init, work in-place.

## Step 2: Base Configuration and Documentation

Create minimal files matching approved selections:

- **`.agents/CORE.md`** and **`.agents/INDEX.md`**: Project title, one-line purpose, directory layout, commands (`uv sync`, `uv run pytest`, `pre-commit run --all-files`), operational rules (immutable research data, native file edits), and an index listing `README.md`, `.agents/CORE.md`, `docs/METHODOLOGY.md`, and created guides (referenced via `@.agents/INDEX.md`).
- **`AGENTS.md`**: Universal operational instructions, immutable data notice, and data freshness contract (authoritative source, cache path, refresh script, staleness threshold).
- **`.claude/settings.json`**: Minimal schema-backed client settings (`https://json.schemastore.org/claude-code-settings.json`), adding a default project agent only when needed.
- **`README.md`**, **`CHANGELOG.md`**, **`docs/METHODOLOGY.md`**, **`docs/ETHICS.md`**: Project overview and setup, initial `[Unreleased]` entry, research questions and reproducibility parameters, and ethics/retention/AI disclosures.
- **`.gitignore`**: Ignore `.claude/settings.local.json`, Python caches (`.venv/`, `__pycache__/`), secrets, OS files, and selected tool outputs (`data/raw/`, `*.parquet`, `*.duckdb`, `_site/`, `_freeze/`, `target/`, `dbt_packages/`, `mlruns/`).
- **`.pre-commit-config.yaml`**, **`.markdownlint-cli2.jsonc`**, **`.markdownlint-rules/no-horizontal-rules.js`**: Standard `pre-commit-hooks` (whitespace, YAML, `--maxkb=500`), `markdownlint-cli2` (banning horizontal dividers via H39), formatter, `ruff-pre-commit`, and `nbstripout` when notebooks are used.
- **`pyproject.toml`**: PEP 621 metadata (`requires-python = ">=3.11"`), `[tool.ruff]` (`target-version = "py311"`, `line-length = 120`, `["E", "F", "I", "UP"]`), `[tool.pytest.ini_options]` (`testpaths = ["tests"]`), and selected dependencies.

## Step 3: GitHub Infrastructure

- **CI & issue templates**: Add CI/automation workflows as selected, plus `.github/ISSUE_TEMPLATE/task.yml` (`1/2/3` priority, description) and `bug_report.yml`.
- **Canonical labels**: Provision idempotently via `gh label create <name> --color <hex> --description <desc> --force` for workflow (`task`, `bug`, `enhancement`, `triage`), PR triage (`triage:escalate`, `triage:stale`, `triage:auto-mergeable`, `triage:needs-judgment`), issue sweep (`triaged-stale`, `triaged-duplicate`, `triaged-evidence-bump`, `triaged-single`, `triaged-epic`, `triaged-defer`), and criticality (`criticality:critical|high|medium|low`).

## Step 4: Selected Research Tooling

- **Empirical data**: Create `data/raw/` (immutable source data), `data/processed/`, and `src/`.
- **dbt**: Create `dbt_project/` with `dbt_project.yml`, `profiles.yml` (DuckDB target at `../data/processed/<name>.duckdb`), `dbt_project/models/schema.yml` (`sources: [raw]`), `staging/` and `marts/` `.gitkeep`s, `data/cache/.gitignore` (`*`), and executable `scripts/refresh.sh` (`uv run dbt build`).
- **Quarto**: Create `manuscript/_quarto.yml` (`type: manuscript`, `execute: {freeze: true, echo: false}`, `bibliography: references.bib`), `manuscript/index.qmd`, empty `references.bib`, and optional `_setup.qmd` for read-only DuckDB reads.
- **MLflow / DVC**: Add `mlflow` to dependencies and create `experiments/`, or run `dvc init`, configure remote, and track `data/raw/`.

## Step 5: PKB Registration and Initial Push

When PKB registration is directed by the composed workflow, search PKB for `<title or slug>`; if found, halt and prompt (or report in headless workflows). Otherwise create the project node (`title: "Project: <title>"`, `type: "project"`, `body: "<description>"`, `tags: ["project-<slug>"]`, optional `parent: "<goal_id>"`).

Sync the environment and create the initial commit; run `git push -u origin main` when directed by the composed workflow and permitted by repository permissions:

```bash
uv sync && pre-commit install
git add -A && git commit -m "feat: initial project scaffolding"
# git push -u origin main  # run when directed by the composed workflow and repository permissions
```

When directed by the composed workflow and host permissions, register the new repository in the environment's project registry (and configure read-only secret mounts if container execution is used).

## Step 6: Report

Output created assets, any failures with exact retry commands, and manual next steps for the user:

1. Place scoped data credentials in the project's secret mount path if required.
2. Configure repository CI/GitHub integration tokens.
3. Open `<path>` in the agent client to begin work.
