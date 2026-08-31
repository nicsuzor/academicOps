# Init — Project Scaffolding Procedure

Execute after Phase 1 discovery, using the user's answers about project type,
tooling, and preferences.

## Operating principles

- **Check before you create.** Before any step that creates external state
  (repo, PKB node, polecat entry), check whether it already exists. If it does,
  HALT and let the user choose to resume, rename, or abort — never overwrite or
  duplicate.
- **Never roll back on partial failure.** A half-scaffolded repo is
  recoverable; a half-deleted one is not. Report what succeeded, what failed,
  and the exact command to resume from the failure point.
- **Keep a running log** of what you created. Step 9 prints it whether or not
  you reached the end.

## Step 1: Create the GitHub repository

```bash
gh repo view <org>/<project-name> >/dev/null 2>&1 && echo "EXISTS"
```

If it exists, HALT and ask the user to (a) pick a different name, (b) resume
scaffolding inside the existing repo (clone, then Step 2), or (c) abort.

Otherwise:

```bash
gh repo create <org>/<project-name> --<visibility> --clone
cd <project-name>
git checkout -B main  # ensure default branch (creates or resets to main)
```

To initialise an existing local directory instead, skip repo creation and work
in place. On failure (auth, name collision, network) HALT and print the error —
nothing local exists yet.

## Step 2: Base structure (all projects)

### `.agents/CORE.md`

Write a project title, a one-line statement of what the project is and why it
exists, a **Key Components** list matching the directories actually created, a
**Development** section (`uv sync`, `uv run`, `uv run pytest`,
`pre-commit run --all-files`), and an **Agent Rules** section carrying:

- Check the repo before asking the user — if a file answers the question, read it.
- Search the PKB before creating tasks or proposing plans.
- Research data is immutable: never modify, convert, or "fix" source datasets,
  ground-truth labels, or raw outputs.
- Edit files with Read/Write/Edit, never a heredoc, `python3 -c`, `sed`, or
  `awk` against a tracked file. If the native tool cannot do the job, STOP and
  report rather than shelling out.

Add project-specific rules from the Phase 1 conversation (e.g. dbt-first
analysis, Quarto rendering conventions).

### `CLAUDE.md`

```markdown
@.agents/CORE.md

**RESEARCH DATA IS IMMUTABLE**: Source datasets and ground truth labels are
SACRED. NEVER modify, convert, reformat, or "fix" them. If infrastructure
doesn't support the data format, HALT and report the gap.

## Data freshness

- Authoritative source: <upstream warehouse or dataset the user named>
- Local cache lives at: <path the user chose>
- Refresh script: `scripts/refresh.sh`
- Stale means: <project-author's call>
- If the cache is missing or stale, the dispatched worker HALTs and reports. It does not regenerate silently.
```

For a tool/library project, replace the immutability line with the project's
primary constraint and drop the Data freshness section.

### `.claude/settings.json`

Research repos open as **Ida**. Write the shared default so every session in
the repo picks it up; the schema host must be `json.schemastore.org`:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "agent": "ida"
}
```

Track this file — it carries the shared default. Machine-local overrides go in
the gitignored `.claude/settings.local.json`. For a tool/library project, omit
the `"agent"` key so sessions use the baseline default.

### `README.md`

Title, description from Phase 1, **Status** (Setup | Active | Analysis |
Writing | Complete), **Architecture** (tooling and directory layout), **Setup**
(`git clone`, `cd`, `uv sync`, `pre-commit install`), **Directory Layout** (the
tree actually created), and **Team**.

### `.gitignore`

Standard Python, secrets/credentials, OS, and IDE ignores, plus the entries the
selected tooling needs — drop the sections for tooling not selected:

```gitignore
# Claude Code / academicOps — settings.json is intentionally TRACKED
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
```

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

For notebook projects add `nbstripout` (`https://github.com/kynan/nbstripout`,
rev `0.7.1`, hook id `nbstripout`).

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

Add dependencies for the Phase 1 selections (e.g. `dbt-duckdb`, `quarto`,
`mlflow`, `dvc`).

## Step 3: Documentation stubs

Create these for all projects, so documentation happens because the structure
exists rather than because someone remembers.

- **`docs/METHODOLOGY.md`** — Research Questions, Data Sources, Analytical
  Approach, and Reproducibility (environment locked via `uv.lock`; data
  versioning approach; computation caching approach; `scripts/refresh.sh` if
  generated). Leave each section as an HTML comment prompt.
- **`docs/ETHICS.md`** — Ethics Approval (status, reference, approving body),
  Data Handling (storage, access controls, retention), and an AI/LLM Disclosure
  stating that AI tools are used for code generation and review, data pipeline
  development, and document formatting, and that all analytical decisions and
  interpretations are made by the research team.
