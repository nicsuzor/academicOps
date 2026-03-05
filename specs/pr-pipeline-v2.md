---
title: PR Pipeline v2
type: spec
category: workflow
status: active
created: 2026-03-04
supersedes: specs/pr-process.md
---

# PR Pipeline v2

## Giving Effect

- [[.github/workflows/code-quality.yml]] → split into [[.github/workflows/lint.yml]] + [[.github/workflows/typecheck.yml]]
- [[.github/workflows/agent-merge-prep.yml]] → rewrite: drop LGTM gate, cron-driven, post `gh pr review --approve` on success, add `workflow_dispatch` trigger (already exists in current impl), add loop ceiling check, set `merge-prep-status` commit status on success and on halt
- [[.github/workflows/merge-prep-cron.yml]] → simplify: 10-min cron, label-free qualification (commit status replaces comment-text scanning)
- [[.github/workflows/agent-conceptual-review.yml]] → rename to [[.github/workflows/agent-review.yml]], switch to `gh pr review`
- [[.github/workflows/summary-and-merge.yml]] → **new**: environment-gated merge workflow
- [[.github/rulesets/pr-review-and-merge.yml]] → add Pytest to required status checks
- [[.github/agents/merge-prep.agent.md]] → remove commit-status instructions, add PR review approval, add loop-ceiling logic
- [[.github/agents/conceptual-review.agent.md]] → update to use `gh pr review` instead of commit status
- GitHub Environment: **production** → required reviewer: repository maintainer(s)

## Overview

**As** the repository maintainer,
**I want** a PR pipeline where bots handle all preparation automatically on a timer,
**So that** when I look at a PR, it is already reviewed, fixed, and ready — and I approve once to merge.

The previous pipeline ([[specs/pr-process.md]]) required a human LGTM to trigger merge-prep. This created a sequencing problem: merge-prep fixes failing checks, so it cannot wait for checks to pass before running. The new design inverts the dependency — merge-prep runs automatically on a cron, bots prepare everything, and the human approves or denies once at the end.

## Design Principles

1. **Bots prepare, human decides.** All mechanical work (lint fixes, review triage, conflict resolution) happens before the human looks at the PR. The human's job is approval or rejection, not preparation.
2. **Single decision point.** The human approves (or denies) once via a GitHub Environment gate. Merge is immediate after approval.
3. **No labels for coordination.** Labels are unreliable state machines. In-progress detection uses `gh run list`; halt state uses the `merge-prep-status` commit status API. No load-bearing labels; no comment-text scanning.
4. **Environment gate for graduation.** Merge-prep signals readiness by triggering a `summary-and-merge.yml` workflow. Job 1 posts a decision brief (summary of all changes, reviews, and fixes). Job 2 requires the `production` environment — the maintainer clicks "Approve" in the GitHub UI to merge. One click, no PR comment archaeology needed.
5. **Cron replaces LGTM dispatch.** Merge-prep runs every 10 minutes on all qualifying PRs. No human trigger needed, no label gate, no event chain to break.
6. **Independence.** Every check runs independently on every push. Lint does not gate Type Check. Type Check does not gate Pytest. If Lint autofixes and pushes, the others re-run on the new commit without waiting.
7. **GitHub affordances only.** Required status checks, PR reviews, commit status API, environments, and auto-merge handle state. No custom orchestration where GitHub provides a native mechanism. No comment parsing; no label-based state machines.

## Architecture: Four Phases

