# Init — Project Scaffolding Procedure

Execute this procedure after Phase 1 discovery. You have the user's answers
about project type, tooling, and preferences. Now build it.

## Operating principles

- **Idempotency first.** Before each step that creates external state (repo, PKB
  node, polecat entry), check whether it already exists. If it does, HALT and
  report — do not overwrite or create a duplicate. The user can decide whether
  to resume, rename, or abort.
- **No rollback on partial failure.** If a later step fails, do NOT tear down
  earlier steps. Report exactly what succeeded, what failed, and the exact
  command to resume from the failure point. A half-scaffolded repo is
  recoverable; a half-deleted one is not.
- **Collect a running log** of what you created as you go. You will print this
  in Step 9 regardless of whether you reached the end or bailed out early.

## Step 1: Create the GitHub repository

First, check for an existing repo (idempotency):

```bash
gh repo view <org>/<project-name> >/dev/null 2>&1 && echo "EXISTS"
```

If it exists, **HALT**. Tell the user the repo is already registered and ask
whether they want to (a) pick a different name, (b) resume scaffolding inside
the existing repo (skip to Step 2 after cloning), or (c) abort. Do not proceed
without an explicit decision.

If it does not exist, create it:

```bash
gh repo create <org>/<project-name> --<visibility> --clone
cd <project-name>
git checkout -B main  # ensure default branch (creates or resets to main)
```

If the user wants to initialise an existing local directory instead, skip repo
creation and work in place.

On failure (auth error, name collision, network): HALT. Nothing has been
created locally yet — no rollback needed. Print the error and stop.

## Step 2: Base structure (all projects)

Create these files for every project, regardless of type.

### `.agents/CORE.md`

Adapt this template based on Phase 1 answers:

```markdown
# <Project Title>

<One-line description of what the project is and why it exists.>

## Key Components

- `src/` — execution code, scripts, prompt templates
- `data/` — datasets (raw is immutable, processed is derived)
- `docs/` — methodology, ethics, project documentation

## Agent Rules

- **Check the repo before asking the user.** If a question about project state
  could be answered by reading a file, READ THE FILE FIRST.
- **Search PKB first.** Before creating tasks or proposing plans, search for
  existing work, prior decisions, and related artifacts.
- **Research data is immutable.** Source datasets, ground truth labels, and raw
  outputs are sacred. Never modify, convert, or "fix" them.

## Development

- **Python**: `uv sync` to install, `uv run` to execute
- **Tests**: `uv run pytest`
- **Formatting**: `pre-commit run --all-files`
```

Adjust the Key Components section to reflect the actual directories created.
Add project-specific rules from the Phase 1 conversation (e.g. dbt-first
analysis, Quarto rendering conventions).

### `CLAUDE.md`

```markdown
@.agents/CORE.md

**RESEARCH DATA IS IMMUTABLE**: Source datasets and ground truth labels are
SACRED. NEVER modify, convert, reformat, or "fix" them. If infrastructure
doesn't support the data format, HALT and report the gap.

## Data freshness

- Authoritative source: <e.g. BigQuery `prosocial-443205.toxicity`>
- Local cache lives at: <e.g. `data/cache/local_cache.duckdb`>
- Refresh script: `scripts/refresh.sh`
- Stale means: <project-author's call — e.g. "older than the most recent BQ load timestamp">
- If the cache is missing or stale, the dispatched worker HALTs and reports. It does not regenerate silently.
```

For non-research projects (tool/library), omit the research data line and
replace with the project's primary constraint. Also omit the Data freshness
section if not applicable.

### `.claude/settings.json` — default to Ida for research repos

