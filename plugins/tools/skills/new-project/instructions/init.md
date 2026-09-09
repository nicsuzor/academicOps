# Init -- Project Scaffolding Procedure

Execute after discovery approval, using the user's choices for tooling and layout.

## Operating principles

- **Check before creating**: Halt and prompt if repo, PKB node, or polecat entry already exists -- never overwrite.
- **Never rollback on partial failure**: Report what succeeded, what failed, and the exact retry command.
- **Maintain a running log** of created assets for the final report.

## Step 1: GitHub repository

```bash
gh repo view <org>/<name> >/dev/null 2>&1 && echo "EXISTS" || \
  gh repo create <org>/<name> --<visibility> --clone && cd <name> && git checkout -B main
```

If repo exists, halt and prompt user: rename, adopt existing, or abort. For local init, work in-place.

## Step 2: Base configuration files

Generate the following core files using minimal project templates:

- **`.agents/CORE.md`**: Title, one-line purpose, key directory list, development commands (`uv sync`, `uv run pytest`, `pre-commit run --all-files`), and rules: check repo first, search PKB before tasks, research data is immutable, edit files with native file tools only.
- **`CLAUDE.md`**: Include `@.agents/CORE.md`, immutable data notice, and data freshness section (authoritative source, local cache path, refresh script, staleness definition).
- **`.claude/settings.json`**:
  ```json
  {
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "agent": "ida"
  }
  ```
  Omit `"agent"` for non-research tool/library repos.
- **`README.md`**: Title, description, status badge, architecture, setup steps (`uv sync`, `pre-commit install`), directory tree, and team.
- **`.gitignore`**: Ignore `.claude/settings.local.json`, `.academicOps/`, standard Python caches (`.venv/`, `__pycache__/`), secrets, OS files, and selected tool artifacts (`data/raw/`, `*.parquet`, `*.duckdb`, `_site/`, `_freeze/`, `target/`, `dbt_packages/`, `mlruns/`).
- **`.pre-commit-config.yaml`**: Standard hooks from `pre-commit-hooks` (trailing-whitespace, end-of-file-fixer, check-yaml, `check-added-large-files` with `--maxkb=500`), `ruff-pre-commit` (ruff `--fix`, ruff-format `--check`), and `nbstripout` if notebooks are used.
- **`pyproject.toml`**: Minimal PEP 621 config with `requires-python = ">=3.11"`, `[tool.ruff]` (target-version "py311", line-length 120, lint select `["E", "F", "I", "UP"]`), `[tool.pytest.ini_options]` (`testpaths = ["tests"]`), and selected project dependencies.

## Step 3: Documentation stubs

Create baseline markdown stubs:

- **`docs/METHODOLOGY.md`**: Research questions, data sources, analytical approach, and reproducibility parameters.
- **`docs/ETHICS.md`**: Approvals, data handling/retention, and AI/LLM disclosures.
- **`CHANGELOG.md`**: Initial `[Unreleased]` entry for scaffolding.

## Step 4: GitHub infrastructure

- **`.github/workflows/claude.yml`**: Trigger on issue/PR comments and issue open/assign containing `@claude`. Run `anthropics/claude-code-action@v1` using `secrets.CLAUDE_CODE_OAUTH_TOKEN` with permissions `contents: read`, `pull-requests: read`, `issues: read`, `id-token: write`, `actions: read`.
- **Issue templates**: `.github/ISSUE_TEMPLATE/task.yml` (priority dropdown `1/2/3`, description) and `bug_report.yml` (what happened, expected).
- **Canonical labels**: Provision idempotently with `gh label create <name> --color <hex> --description <desc> --force`:
  - Workflow: `task` (0e8a16), `bug` (d73a4a), `enhancement` (a2eeef), `triage` (fbca04).
  - PR triage: `triage:escalate` (b60205), `triage:stale` (cccccc), `triage:auto-mergeable` (0e8a16), `triage:needs-judgment` (fbca04).
  - Issue sweep: `triaged-stale`, `triaged-duplicate`, `triaged-evidence-bump`, `triaged-single`, `triaged-epic`, `triaged-defer` (all ededed).
  - Criticality: `criticality:critical` (b60205), `criticality:high` (d93f0b), `criticality:medium` (fbca04), `criticality:low` (0e8a16).
  - Origin: `polecat` (5319e7).

## Step 5: Research tooling (selected only)

- **Empirical data**: Create `data/raw/` (immutable source data), `data/processed/`, and `src/`.
- **dbt**: Create `dbt_project/` with `dbt_project.yml`, `profiles.yml` (DuckDB target at `../data/processed/<name>.duckdb`), `models/schema.yml` (declaring `sources: [raw]`), `models/staging/.gitkeep`, `models/marts/.gitkeep`, `data/cache/.gitignore` (`*`), and executable `scripts/refresh.sh` running `uv run dbt build`.
- **Quarto**: Create `manuscript/_quarto.yml` (type: manuscript, `execute: {freeze: true, echo: false}`, bibliography: `references.bib`), `manuscript/index.qmd`, empty `references.bib`, and optional `_setup.qmd` for read-only DuckDB connection.
- **MLflow / DVC**: If chosen, add `mlflow` to deps and create `experiments/`; run `dvc init`, configure remote, and track `data/raw/`.

## Step 6: Documentation index

Create `.agents/INDEX.md` listing `README.md`, `.agents/CORE.md`, `docs/METHODOLOGY.md`, and all created guides. Reference it from `.agents/CORE.md` via `@.agents/INDEX.md`.

## Step 7: PKB integration

Check for existing node, then create:

```python
results = mcp__services__pkb__task_search(query="<title or slug>", limit=10)
# If matching project node exists, halt and prompt user. Else:
mcp__services__pkb__create_task(
  title="Project: <title>",
  type="project",
  body="<description>",
  tags=["project-<slug>"],
  parent=<goal_id> # if specified
)
```

## Step 8: Git & polecat registration

```bash
uv sync && pre-commit install
git add -A && git commit -m "feat: initial project scaffolding" && git push -u origin main
```

Register in `$AOPS_SESSIONS/polecat.yaml`:

```bash
cd "$AOPS_SESSIONS" && git pull --rebase
# Ensure slug not present, then append:
# <slug>:
#   repo: <repo-name>
#   default_branch: main
#   mounts: [{host: "$AOPS_SESSIONS/secrets/<slug>/", container: "/run/secrets/project/", mode: "ro"}]
git add polecat.yaml && git commit -m "chore(projects): register <slug>" && git push
```

## Step 9: Report

Output summary of created assets, failures with retry commands, and deferred actions:

1. Scoped data credentials at `$AOPS_SESSIONS/secrets/<slug>/sa.json`.
2. GitHub OAuth token: `cd <path> && claude setup-github`.
3. Async QA agents: `$AOPS/scripts/install-async-qa-agents.sh <path>`.
4. Run `cd <path> && claude` to begin work.