```mermaid
flowchart TD
    PR["PR opened / push"]

    %% Phase 1: On every push — independent, deterministic
    PR --> Lint["<b>Lint</b><br/>Autofix + push if needed<br/><i>Required status check</i>"]
    PR --> TC["<b>Type Check</b><br/>basedpyright<br/><i>Required status check</i>"]
    PR --> Test["<b>Pytest</b><br/>Unit tests<br/><i>Required status check</i>"]
    PR --> SR["<b>Agent Review</b><br/>gh pr review: APPROVE or REQUEST_CHANGES"]

    Lint --> LintFix{Issues?}
    LintFix -- Yes --> AutoFix["Autofix + push commit"]
    AutoFix --> PR
    LintFix -- No --> Phase2

    TC --> Phase2
    Test --> Phase2
    SR --> SRV{Verdict}
    SRV -- REQUEST_CHANGES --> Blocked["<b>Merge blocked</b><br/>Author revises"]
    SRV -- APPROVE --> Phase2["<b>Bazaar window</b><br/>External reviews arrive naturally<br/>(Gemini, Copilot, commenters)"]

    %% Phase 2: Cron — no human trigger needed
    Phase2 --> Cron["<b>Cron: every 10 min</b><br/>Finds PRs ≥ 15 min old<br/>No in-progress run"]

    Cron --> MP["<b>Merge Prep</b><br/>Triage ALL review feedback<br/>Fix issues, resolve conflicts<br/>Run lint + typecheck + tests<br/>Push fixes"]
    MP --> MPV{Outcome}
    MPV -- Failure --> RetryOrEscalate["Retry next cron tick<br/>After 3 failures: set commit<br/>status failure, notify"]
    MPV -- Success --> Trigger["<b>Trigger summary-and-merge.yml</b><br/>Posts decision brief"]

    %% Phase 3: Environment gate
    Trigger --> EnvGate{"<b>Environment: production</b><br/>Maintainer clicks Approve<br/>in GitHub UI"}
    EnvGate -- "Approve" --> Merge
    EnvGate -- "Reject" --> Blocked

    %% Phase 4: Merge
    Merge["<b>Squash merge + delete branch</b><br/>via gh pr merge"]

    %% Styling
    classDef check fill:#e8f4fd,stroke:#2196f3
    classDef agent fill:#fff3e0,stroke:#ff9800
    classDef human fill:#e8f5e9,stroke:#4caf50
    classDef success fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef fail fill:#ffebee,stroke:#f44336
    classDef cron fill:#f3e5f5,stroke:#9c27b0
    classDef env fill:#fce4ec,stroke:#e91e63

    class Lint,TC,Test check
    class SR,MP agent
    class EnvGate human
    class Merge success
    class Blocked fail
    class Cron cron
```

## Phase 1: On Every Push (Deterministic Checks)

All four jobs run concurrently and independently on every `pull_request` push. No job waits for another.

| Workflow     | File               | Job name       | Required check?     | Action                                                        |
| ------------ | ------------------ | -------------- | ------------------- | ------------------------------------------------------------- |
| Lint         | `lint.yml`         | `Lint`         | Yes                 | `ruff check --fix` + `ruff format`. Autofix + push if needed. |
| Type Check   | `typecheck.yml`    | `Type Check`   | Yes                 | `basedpyright`. Read-only.                                    |
| Pytest       | `pytest.yml`       | `Pytest`       | Yes                 | `pytest -m "not requires_local_env"`. Read-only.              |
| Agent Review | `agent-review.yml` | `Agent Review` | Via required review | Advisory + judgment. Posts `gh pr review`.                    |

**Lint autofix loop:** When Lint pushes a fix commit, the new push re-triggers all four workflows on the new commit. Type Check and Pytest were never waiting for Lint — they re-run on the fixed commit naturally.

**Agent Review uses `gh pr review`, not commit status.** PR reviews are GitHub's native mechanism for "does this change look right?" A `REQUEST_CHANGES` review blocks merge natively via branch protection, with no custom status machinery needed.

**Note on custodiet-reviewer:** The existing `custodiet-reviewer` agent may also run during Phase 1. It is advisory and does not block merge. The spec does not prescribe its trigger or output format — it can continue as-is or be folded into the Agent Review workflow in future.

## Phase 2: Merge Prep (Cron-Driven)