Research project repos open as **Ida** (the interactive academic-research head
personality) by default. Write the shared default-agent setting so every
session launched in the repo picks it up automatically (mechanism: the
top-level `"agent"` key — mem-e7b976da; the schema URL must be
`json.schemastore.org`, not `json-schema.org`):

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "agent": "ida"
}
```

This file is **git-tracked** (it carries the shared agent default, so it must
travel with the repo — see the `.gitignore` note below); machine-local
overrides go in `.claude/settings.local.json`, which stays gitignored. For a
non-research tool/library project, omit the `"agent"` key (those default to
Junior).

### `README.md`

````markdown
# <Project Title>

<Description from Phase 1.>

## Status

**Phase**: Setup | Active | Analysis | Writing | Complete

## Architecture

<Brief overview of tooling and directory layout.>

## Setup

```bash
git clone <repo-url>
cd <project-name>
uv sync
pre-commit install
```

## Directory Layout

```
<generated tree of what was actually created>
```

## Team

- <PI / lead researcher>
````

### `.gitignore`

Generate a comprehensive `.gitignore` covering all selected tooling:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
dist/
*.egg-info/

# Environment and secrets
.env
.env.local
.env.*.local
credentials/
*.key
*.pem

# Claude Code / academicOps
# NOTE: .claude/settings.json is intentionally TRACKED — it carries the shared
# repo defaults (e.g. "agent": "ida" so research repos open as Ida). Only the
# machine-local override file is ignored.
.claude/settings.local.json
.claude/agents/
.academicOps/

# Data (large files — use DVC if version tracking needed)
data/raw/
*.parquet
*.duckdb
*.db

# Quarto outputs
_site/
_book/
_manuscript/
_freeze/
.quarto/

# dbt
target/
dbt_packages/
logs/

# Experiment tracking
mlruns/

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
```

Remove sections for tooling not selected (e.g. drop dbt section if no dbt).

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
        args: [--check]
```

If the project uses Jupyter notebooks, add `nbstripout`:

```yaml
- repo: https://github.com/kynan/nbstripout
  rev: 0.7.1
  hooks:
    - id: nbstripout
```

### `pyproject.toml`

```toml
[project]
name = "<project-name>"
version = "0.1.0"
description = "<one-line description>"
requires-python = ">=3.11"
dependencies = []

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Add tool-specific dependencies based on Phase 1 selections (e.g. `dbt-duckdb`,
`quarto`, `mlflow`, `dvc`).

## Step 3: Documentation stubs

Create these for all projects. They ensure documentation happens because the
files exist and have structure — not because someone remembers to create them.

### `docs/METHODOLOGY.md`

```markdown
# Methodology

## Research Questions

<!-- State the primary research questions this project addresses. -->

## Data Sources

<!-- Describe data sources, collection methods, and access requirements. -->

## Analytical Approach

<!-- Describe the analytical methods, tools, and pipeline architecture. -->

## Reproducibility

- **Environment**: Python dependencies locked via `uv.lock`
- **Data versioning**: <DVC / git-ignored snapshots / describe approach>
- **Computation caching**: <Quarto freeze / describe approach>
- **Data refresh**: `scripts/refresh.sh` (if generated) — rebuilds local DuckDB cache from source.
```

### `docs/ETHICS.md`

```markdown
# Ethics and Data Governance

## Ethics Approval

<!-- Status, reference number, approving body. -->

## Data Handling

<!-- Storage, access controls, retention policy. -->

## AI/LLM Disclosure

This project uses AI tools (Claude Code, academicOps framework) for:

- Code generation and review
- Data pipeline development
- Document formatting

All analytical decisions and interpretations are made by the research team.
```

### `CHANGELOG.md`

```markdown
# Changelog

## [Unreleased]

### Added

- Initial project scaffolding
```

## Step 4: GitHub infrastructure

### `.github/workflows/claude.yml`

```yaml
name: Claude Code

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]
  pull_request_review:
    types: [submitted]

jobs:
  claude:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review' && contains(github.event.review.body, '@claude')) ||
      (github.event_name == 'issues' && (contains(github.event.issue.body, '@claude') || contains(github.event.issue.title, '@claude')))
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write
      actions: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Run Claude Code
        uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          additional_permissions: |
            actions: read
```

### `.github/ISSUE_TEMPLATE/task.yml`

