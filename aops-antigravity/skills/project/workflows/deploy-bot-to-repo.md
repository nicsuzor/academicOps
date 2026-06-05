---
id: deploy-bot-to-repo
name: deploy-bot-to-repo
category: operations
bases: []
description: Deploy aops bot automation (PR review, merge prep, QA agents) to an existing GitHub repository
permalink: workflows/deploy-bot-to-repo
tags: [workflow, deployment, github, automation, ci]
version: 1.0.0
---

# Deploy aops Bot Automation to a Repository

**Purpose**: Add aops bot automation (PR review, merge prep, async QA) to an
existing repo so it reviews PRs with the universal axioms plus project context.

**Owner**: `/project` skill. **Invoke** when onboarding a repo or upgrading its
tier. Current deployment state lives in [[DEPLOYMENTS|specs/DEPLOYMENTS.md]].

**Prerequisites**: `gh` CLI authed with `repo` + `workflow` scopes; GitHub Actions enabled on the target; rights to set repo secrets.

## Tiers

- **Light** — `claude.yml` (@claude handler) + `pr-review.yml`. Small/low-activity
  repos. Secret: `CLAUDE_CODE_OAUTH_TOKEN` (via `claude setup-github`).
- **Full** — adds `pr-pipeline.yml`/`pr-review-pipeline.yml`, `agent-enforcer.yml`,
  `agent-merge-prep.yml`, `merge-prep-cron.yml`, and `.github/agents/*` prompts.
  Active repos. Also needs `AOPS_BOT_GH_TOKEN` (PAT for pushes).

## Steps (full deployment)

### 1. Scaffold project context

The repo needs `.agents/CORE.md` with project context (Key Components + Agent
Rules) — run `/project` to scaffold or create it by hand. Without it, reviews are generic.

### 2. Install workflows and agent prompts

```bash
AOPS=$(pwd)                      # academicOps repo root
TARGET=~/src/<target-repo>
mkdir -p "$TARGET/.github/workflows" "$TARGET/.github/agents"
cp "$AOPS/.github/workflows/claude.yml" "$TARGET/.github/workflows/"   # Light: this only
# Full: also copy pipeline workflows + agent prompts:
cp "$AOPS"/.github/agents/{pr-reviewer,qa,enforcer}.agent.md "$TARGET/.github/agents/"
```

Pipeline workflows are tuned for academicOps CI — adapt per target: lint/test
commands, default branch (buttermilk uses `dev`), concurrency groups, required checks.

### 3. Configure secrets

```bash
REPO=<owner/repo>
cd "$TARGET" && claude setup-github               # sets CLAUDE_CODE_OAUTH_TOKEN
gh secret set AOPS_BOT_GH_TOKEN --repo "$REPO"    # full tier only
```

### 4. Provision canonical labels

```bash
REPO=<owner/repo>
gh label create task        --color 0e8a16 --description "Discrete unit of work"              --force --repo "$REPO"
gh label create bug         --color d73a4a --description "Defect or regression"               --force --repo "$REPO"
gh label create enhancement --color a2eeef --description "Improvement to existing capability" --force --repo "$REPO"
gh label create triage      --color fbca04 --description "Needs initial triage"               --force --repo "$REPO"
gh label create polecat     --color 5319e7 --description "PR authored by a polecat worker"    --force --repo "$REPO"
```

### 5. Commit, push, verify

```bash
cd "$TARGET"
git add .github/ .agents/
git commit -m "ci: add aops bot automation (PR review + merge prep)"
git push
gh secret list --repo "$REPO"; gh workflow list --repo "$REPO"
```

Open a test PR; confirm the bot reviews within minutes. Record the new
deployment in [[DEPLOYMENTS|specs/DEPLOYMENTS.md]].

## Install scripts

| Script                                      | What it does                                                                   |
| ------------------------------------------- | ------------------------------------------------------------------------------ |
| `scripts/install-pr-reviewer.sh <path>`     | Copies pr-reviewer agent + workflow, sets secrets                              |
| `scripts/install-async-qa-agents.sh <path>` | Copies hydrator-reviewer + enforcer-reviewer agents + async-qa-review workflow |
| `scripts/install-brain-workflows.sh`        | Installs PKB consolidation workflows to brain repo                             |

`install-pr-reviewer.sh` references `pr-review.yml` (may be renamed — verify source paths first). This procedure is authoritative.

## Troubleshooting

- **`startup_failure` on the pipeline** — the `workflow_run` trigger can't match the
  upstream workflow; `on.workflow_run.workflows[]` must match the name exactly and
  that workflow must exist on the default branch.
- **Generic reviews** — `.agents/CORE.md` missing; the reviewer reads it for context.
- **Secrets failing** — re-run `claude setup-github`; `CLAUDE_CODE_OAUTH_TOKEN` must
  be an OAuth token, not a PAT.
