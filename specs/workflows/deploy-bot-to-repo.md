# Deploying aops Automation to a Repository

How to add aops bot automation (PR review, merge prep, QA agents) to an
existing GitHub repository. This covers the manual process — the install
scripts automate parts of it but may need updating as workflows evolve.

## Prerequisites

- `gh` CLI authenticated with a token that has `repo` and `workflow` scopes
- The target repo has GitHub Actions enabled
- Access to set secrets on the target repo

## Quick Reference: Current Deployments

| Repo                  | Tier  | Workflows                                                                                       | Agents                                      |
| --------------------- | ----- | ----------------------------------------------------------------------------------------------- | ------------------------------------------- |
| nicsuzor/academicOps  | Full  | pr-pipeline, agent-enforcer, agent-merge-prep, merge-prep-cron, claude                          | pr-reviewer, enforcer, qa                   |
| qut-dmrc/buttermilk   | Full  | pr-review-pipeline, agent-merge-prep, agent-qa, agent-strategic-review, claude, merge-prep-cron | custodiet, gatekeeper, qa, strategic-review |
| nicsuzor/mem          | Full  | pr-pipeline, agent-enforcer, agent-merge-prep, merge-prep-cron                                  | pr-reviewer, enforcer, custodiet, qa        |
| nicsuzor/brain        | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/explorations | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/omcp         | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/zotmcp       | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/labeler      | Light | pr-review, claude                                                                               | —                                           |

## Deployment Tiers

### Tier 1: Light (claude.yml + pr-review)

Minimal bot presence — Claude Code responds to @claude mentions and reviews
PRs. Suitable for small/low-activity repos.

**What gets installed:**

- `.github/workflows/claude.yml` — @claude mention handler
- `.github/workflows/pr-review.yml` — PR review trigger (if standalone workflow exists)

**Secrets needed:**

- `CLAUDE_CODE_OAUTH_TOKEN` — provision via `claude setup-github` in the repo

### Tier 2: Full (review pipeline + merge prep + QA)

Full automation — PR review pipeline, axiom enforcement, merge preparation,
QA agents. Suitable for active repos with regular PRs.

**What gets installed:**

- `.github/workflows/claude.yml` — @claude mention handler
- `.github/workflows/pr-pipeline.yml` or `pr-review-pipeline.yml` — review pipeline
- `.github/workflows/agent-enforcer.yml` — axiom compliance reviewer
- `.github/workflows/agent-merge-prep.yml` — merge preparation agent
- `.github/workflows/merge-prep-cron.yml` — periodic merge-prep dispatcher
- `.github/agents/` — agent prompts (pr-reviewer, enforcer, qa, etc.)

**Secrets needed:**

- `CLAUDE_CODE_OAUTH_TOKEN` — provision via `claude setup-github`
- `AOPS_BOT_GH_TOKEN` — PAT for push operations (set via `gh secret set`)

## Step-by-Step: Full Deployment

### 1. Scaffold project context

The target repo needs an `.agent/CORE.md` (or `.agents/CORE.md`) with
project-specific context. The `/project` skill can scaffold this:

```text
/project   # interactive scaffolding for new repos
```

For existing repos, create `.agent/CORE.md` manually:

```markdown
# <Project Name>

<One-line description.>

## Key Components

- `src/` — source code
- `tests/` — test suite

## Agent Rules

- Check the repo before asking the user.
- Search PKB first before creating tasks.
```

### 2. Install workflows and agent prompts

Clone the target repo and copy files from academicOps:

```bash
# From the academicOps repo root
AOPS=$(pwd)
TARGET=~/src/<target-repo>

# Minimal: claude.yml only
mkdir -p "$TARGET/.github/workflows"
cp "$AOPS/.github/workflows/claude.yml" "$TARGET/.github/workflows/"

# Full: copy agent prompts and all pipeline workflows
mkdir -p "$TARGET/.github/agents"
cp "$AOPS/.github/agents/pr-reviewer.agent.md" "$TARGET/.github/agents/"
cp "$AOPS/.github/agents/qa.agent.md" "$TARGET/.github/agents/"
cp "$AOPS/.github/agents/enforcer.agent.md" "$TARGET/.github/agents/"

# Copy pipeline workflows — adapt filenames and triggers for the target repo
# The source pr-pipeline.yml may need modification for repos with different
# CI structure (different test commands, linters, etc.)
```

**Important:** The pipeline workflows in academicOps are tuned for this
repo's CI structure. For other repos, you'll likely need to adapt:

- Lint/typecheck/test commands
- Default branch name (buttermilk uses `dev`, most others use `main`)
- Concurrency group naming
- Required status checks

### 3. Configure secrets

```bash
REPO=<owner/repo>

# Preferred: use Claude's built-in setup
cd $TARGET && claude setup-github

# Or manually:
gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo $REPO
gh secret set AOPS_BOT_GH_TOKEN --repo $REPO  # for full tier
```

### 4. Provision canonical labels

The triage pipeline expects standard labels. Run from the target repo:

```bash
REPO=<owner/repo>
gh label create task        --color "0e8a16" --description "Discrete unit of work"               --force --repo $REPO
gh label create bug         --color "d73a4a" --description "Defect or regression"                --force --repo $REPO
gh label create enhancement --color "a2eeef" --description "Improvement to existing capability"  --force --repo $REPO
gh label create triage      --color "fbca04" --description "Needs initial triage"                --force --repo $REPO
gh label create polecat     --color "5319e7" --description "PR authored by a polecat worker"     --force --repo $REPO
```

### 5. Commit, push, verify

```bash
cd $TARGET
git add .github/ .agent/
git commit -m "ci: add aops bot automation (PR review + merge prep)"
git push
```

### 6. Verify the deployment

```bash
# Check secrets are set
gh secret list --repo $REPO

# Check workflow registration
gh workflow list --repo $REPO

# Trigger a manual review (if workflow supports workflow_dispatch)
gh workflow run "PR Pipeline" --repo $REPO -f pr_number=<N>

# Check recent runs
gh run list --repo $REPO --limit 5
```

Open a test PR and verify the bot posts a review within a few minutes.

## Install Scripts

Existing install scripts automate parts of this process:

| Script                                      | What it does                                          |
| ------------------------------------------- | ----------------------------------------------------- |
| `scripts/install-pr-reviewer.sh <path>`     | Copies pr-reviewer agent + workflow, sets secrets     |
| `scripts/install-async-qa-agents.sh <path>` | Copies hydrator-reviewer + enforcer agents + workflow |
| `scripts/install-brain-workflows.sh`        | Installs PKB consolidation workflows to brain repo    |

**Note:** `install-pr-reviewer.sh` references `.github/workflows/pr-review.yml`
which may not exist if the workflow has been renamed. Verify source paths
before running. The manual process above is the authoritative reference.

## Troubleshooting

### PR Pipeline shows `startup_failure`

Usually means the `workflow_run` trigger can't find the triggering workflow.
Check that the referenced workflow name in `on.workflow_run.workflows[]`
matches exactly. The workflow must exist on the repo's default branch.

### Bot reviews are generic / not context-aware

Ensure `.agent/CORE.md` (or `.agents/CORE.md`) exists with project-specific
context. The PR reviewer reads this file to understand local conventions.

### Secrets not working

Re-provision with `claude setup-github` or verify with `gh secret list`.
The `CLAUDE_CODE_OAUTH_TOKEN` must be a valid OAuth token, not a PAT.