- **`CHANGELOG.md`** — `## [Unreleased]` / `### Added` / `- Initial project
  scaffolding`.

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

### Issue templates

`.github/ISSUE_TEMPLATE/task.yml` — name "Task", label `task`, a required
`priority` dropdown (`1`, `2`, `3`) and a required `description` textarea.

`.github/ISSUE_TEMPLATE/bug_report.yml` — name "Bug Report", label `bug`, two
required textareas: "What happened?" and "What did you expect?".

The priority dropdown is for a human filing an issue. An agent creating a task
programmatically leaves `intent`/`priority` at the uncurated default; only Nic
sets a non-default band, by express per-request instruction
([[framework-conventions-summary#intent-authority]]).

### Canonical labels

Provision the framework's canonical label set: GitHub does not auto-create
labels from a template's `labels:` field, and `gh pr edit --add-label` against
a missing label fails with exit 1. `--force` makes this idempotent.

```bash
# Issue-template defaults (referenced by .github/ISSUE_TEMPLATE/*.yml)
gh label create task        --color "0e8a16" --description "Discrete unit of work"               --force
gh label create bug         --color "d73a4a" --description "Defect or regression"                --force
gh label create enhancement --color "a2eeef" --description "Improvement to existing capability"  --force
gh label create triage      --color "fbca04" --description "Needs initial triage"                --force

# PR triage routing
gh label create "triage:escalate"       --color "b60205" --description "PR needs human attention (CI failed / stalled)" --force
gh label create "triage:stale"          --color "cccccc" --description "Open >7d without merge or update"               --force
gh label create "triage:auto-mergeable" --color "0e8a16" --description "Bot-authored, CI green, safe to auto-merge"     --force
gh label create "triage:needs-judgment" --color "fbca04" --description "Human-authored, needs review judgment"          --force

# Issue-sweep dispositions (consumed by the triage skill, sweep mode)
gh label create "triaged-stale"   --color "ededed" --description "Sweep: closed as stale"            --force
gh label create "triaged-duplicate" --color "ededed" --description "Sweep: merged into canonical"     --force
gh label create "triaged-evidence-bump" --color "ededed" --description "Sweep: evidence added to canonical" --force
gh label create "triaged-single"  --color "ededed" --description "Sweep: filed as single polecat task" --force
gh label create "triaged-epic"    --color "ededed" --description "Sweep: filed as fix-epic"         --force
gh label create "triaged-defer"   --color "ededed" --description "Sweep: deferred; revisit-by date set" --force

# Criticality (used by triage + sweep when filing/triaging issues)
gh label create "criticality:critical" --color "b60205" --description "Production-blocking or data-integrity risk" --force
gh label create "criticality:high"     --color "d93f0b" --description "Material impact on workflows"               --force
gh label create "criticality:medium"   --color "fbca04" --description "Noticeable but contained"                   --force
gh label create "criticality:low"      --color "0e8a16" --description "Polish, minor friction"                     --force

# PR origin
gh label create polecat --color "5319e7" --description "PR authored by a polecat worker" --force
```

If the `gh` token lacks `repo:write` on the new repo this fails here rather
than silently downstream — file a token-scope task and HALT.

## Step 5: Research tooling (only what Phase 1 selected)

### Data directories (empirical research)

```
data/
  raw/         # Immutable source data
  processed/   # Derived outputs (parquet, csv)
src/           # Execution code, API scripts, prompt templates
```

Tell the user the defaults: `data/raw/` is immutable (DVC-tracked or
gitignored, never modified); raw LLM outputs go to JSONL (schema-flexible,
human-readable, fine-tuning compatible); analytical tables go to Parquet
(columnar, compressed, fast under DuckDB); DuckDB is the default local
analytical database, so small teams need no cloud warehouse.

### dbt

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

**`dbt_project/models/schema.yml`**:

```yaml
version: 2
sources:
  - name: raw
    description: Raw source data
    tables: []
```

Also create `dbt_project/models/staging/.gitkeep` and
`dbt_project/models/marts/.gitkeep` so the staging → marts pattern is visible,
`data/cache/.gitignore` containing `*`, and an executable `scripts/refresh.sh`:

```bash
#!/bin/bash
# Rebuild the local DuckDB cache from BigQuery/source
uv run dbt build --project-dir dbt_project --profiles-dir dbt_project
```

### Quarto

**`manuscript/_quarto.yml`** (manuscript format; adjust `project.type` for
website or book):

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

Also create `manuscript/index.qmd` (frontmatter with title, author name and
affiliation, `date: today`, an abstract placeholder, then an `## Introduction`
stub) and an empty `manuscript/references.bib`.

For multi-chapter projects with dbt/DuckDB selected, add
**`manuscript/_setup.qmd`** for shared imports:

```python
#| label: setup
#| include: false

from pathlib import Path
import duckdb
import pandas as pd

# Connect to project DuckDB via absolute canonical path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "<project_name>.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)
```

### MLflow

Add `mlflow` to `pyproject.toml` dependencies and create `experiments/`.
`mlruns/` is already gitignored.

### DVC

```bash
dvc init
dvc remote add -d storage <remote-path>  # configure with user
```

Track `data/raw/` with DVC; commit `.dvc/` and keep `data/raw/` gitignored.

## Step 6: Documentation index

Create `.agents/INDEX.md` listing every documentation file created — at
minimum `README.md`, `.agents/CORE.md`, and `docs/METHODOLOGY.md` where
applicable — each with a one-line description. `CORE.md` includes it via
`@.agents/INDEX.md`, which is how any agent discovers the repo's docs.

## Step 7: PKB integration

Search for duplicates first, because project nodes are long-lived and two nodes
for one project leave tasks split across both:

```
mcp__services__pkb__task_search(query="<project title or slug>", limit=10)
```

If a `type=project` node with a matching title or slug exists, HALT and ask the
user to (a) link work to the existing node, (b) rename to disambiguate, or (c)
abort. Otherwise:

```
mcp__services__pkb__create_task(
  title="Project: <title>",
  type="project",
  body="<description from Phase 1>",
  tags=["project-<slug>"],
  parent=<goal-id if specified>
)
```

Record the returned node ID in the running log. If creation fails, note it and
continue to Step 8 — the repo works without a PKB node and the user can retry
the same command later.

## Step 8: Git, pre-commit, and polecat registration

```bash
uv sync                           # install Python dependencies
pre-commit install                # activate hooks
git add -A
git commit -m "feat: initial project scaffolding"
git push -u origin main
```

If `uv sync` or `pre-commit install` fails, continue — the user can re-run
them. Commit and push are load-bearing: if either fails, HALT and report the
exact retry command. Do not delete the local repo.

### Register with polecat

Registration is git-native and portable: edit the sessions repo's
`polecat.yaml`, commit, push. Paths resolve at read time by convention
(`$AOPS_SRC_DIR/<repo>`), with overrides in `$POLECAT_HOME/local.yaml`, so no
machine-local data belongs in the registry.

```bash
# $AOPS_SESSIONS is the sessions repo (e.g. <org>/sessions)
cd "$AOPS_SESSIONS"
git pull --rebase                 # avoid stale-write conflicts
grep -E "^\s*<slug>:" "$AOPS_SESSIONS/polecat.yaml" && echo "EXISTS"
```

If the slug already appears, HALT and ask whether to reuse it, rename, or
abort. Otherwise append (no `path:` — that is machine-local):

```yaml
<slug>:
  repo: <repo-name>               # optional, defaults to slug
  default_branch: main
  mounts:                              # optional, for empirical projects
    - host: $AOPS_SESSIONS/secrets/<slug>/
      container: /run/secrets/project/
      mode: ro
```

```bash
git add polecat.yaml
git commit -m "chore(projects): register <slug>"
git push
```

Then tell the user: on other machines, `git pull` in `$AOPS_SESSIONS` and run
`setup-machine.sh`. A repo at the conventional location
(`$AOPS_SRC_DIR/<repo>`) needs nothing further; otherwise add a `paths:` entry
to `$POLECAT_HOME/local.yaml`.

If the sessions push fails (auth, conflict), the local repo and PKB node are
already in place — the user retries this step manually. Do not unwind earlier
work.

## Step 9: Report

Print what was created, what failed, and what was deliberately deferred, so the
user never has to guess which parts are done. Say at the top if any step HALTed
for idempotency, and make the summary match what actually happened.

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

  0. Project credentials (research projects): create a scoped service account
     for this project's data and drop the JSON at
     `$AOPS_SESSIONS/secrets/<slug>/sa.json`. The polecat launcher mounts that
     directory read-only at dispatch time.

  1. GitHub OAuth token for Claude Code workflows:
     cd <path> && claude setup-github
     (Provisions CLAUDE_CODE_OAUTH_TOKEN. Do NOT set it by hand with
     `gh secret set` — the built-in mechanism is the supported path.)

  2. Async QA agents (optional):
     $AOPS/scripts/install-async-qa-agents.sh <path>

  3. Branch protection: not set — solo project default.

  4. CI/CD beyond claude.yml: not configured.

  5. Polecat on other machines:
     polecat sync && $AOPS/scripts/setup-machine.sh

Start working:
  cd <path> && claude
```