Merge Prep runs on a 10-minute cron. It finds all qualifying PRs and processes each one.

### Qualification criteria (label-free)

A PR qualifies for merge-prep if ALL of the following are true:

1. **Age gate:** Last commit was >= 15 minutes ago. This preserves a bazaar window for external reviews (Gemini, Copilot) to arrive before merge-prep triages them.
2. **No in-progress run:** `gh run list --workflow=agent-merge-prep.yml --json status` shows no `in_progress` or `queued` run for this PR. Replaces the `merge-prep-running` label.
3. **Not already completed or permanently halted:** The latest commit does not have a `merge-prep-status` commit status (via `gh api repos/{owner}/{repo}/commits/{sha}/statuses`) with `state: success` or `state: failure`. Merge-prep sets `success` at the end of every successful run (preventing redundant re-processing if no new commits have arrived); it sets `failure` after 3 consecutive failures. A new commit from any actor clears this automatically — the new SHA has no status yet, so merge-prep will re-run. Replaces the `merge-prep-failed` label and comment-text scanning.

The cron dispatcher does not check whether checks are passing. Merge-prep runs regardless — it will fix what it can and post an honest outcome.

### What Merge Prep does

1. **Dismiss prior merge-prep approval** — `gh pr review --dismiss` any existing approval from `github-actions[bot]` on this PR (ensures approval always reflects the latest code state, not a prior run).
2. Checks for a self-loop (last commit has `Merge-Prep-By:` trailer — skip if so).
3. Checks the runaway loop ceiling (see below) — halt if exceeded.
4. Resolves merge conflicts if present (`git merge origin/main --no-edit`).
5. Reads ALL GitHub PR review feedback: Agent Review, external bots (Gemini, Copilot), human reviewers. Triages each piece: fix, dismiss, or defer.
6. Runs `ruff check --fix && ruff format`, `basedpyright`, `pytest` locally.
7. Commits and pushes fixes with `Merge-Prep-By: agent` trailer (if any fixes are needed).
8. Posts a triage summary comment.
9. Posts `gh pr review --approve` (satisfies `required_approving_review_count: 1` in branch protection, and ensures approval always reflects this run's output).
10. Sets `merge-prep-status: success` commit status on the latest commit.
11. Triggers `summary-and-merge.yml` via `gh workflow run` (or `workflow_dispatch`).

**No comment parsing.** Merge-prep reads GitHub PR _reviews_ (step 5) — a structured, native GitHub mechanism. It does not scan arbitrary comment text for instructions. Human direction comes through the review mechanism (REQUEST_CHANGES with notes), not freeform comments.

### Graduation mechanism: Environment gate

Merge-prep signals readiness by triggering **`summary-and-merge.yml`**, which:

- **Job 1 (summary):** Posts a decision brief comment on the PR — a concise summary of what changed, what reviews said, what merge-prep fixed, and what's left. The human reads this one comment, not 30 scattered review threads.
- **Job 2 (merge):** Requires the `production` environment. The maintainer sees the summary, clicks "Approve" in the GitHub Environments UI, and the PR merges automatically.

Merge-prep still posts `gh pr review --approve` (step 9 above) to satisfy the `required_approving_review_count: 1` branch protection rule. The environment gate supplements this: rather than the human providing a second approval in the PR review UI (same interface, same comment thread), the human decides via the Actions environment gate — a clean, separate UI that presents only the decision brief and an Approve/Reject button.

**Why GitHub Environments?** The maintainer's stated requirement is "I want a summary and a decision, not a bunch of PR comments." Environments provide exactly this: a clean gate with a single approval button, separate from the PR review thread. The decision brief gives context; the environment gate gives the action.

### Global concurrency

All merge-prep runs share a global concurrency group `merge-prep-global` to prevent API rate limit issues when multiple PRs qualify simultaneously. PRs are processed sequentially within each cron tick. The per-PR concurrency group (`merge-prep-{pr_number}`) also remains to prevent duplicate runs on the same PR across cron ticks.

### Failure handling (label-free)

| Failure count | Action                                                                                                                                                                                                                                                                                        |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1st failure   | Workflow run shows as failed in Actions tab. Retry on next cron tick (10 min).                                                                                                                                                                                                                |
| 2nd failure   | Same.                                                                                                                                                                                                                                                                                         |
| 3rd failure   | (1) Dismiss any prior merge-prep approval. (2) Set `merge-prep-status: failure` commit status on latest commit via GitHub API. (3) Post notification comment for human visibility. Subsequent cron ticks skip this PR (detected via commit status API, not comment text).                     |
| Manual retry  | Human uses Actions → Agent: Merge Prep → Run workflow (with PR number). The workflow_dispatch trigger already exists. Merge-prep re-runs; if successful, posts `gh pr review --approve`, sets `merge-prep-status: success`, and triggers summary-and-merge (same as a normal successful run). |

No `merge-prep-failed` label. No `merge-prep-running` label. No comment-text scanning. State is read from run history (in-progress check) and the commit status API (halt check).

### Runaway loop protection

**Self-loop detection** (existing): If the last commit on the branch has a `Merge-Prep-By:` trailer, merge-prep skips the run. Prevents processing on top of its own unreviewed output.

**Cascade ceiling** (new, replaces v1 cascade limit): Count commits in the branch since diverging from `origin/main` that contain a `Merge-Prep-By:` trailer:

```bash
git log origin/main..HEAD --grep="^Merge-Prep-By:" --oneline | wc -l
```

If this count reaches `MAX_MERGE_PREP_RUNS` (default: **5**, provisional), merge-prep treats the situation as a permanent failure: dismisses its approval, sets `merge-prep-status: failure`, and posts a notification. No further cron runs occur until manual retry.

This ceiling is:

- **Label-free and comment-parsing-free** — derived entirely from git history.
- **Mathematically bounded** — convergent cycles (e.g., lint + merge-prep alternating) cannot exceed MAX_MERGE_PREP_RUNS total merge-prep commits regardless of success/failure mix.
- **Transparent** — visible in `git log` with no external state to query.
- **Equivalent to the v1 cascade limit** from the PR 582 post-mortem, but more robust: the old limit counted pipeline runs via comment-tracked counters; this counts actual merge-prep commits in git history.
- **Provisional** — 5 is conservative. Normal convergent cycles produce 2–3 merge-prep commits. If 5 have accumulated without the PR stabilising, something structural is wrong. Calibrate based on real-world data over the first 20 PRs.

## Phase 3: Environment Gate (Human Decision)

By the time the human sees the environment approval prompt:

- Cheap checks (Lint, Type Check, Pytest) are green on the latest commit.
- Agent Review has posted its assessment.
- External reviews (Gemini, Copilot) have arrived.
- Merge Prep has triaged all review feedback, pushed any fixes, and posted a decision brief.

The **`summary-and-merge.yml`** workflow has two jobs:

### Job 1: Decision Brief

Runs immediately. Collects and posts a structured summary comment:

- What changed (files, scope)
- Review verdicts (Agent Review, Gemini, Copilot, human comments)
- What merge-prep fixed vs. deferred
- Outstanding concerns (if any)
- Final recommendation: MERGE or HOLD

### Job 2: Merge (environment-gated)

```yaml
merge:
  needs: summary
  runs-on: ubuntu-latest
  environment: production
  steps:
    - name: Merge PR
      run: gh pr merge ${{ needs.summary.outputs.pr_number }} --squash --delete-branch
      env:
        GH_TOKEN: ${{ github.token }}
```

The `production` environment requires approval from one or more designated maintainers. The maintainer:

- Reads the decision brief (Job 1 output)
- Clicks **Approve** in the GitHub Actions environment approval UI
- PR merges automatically (squash + delete branch)

Or clicks **Reject** to block the merge. The PR stays open; author revises.

The human does NOT wade through individual PR review comments. The decision brief synthesises everything into one summary.

## Phase 4: Merge

Merge happens as part of Job 2 in `summary-and-merge.yml`. After environment approval:

1. `gh pr merge --squash --delete-branch`
2. Branch is deleted
3. Done

No separate auto-merge configuration needed — the merge is executed by the workflow job itself, not by GitHub's auto-merge feature.

## Workflow Files: Changes Required

| File                          | Action              | Notes                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `code-quality.yml`            | **Split into two**  | Create `lint.yml` (Lint job) and `typecheck.yml` (Type Check job). Remove `needs: lint` dependency.                                                                                                                                                                                                                                                                                                             |
| `agent-conceptual-review.yml` | **Rename + update** | Rename to `agent-review.yml`. Switch from commit status to `gh pr review`.                                                                                                                                                                                                                                                                                                                                      |
| `agent-merge-prep.yml`        | **Rewrite**         | Drop `lgtm-gate` job. Remove all label operations. Add: dismiss prior approval (step 1), loop ceiling check (step 3), post `gh pr review --approve` on success (step 9), set `merge-prep-status: success` commit status on success (step 10), set `merge-prep-status: failure` on halt. Add `workflow_dispatch` trigger with `pr_number` input (already present in current impl). Add global concurrency group. |
| `merge-prep-cron.yml`         | **Simplify**        | Change cron to `*/10 * * * *`. Replace label checks with `gh run list` (in-progress) + commit status API (`success` or `failure` = skip). Remove `gh workflow run` label manipulation.                                                                                                                                                                                                                          |
| `summary-and-merge.yml`       | **New**             | Two-job workflow: decision brief + environment-gated merge. Triggered by merge-prep on success.                                                                                                                                                                                                                                                                                                                 |
| `pytest.yml`                  | **No change**       | Already independent.                                                                                                                                                                                                                                                                                                                                                                                            |
| Ruleset                       | **Update**          | Add `Pytest` to required status checks.                                                                                                                                                                                                                                                                                                                                                                         |
| `merge-prep.agent.md`         | **Update**          | Remove commit status instructions. Add: dismiss-prior-approval step, loop ceiling logic, trigger summary-and-merge on success.                                                                                                                                                                                                                                                                                  |
| `conceptual-review.agent.md`  | **Update**          | Replace commit status with `gh pr review`. Rename context references.                                                                                                                                                                                                                                                                                                                                           |

### Workflows to delete after migration

| File               | Reason                                   |
| ------------------ | ---------------------------------------- |
| `code-quality.yml` | Replaced by `lint.yml` + `typecheck.yml` |

## GitHub Ruleset

```yaml
rules:
  - type: pull_request
    parameters:
      required_approving_review_count: 1
      dismiss_stale_reviews_on_push: false

  - type: required_status_checks
    parameters:
      strict_required_status_checks_policy: false
      required_status_checks:
        - context: Lint          # lint.yml
        - context: Type Check    # typecheck.yml
        - context: Pytest        # pytest.yml
```

**Note:** The `required_approving_review_count: 1` is still needed for PRs where merge-prep doesn't run (e.g., trivial changes merged directly). For the environment-gated path, merge is handled by the workflow job, not auto-merge, so the review count is not the primary gate.

## GitHub Environment: `production`

```yaml
# Settings → Environments → production
environment:
  name: production
  protection_rules:
    required_reviewers:
      - maintainer-team  # or specific usernames
    wait_timer: 0  # no delay after approval
  deployment_branch_policy:
    protected_branches: false
    custom_branch_policies: true
    # Allow all branches (PRs come from feature branches)
```

## Acceptance Criteria

- [ ] A PR triggers Lint, Type Check, Pytest, and Agent Review concurrently on every push
- [ ] Lint autofixes and pushes without blocking Type Check or Pytest
- [ ] Agent Review posts a `gh pr review` (not a commit status)
- [ ] An Agent Review `REQUEST_CHANGES` blocks merge via branch protection
- [ ] Merge Prep runs automatically within 25 minutes of a PR being opened (10-min cron + 15-min age gate)
- [ ] Merge Prep dismisses its prior approval before each run (approval always reflects latest code state)
- [ ] Merge Prep triggers `summary-and-merge.yml` on success
- [ ] `summary-and-merge.yml` Job 1 posts a decision brief comment
- [ ] `summary-and-merge.yml` Job 2 requires `production` environment approval
- [ ] After environment approval, PR is squash-merged and branch deleted
- [ ] No `lgtm`, `merge-prep-running`, or `merge-prep-failed` labels in any workflow file
- [ ] No comment-text scanning in merge-prep-cron.yml (halt detection uses commit status API)
- [ ] In-progress detection uses `gh run list` — no duplicate merge-prep runs
- [ ] On every successful merge-prep run: `gh pr review --approve` posted, `merge-prep-status: success` commit status set on latest commit, `summary-and-merge.yml` triggered
- [ ] Cron qualification skips PRs where latest commit has `merge-prep-status: success` (already processed) or `failure` (halted)
- [ ] After 3 consecutive merge-prep failures: merge-prep approval dismissed, `merge-prep-status: failure` commit status set, notification comment posted, cron skips the PR
- [ ] Runaway loop ceiling: merge-prep halts (same as above) when `Merge-Prep-By:` commit count in branch ≥ 5
- [ ] Manual retry via workflow_dispatch resets halt state (re-runs full success sequence if successful)
- [ ] Merge-prep does not parse arbitrary comment text for instructions (reads PR reviews only)
- [ ] Global concurrency group prevents simultaneous merge-prep runs across PRs
- [ ] `validate-ruleset.yml` passes with new job names
- [ ] `Merge-Prep-By: agent` self-loop detector still works

## Design Decisions

**Why cron instead of event-driven dispatch?**
Merge-prep fixes failing checks, so it cannot be gated on check completion. A `workflow_run` trigger (fire when checks pass) would prevent merge-prep from running on PRs with failing checks — exactly the PRs that need it most. Cron is simpler and avoids this chicken-and-egg problem entirely.

**Why 15-minute age gate with 10-minute cron?**
The age gate ensures external reviews (Gemini, Copilot) have time to arrive before merge-prep triages them. 15 minutes is a provisional estimate based on observed bot review latency; validate against actual Copilot/Gemini response times over the first few PRs and adjust if needed. Worst case: 25 minutes from push to merge-prep start.

**Why GitHub Environments for graduation?**
The maintainer's requirement: "I want a summary and a decision, not a bunch of PR comments." Environments provide a clean gate with a single "Approve" button in the GitHub Actions UI, completely separate from PR review threads. The decision brief (Job 1) gives context; the environment gate (Job 2) gives the action. This is the cleanest GitHub-native mechanism for "bot is done, human decides."

**Why not PR reviews for graduation?**
PR reviews work but force the human to interact with the PR review UI — the same place where 5 bot reviewers have left 30 comments. The environment gate is a cleaner separation: bots work in PR comments/reviews, human decides in the Actions tab with a synthesised summary.

**Why `agent-review.yml` (not `agent-strategic-review.yml`)?**
The original name `agent-conceptual-review.yml` was already being renamed. `agent-strategic-review.yml` risks collision with other agent workflows and is unnecessarily specific. `agent-review.yml` is simple, descriptive, and leaves room for the review scope to evolve.

**Why commit status for halt detection, not comment text?**
Comment text scanning is fragile: a human quoting the halt string in a comment would accidentally suppress merge-prep. It also lacks delete-reset semantics that are easy to reason about. The `merge-prep-status` commit status uses GitHub's native Commit Statuses API — queryable without text parsing, set and cleared programmatically, and visible in the PR UI alongside other checks. The cron can query `GET /repos/{owner}/{repo}/commits/{sha}/statuses` for a `merge-prep-status` context with state `failure` in one deterministic API call.

**Why a runaway loop ceiling based on git history?**
The v1 cascade limit (max 3 pipeline runs, tracked via comments) was added after a real bot-loop incident (PR 582 post-mortem). This spec removes that safeguard and replaces it with a stronger one: counting `Merge-Prep-By:` commits in git history. This is preferable because: (a) the count is derived from immutable git history rather than mutable comments; (b) it caps total merge-prep activity regardless of success/failure mix, not just consecutive failures; (c) it is label-free and comment-parsing-free. The ceiling of 5 is provisional — calibrate based on real-world data.

**Why dismiss merge-prep's prior approval before each run?**
`dismiss_stale_reviews_on_push: false` is set so that the _human's_ approval is not wiped out by every bot push. Without this setting, a lint autofix push would dismiss the human's approval and require a second human action. However, this means merge-prep's approval from a prior run would also survive subsequent pushes. If merge-prep then runs again (because new commits arrived), its old approval might represent code that no longer exists. Dismissing the prior approval at the start of each run ensures merge-prep's approval is always freshly earned.

**Why set `merge-prep-status: success` on every successful run, not just manual retry?**
Without a `success` status, the cron qualification criteria only check for `failure` (permanent halt) and in-progress runs. If merge-prep succeeds without pushing any commits (all checks pass, no review feedback to address), there is no `Merge-Prep-By:` trailer on the latest commit (the self-loop check relies on this), so the next cron tick dispatches merge-prep again. This repeats every 10 minutes until the human approves — posting duplicate triage summaries and triggering duplicate `summary-and-merge` runs. Setting `merge-prep-status: success` after every successful completion closes this gap: the cron skips the PR until a new commit arrives (which creates a new SHA without any status, resetting the check naturally). This uses zero new infrastructure — the same commit status API already specified for the failure path.

**Why remove LGTM entirely?**
The LGTM workflow was a dispatch mechanism because merge-prep was event-driven. With cron, there is no dispatch to coordinate — the cron finds qualifying PRs itself. The `lgtm` label, comment pattern, and LGTM workflow are all eliminated.

**Why split `code-quality.yml`?**
The current `needs: lint` dependency in Type Check is a false dependency. Running them in parallel is faster and respects the independence principle.

**Why `dismiss_stale_reviews_on_push: false`?**
Ensures the human's approval survives subsequent bot pushes (lint autofixes, merge-prep commits). See "Why dismiss merge-prep's prior approval" above for how this interacts with merge-prep's own approval management.

**Why global concurrency for merge-prep?**
Without a global limit, 5+ merge-prep runs could fire simultaneously when the cron ticks, all calling GitHub APIs and Claude. A `merge-prep-global` concurrency group serialises runs across PRs, preventing API rate limits and reducing cost. Each PR still gets processed — just sequentially within a cron tick rather than in parallel.

## Migration Plan

Each step leaves the pipeline functional. Never delete a workflow until its replacement is verified on 2-3 real PRs.

### Step 1: Create `production` environment and `summary-and-merge.yml` (low risk)

1. Create `production` environment in GitHub Settings → Environments.
2. Add required reviewers (maintainer(s)).
3. Create `summary-and-merge.yml` with two jobs: decision brief + environment-gated merge.
4. Test manually on a disposable PR.

### Step 2: Split `code-quality.yml` (low risk)

1. Create `lint.yml` with the Lint job (autofix logic intact).
2. Create `typecheck.yml` with the Type Check job (no `needs:` dependency).
3. Run both in parallel with `code-quality.yml` for 2-3 PRs.
4. Update `validate-ruleset.yml` check list.
5. Delete `code-quality.yml`.

### Step 3: Convert Agent Review to PR review (medium risk)

1. Rename `agent-conceptual-review.yml` to `agent-review.yml`.
2. Update agent instructions: replace `gh api .../statuses/` with `gh pr review`.
3. Verify on 2-3 PRs that APPROVE and REQUEST_CHANGES work correctly.

### Step 4: Rewrite merge-prep and cron (higher risk)

**Cron changes:**

- Schedule from `*/5` to `*/10`.
- Replace label checks with `gh run list` in-progress check and `merge-prep-status` commit status halt check.
- Keep age gate at 15 minutes.

**Merge-prep changes:**

- Drop `lgtm-gate` job entirely.
- Remove all label operations.
- Add step 1: dismiss prior merge-prep approval.
- Add step 3: check loop ceiling (`git log origin/main..HEAD --grep="^Merge-Prep-By:"`) — halt if ≥ 5.
- On success: post `gh pr review --approve` (step 9), set `merge-prep-status: success` commit status (step 10), then trigger `summary-and-merge.yml` (step 11).
- Add global concurrency group `merge-prep-global`.
- On 3rd failure or ceiling breach: dismiss approval + set `merge-prep-status: failure` commit status + post notification comment.

### Step 5: Update ruleset and clean up (low risk)

1. Add `Pytest` to required status checks.
2. Remove unused label definitions (`lgtm`, `merge-prep-running`, `merge-prep-failed`).
3. Update `specs/INDEX.md` to link to this spec and mark `specs/pr-process.md` as superseded.

## Open Questions

1. **Pytest reliability.** Before adding Pytest as a required check, verify it passes reliably on bot-authored PRs and PRs with non-Python changes. If flaky, keep it advisory until stabilised.

2. **Copilot review timing.** Copilot is configured with `review_on_push: false`. If changed to `true`, its reviews will arrive during Phase 1/2. No pipeline change needed, but worth confirming timing against the 15-minute age gate.

3. **Multiple concurrent PRs.** The global concurrency group `merge-prep-global` serialises merge-prep across PRs. Monitor whether this causes excessive queueing when many PRs are open. If so, consider raising the limit or switching to per-PR concurrency only.

4. **Human approval before merge-prep.** If the human approves before merge-prep runs, auto-merge waits for required checks. After merge-prep pushes fixes and checks re-run, auto-merge fires without any further human action.

5. **`validate-ruleset.yml` update.** After the split, the validation script needs to find `Lint` in `lint.yml`, `Type Check` in `typecheck.yml`, and `Pytest` in `pytest.yml`. Verify the script handles multi-file checks.

6. **Custodiet-reviewer integration.** The custodiet-reviewer agent currently runs as a separate workflow. Consider whether it should be folded into `agent-review.yml` or remain independent. No blocking decision needed — it can run as-is during migration.

7. **Loop ceiling calibration.** The ceiling of 5 is conservative. After 20 real PRs, review actual `Merge-Prep-By:` commit counts and adjust if warranted. A ceiling too low causes false halts; too high defeats the purpose.

8. **Summary workflow trigger filtering.** `summary-and-merge.yml` should only run when triggered by merge-prep (not manually or accidentally). Consider using a `workflow_dispatch` input to pass the PR number and a validation step to confirm merge-prep actually succeeded.

9. **Decision brief + environment approval UX.** The maintainer reads the decision brief as a PR comment (Job 1) but approves in the GitHub Actions environment UI (Job 2) — two different pages. After 5–10 real PRs, evaluate whether this navigation split causes friction in practice, or whether the clean separation of "reading" (PR tab) and "deciding" (Actions tab) is actually preferred over a single-page decision point.

## Related Specifications

- [[specs/pr-process.md]] — superseded by this spec
- [[specs/polecat-supervision.md]] — polecat PR auto-merge criteria
- [[specs/non-interactive-agent-workflow-spec.md]] — Phase 5 (PR Review and Merge) references this pipeline