This dropdown is for a **human** filing an issue. When an agent creates a task programmatically it follows the intent-authority rule instead — leave `priority` at the uncurated default; only Nic sets a non-default band, by express per-request instruction ([[framework-conventions-summary#intent-authority]]).

```yaml
name: Task
description: Create a task for this project
labels: ["task"]
body:
  - type: dropdown
    id: priority
    attributes:
      label: Priority
      options:
        - "1"
        - "2"
        - "3"
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Description
    validations:
      required: true
```

### `.github/ISSUE_TEMPLATE/bug_report.yml`

```yaml
name: Bug Report
description: Report a bug
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: What happened?
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What did you expect?
    validations:
      required: true
```

### Canonical labels

Provision the framework's canonical label set on the new repo. Issue templates and the `repo-sync-cron` triage pipeline assume these exist — GitHub does **not** auto-create labels from `labels:` fields in issue templates, and `gh pr edit --add-label` against a missing label fails with exit 1 (which historically caused `pr-state.json` to bail mid-write; see aops-2a4d0d47).

`gh label create --force` is idempotent — safe to re-run on existing repos.

```bash
# Issue-template defaults (referenced by .github/ISSUE_TEMPLATE/*.yml)
gh label create task        --color "0e8a16" --description "Discrete unit of work"               --force
gh label create bug         --color "d73a4a" --description "Defect or regression"                --force
gh label create enhancement --color "a2eeef" --description "Improvement to existing capability"  --force
gh label create triage      --color "fbca04" --description "Needs initial triage"                --force

# PR triage routing (consumed by aops-core/scripts/dump_pr_state.py)
gh label create "triage:escalate"       --color "b60205" --description "PR needs human attention (CI failed / stalled)" --force
gh label create "triage:stale"          --color "cccccc" --description "Open >7d without merge or update"               --force
gh label create "triage:auto-mergeable" --color "0e8a16" --description "Bot-authored, CI green, safe to auto-merge"     --force
gh label create "triage:needs-judgment" --color "fbca04" --description "Human-authored, needs review judgment"          --force

# Issue-sweep dispositions (consumed by aops-core/skills/survey, sweep mode)
gh label create "triaged-stale"   --color "ededed" --description "Sweep: closed as stale"            --force
gh label create "triaged-duplicate" --color "ededed" --description "Sweep: merged into canonical"     --force
gh label create "triaged-evidence-bump" --color "ededed" --description "Sweep: evidence added to canonical" --force
gh label create "triaged-single"  --color "ededed" --description "Sweep: filed as single polecat task" --force
gh label create "triaged-epic"    --color "ededed" --description "Sweep: filed as fix-epic"         --force
gh label create "triaged-defer"   --color "ededed" --description "Sweep: deferred; revisit-by date set" --force

# Criticality (used by survey + sweep when filing/triaging issues)
gh label create "criticality:critical" --color "b60205" --description "Production-blocking or data-integrity risk" --force
gh label create "criticality:high"     --color "d93f0b" --description "Material impact on workflows"               --force
gh label create "criticality:medium"   --color "fbca04" --description "Noticeable but contained"                   --force
gh label create "criticality:low"      --color "0e8a16" --description "Polish, minor friction"                     --force

# PR origin
gh label create polecat --color "5319e7" --description "PR authored by a polecat worker" --force
```

If the cron's `gh` token lacks `repo:write` on the new repo, label provisioning will fail loudly here rather than silently downstream — file a token-scope task and HALT per the fail-fast rule.

## Step 5: Research tooling (conditional)

Only create these if the user selected them in Phase 1.

### Data directories (empirical research)

```
data/
  raw/         # Immutable source data
  processed/   # Derived outputs (parquet, csv)
src/           # Execution code, API scripts, prompt templates
```

Key defaults to communicate:

- `data/raw/` is **immutable** — tracked by DVC or `.gitignored`, never modified
- Raw LLM outputs → JSONL format (schema-flexible, human-readable, fine-tuning compatible)
- Analytical tables → Parquet format (columnar, compressed, fast for DuckDB queries)
- DuckDB as default local analytical database — no cloud warehouse needed for small teams

### dbt (if selected)

Create `dbt_project/` with working configuration:

**`dbt_project/dbt_project.yml`**:

```yaml
name: '<project_name>'
version: '1.0.0'
profile: '<project_name>'

model-paths: ["models"]
test-paths: ["tests"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]
```

**`dbt_project/profiles.yml`**:

```yaml
'<project_name>':
  target: dev
  outputs:
    dev:
      type: duckdb
      path: '../data/processed/<project_name>.duckdb'
      threads: 4
```

**`dbt_project/models/staging/.gitkeep`** and
**`dbt_project/models/marts/.gitkeep`** — these directories should exist to
show the medallion architecture pattern (staging → marts).

**`dbt_project/models/schema.yml`**:

```yaml
version: 2
sources:
  - name: raw
    description: Raw source data
    tables: []
```

**`scripts/refresh.sh`** (executable):

```bash
#!/bin/bash
# Rebuild the local DuckDB cache from BigQuery/source
uv run dbt build --project-dir dbt_project --profiles-dir dbt_project
```

**`data/cache/.gitignore`**:

```gitignore
*
```

### Quarto (if selected)

Create the manuscript/report directory with working configuration.

**`manuscript/_quarto.yml`** (for manuscript format):

```yaml
project:
  type: manuscript

manuscript:
  article: index.qmd

execute:
  freeze: true    # Cache outputs — re-run only when source changes
  echo: false     # Hide code in rendered output by default

bibliography: references.bib
csl: apa.csl
```

Adjust `project.type` for website or book formats as requested.

**`manuscript/index.qmd`**:

```markdown
---
title: "<Project Title>"
author:
  - name: "<Author>"
    affiliation: "<Institution>"
date: today
abstract: |
  <!-- Abstract goes here. -->
---

## Introduction

<!-- Begin writing here. -->
```

**`manuscript/references.bib`**: empty file (placeholder)

**`manuscript/_setup.qmd`** (shared imports for multi-chapter projects):

```python
#| label: setup
#| include: false

import duckdb
import pandas as pd

# Connect to project DuckDB
con = duckdb.connect("../data/processed/<project_name>.duckdb", read_only=True)
```

Only include `_setup.qmd` if dbt/DuckDB is also selected.

### MLflow (if selected)

Add to `pyproject.toml` dependencies: `mlflow`.

Create `experiments/` directory. Add `mlruns/` to `.gitignore` (already in
the base template).

### DVC (if selected)

```bash
dvc init
dvc remote add -d storage <remote-path>  # configure with user
```

Add `data/raw/` to DVC tracking. Ensure `.dvc/` is committed but
`data/raw/` is in `.gitignore`.

## Step 6: Documentation Index

Create `.agents/INDEX.md`. This plain-text index makes the repo's documentation discoverable by any agent via the `@.agents/INDEX.md` include in `CORE.md`.

```markdown
# Available Documentation

- **`README.md`**: Project overview, architecture, and installation
- **`.agents/CORE.md`**: Core architecture decisions, agent instructions, and project rules
- **`docs/METHODOLOGY.md`**: (if applicable) Research methods and design
```

Add any other documentation created in earlier steps to this list.

## Step 7: PKB integration

**Search for duplicates first.** Project nodes are long-lived; two nodes for
the same project cause downstream confusion (which tasks hang off which?).

```
mcp__pkb__task_search(query="<project title or slug>", limit=10)
```

Inspect the results. If a `type=project` node with a matching title or slug
already exists, **HALT** and ask the user: (a) link work to the existing node,
(b) rename the new project to disambiguate, or (c) abort. Do not create a
second node silently.

If no duplicate exists, create the project node:

```
mcp__pkb__create_task(
  title="Project: <title>",
  type="project",
  body="<description from Phase 1>",
  tags=["project-<slug>"],
  parent=<goal-id if specified>
)
```

Record the returned node ID in your running log — Step 9 will reference it.
If creation fails, note the failure and continue to Step 8; the repo is still
usable without a PKB node, and the user can retry later with the same command.

## Step 8: Git, pre-commit, and polecat registration

Initial commit and push:

```bash
uv sync                           # install Python dependencies
pre-commit install                # activate hooks
git add -A
git commit -m "feat: initial project scaffolding"
git push -u origin main
```

If `uv sync` or `pre-commit install` fails (missing tool, locked file, network):
continue anyway — they can be re-run by the user. Commit and push are the
load-bearing steps; if either of those fails, HALT and report the exact command
to retry. Do not delete the local repo.

### Register with polecat (git-native propagation)

Per decision `epic-fe52f422`, polecat registration is git-native: edit the
sessions repo's `polecat.yaml`, commit, and push. The registry is portable —
no machine-local data lives in it. Path resolution happens at read-time via
convention (`$AOPS_SRC_DIR/<repo>`) with overrides in
`$POLECAT_HOME/local.yaml`.

```bash
# $AOPS_SESSIONS is the sessions repo (e.g. nicsuzor/sessions)
cd "$AOPS_SESSIONS"
git pull --rebase                 # avoid stale-write conflicts
```

Check for an existing entry before appending (idempotency):

```bash
grep -E "^\s*<slug>:" "$AOPS_SESSIONS/polecat.yaml" && echo "EXISTS"
```

If the slug already appears, **HALT** and ask the user whether to reuse it,
rename, or abort. Otherwise append (note: no `path:` — that's machine-local):

```yaml
<slug>:
  repo: <repo-name>               # optional, defaults to slug
  default_branch: main
  mounts:                              # optional, for empirical projects
    - host: $AOPS_SESSIONS/secrets/<slug>/
      container: /run/secrets/project/
      mode: ro
```

Commit and push:

```bash
git add polecat.yaml
git commit -m "chore(projects): register <slug>"
git push
```

Then tell the user: on other machines, run `git pull` in `$AOPS_SESSIONS` and
then `setup-machine.sh`. If the repo lives at the conventional location
(`$AOPS_SRC_DIR/<repo>`) nothing further is required; otherwise add a `paths:`
entry to `$POLECAT_HOME/local.yaml`.

If the sessions repo push fails (auth, conflict): the local repo and PKB node
are already in place — the user can retry this step manually. Do not unwind
earlier work.

## Step 9: Report

Print a summary covering three things: what was created, what failed (if
anything), and what was deliberately deferred to the user. Be explicit — the
user should not need to guess which parts are done.

```
Project '<name>' — scaffolding report

Repository: https://github.com/<org>/<name>
Local path: <path>
PKB node:   <task-id or "not created">

Created:
  <directory tree of what was actually scaffolded>

Failed (if any):
  <step name>: <error, and the exact command to retry>

Deferred to user (by design):

  0. Project Credentials (for research projects):
     Before dispatching analytic work, create a scoped service account for this
     project's data and drop the JSON at `$AOPS_SESSIONS/secrets/<slug>/sa.json`.
     The polecat launcher mounts
     that directory read-only at dispatch time. (No 1Password, no env-file
     ceremony. One human action, once.)

  1. GitHub OAuth token for Claude Code workflows (per decision epic-2964b83a):
     cd <path> && claude setup-github
     (This provisions CLAUDE_CODE_OAUTH_TOKEN automatically. Do NOT set it by
     hand with `gh secret set` — the built-in mechanism is the supported path.)

  2. Async QA agents (optional):
     $AOPS/scripts/install-async-qa-agents.sh <path>

  3. Branch protection: not set — solo project default. Enable in GitHub
     settings if the project grows a team.

  4. CI/CD beyond claude.yml: not configured. Add workflows as needed.

  5. Polecat on other machines:
     polecat sync && $AOPS/scripts/setup-machine.sh

Start working:
  cd <path> && claude
```

If any step HALTed for idempotency (existing repo, duplicate PKB node,
existing polecat slug), the report should say so clearly at the top — the user
resumed or aborted, and the summary should match reality.
