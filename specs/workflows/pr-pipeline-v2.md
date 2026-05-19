---
id: pr-pipeline-v2
title: "PR Pipeline v2"
type: spec
created: 2026-05-15T02:07:45.675923357+00:00
modified: 2026-05-15T02:07:45.675923357+00:00
alias:
  - "pr-pipeline-v2-pr-pipeline-v2"
  - "pr-pipeline-v2"
permalink: pr-pipeline-v2
status: draft
tags:
  - workflow
  - pr-pipeline
  - v2
  - draft-spec
supersedes: "pr-pipeline.md"
---

# PR Pipeline v2 — Modular Named-Agent Enforcement

> Status: **draft spec** — proposes a structural rework of the v1 pipeline ([[pr-pipeline]]). This document is the contract for migration; v1 remains the operative pipeline until each phase below ships.
>
> Epic: `aops-10d5b344` (Modular GHA agent pipeline v2)
> Parent: `task-bf380696` (Coordinator Layer Step-Change)
> Predecessor: `task-9f179cfb` (W3a — reusable workflow refactor)
>
> **Canonical location**: this spec was relocated from `academicOps/specs/pr-pipeline-v2.md` to the brain PKB (Option A; respects the orphan-md hook + brain-canonical policy). PR #1040 in `nicsuzor/academicOps` removes the in-repo copy.

## 1. Why v2

v1 pipeline collapsed three concerns into two workflows:

1. **Mechanical CI** (`lint`, `typecheck`, `pytest`) — deterministic, framework-shipped today, but every consumer repo's stack is different.
2. **Axiom enforcement** (`agent-enforcer.yml`) — fires on `workflow_run`, self-skips on agent-authored HEAD, posts to PR via review API + `merge-prep-status` transitively.
3. **Triage / merge prep** (`agent-merge-prep.yml`) — reads everyone's reviews, fixes what it can, approves, sets the _required_ `merge-prep-status`, enables auto-merge.

The collapse produces three concrete pathologies:

| #  | Pathology                                                                                                                                                                                    | Evidence                                                                                               |
| -- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| P1 | Loose triggers waste cache (~130M cache_r/wk)                                                                                                                                                | `aops-638a351e`                                                                                        |
| P2 | Enforcer self-skips on agent-authored HEAD → merge-prep substitutes its own approval for an absent enforcer verdict → PR lands with zero axiom review                                        | PR #1037 → issue #1039 (today's worked example)                                                        |
| P3 | Pauli (alignment) cannot run from GHA (no PKB MCP reachability) → alignment verdict missing entirely from the merge gate                                                                     | issue #1034                                                                                            |
| P4 | Cross-repo install is "copy three workflow files" rather than "pick the agents you want"                                                                                                     | `examples/cross-repo-shim/` carries all three; consumer cannot opt out of merge-prep without rewriting |
| P5 | Mechanical CI is framework-shipped (lint.yml/typecheck.yml/pytest.yml) but consumer stacks vary (Rust/Python/Node) — every consumer either inherits inappropriate workflows or rewrites them | mem repo (Rust) cannot use the inherited `pytest.yml`                                                  |

v2 reframes around two structural decisions:

- **One LLM agent ≡ one named framework agent ≡ one named status check.** No anonymous Claude runs. No triage agent. Branch protection AND-gates the status checks directly; there is no LLM judgment in the merge gate.
- **The framework ships agents, not mechanics.** Mechanical CI is a _naming contract_ the framework declares; consumer repos emit those names from whatever pipeline they like.

## 2. Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │             GitHub Pull Request              │
                               │  HEAD SHA = X                                │
                               └──────────────────────────────────────────────┘
                                                    │
           ┌────────────────────────────────────────┼────────────────────────────────────────┐
           ▼                                        ▼                                        ▼
┌─────────────────────┐               ┌───────────────────────┐               ┌─────────────────────────┐
│  Mechanical CI      │               │  Framework agents     │               │  Mechanic (rebase only) │
│  (consumer-owned)   │               │  (workflow_call)      │               │  (workflow_call)        │
├─────────────────────┤               ├───────────────────────┤               ├─────────────────────────┤
│ lint-status         │               │ enforcer-status (rbg) │               │ mechanic-status         │
│ typecheck-status    │               │ alignment-status      │               │  (was merge-prep)       │
│ test-status         │               │  (pauli, off-GHA)     │               │                         │
│ build-status (opt.) │               │ qa-status (marsha,    │               │ Rebase + conflict       │
└─────────────────────┘               │  optional/post-MVP)   │               │ resolve only.           │
           │                          └───────────────────────┘               │ No verdict authority.   │
           │                                       │                          └─────────────────────────┘
           │                                       │                                        │
           ▼                                       ▼                                        ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────┐
     │           GitHub commit statuses on HEAD SHA (one per agent, named identically)         │
     │                            +  GitHub PR reviews (verdicts)                              │
     └─────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
                           ┌──────────────────────────────────────────────┐
                           │   Branch Protection Ruleset (AND-gate)       │
                           │   required: lint-status, typecheck-status,   │
                           │             test-status, enforcer-status,    │
                           │             alignment-status, mechanic-status│
                           │   required_approving_review_count: 1 (human) │
                           └──────────────────────────────────────────────┘
                                                    │
                                                    ▼
                                         ┌────────────────────┐
                                         │  Human merges PR   │
                                         └────────────────────┘
```

Key properties of this diagram:

- **No triage box.** The AND-gate is GitHub branch protection. There is no LLM agent whose role is "decide whether the verdicts add up to mergeable" — branch protection does that mechanically.
- **Each agent owns one status check** named after itself. The status name is the contract.
- **Each agent posts a real GitHub PR review** as its human-facing verdict (APPROVED / CHANGES_REQUESTED / COMMENTED). The commit status is the parallel branch-protection surface.
- **Mechanic does not post a verdict.** It does mechanical work (rebase, conflict resolution) and reports the outcome via its own status. It cannot approve on behalf of a missing agent.

## 3. Per-agent contract (locked)

Every agent in the pipeline — present and future — obeys these six rules:

### 3.1 `workflow_call` is the only invocation surface

The agent's workflow file declares **only** `workflow_call`. No `pull_request`, no `workflow_run`, no `schedule`. Triggers are a separate concern; consumer repos compose them in a `triggers/` shim layer (see §6).

```yaml
# .github/workflows/agent-<name>.yml — framework
name: "Agent: <Name>"
on:
  workflow_call:
    inputs:
      pr_number: { required: true, type: string }
      ref:       { required: true, type: string }
      sha:       { required: true, type: string }   # explicit, not derived
    secrets:
      AOPS_BOT_GH_TOKEN: { required: true }
      CLAUDE_CODE_OAUTH_TOKEN: { required: true }
```

Rationale: the v1 enforcer carried `pull_request` + `workflow_run` + `workflow_dispatch` + `workflow_call`, which made the trigger-fan-out invisible (`aops-638a351e`). Forcing every fire through `workflow_call` makes the call graph traceable in `actions/runs`.

### 3.2 One named commit status, posted to HEAD SHA

The status name **equals** the agent name with the `-status` suffix:

| Agent                     | Status name        |
| ------------------------- | ------------------ |
| Enforcer (rbg)            | `enforcer-status`  |
| Alignment (pauli)         | `alignment-status` |
| Mechanic (was merge-prep) | `mechanic-status`  |
| QA (marsha, post-MVP)     | `qa-status`        |

Skip is a **success outcome with descriptive text** — never `exit 1`. Examples:

- `success` / "Skipped: HEAD SHA already reviewed (target_sha=X)" (loop-skip — see §3.6)
- `success` / "Skipped: no Python files in diff" (consumer-defined applicability)
- `failure` / "3 axiom violations — see review" (real verdict)
- `pending` / "Agent dispatched (off-GHA)" (alignment, while pauli runs on host)

### 3.3 One row in `.agents/ENFORCEMENT-MAP.md`

Every agent appears in the enforcement map under a new "PR-pipeline agents" section, declaring which axioms / rules / lifecycle points it covers. This is a **propagation rule**: a PR adding a new agent that omits its enforcement map row fails review by enforcer.

### 3.4 One `.github/agents/<name>.agent.md` prompt file

The prompt file is the agent's _behaviour contract_. It is `uses:`-mountable by other workflows, so:

- The workflow code (orchestration) and the prompt (behaviour) version independently.
- A consumer can pin the prompt at one ref and the workflow at another (rare; documented escape hatch).
- The canonical agent personality (e.g. `aops-core/agents/rbg.md`) is sourced _into_ the prompt file, not duplicated. The prompt file adds the PR-context wrapping (read .agents/CORE.md, run `gh pr view`, format review).

### 3.5 Versioned ref per agent

Each agent ships under its own ref:

| Ref            | Pins                                                             |
| -------------- | ---------------------------------------------------------------- |
| `enforcer-v1`  | enforcer workflow + `rbg.md` prompt content the workflow expects |
| `alignment-v1` | alignment workflow + pauli prompt + the pauli-callback contract  |
| `mechanic-v1`  | mechanic workflow + merge-prep.agent.md content (trimmed)        |

Breaking changes ship with intent: a new tag (`enforcer-v2`), an issue documenting the migration, and a deprecation window on `enforcer-v1`. Consumers pin to refs, never `@main`. (This is the W3a pattern — `task-9f179cfb` — generalised per-agent.)

### 3.6 Per-agent SHA-based loop-skip

Every agent reads its own latest commit status from PR HEAD before running.

The snippet below assumes three shell variables, sourced from the calling
workflow's `env:` block:

| Variable      | Source                                                        |
| ------------- | ------------------------------------------------------------- |
| `$REPO`       | `${{ github.repository }}` (e.g. `nicsuzor/academicOps`)      |
| `$HEAD_SHA`   | `${{ inputs.sha }}` — explicit workflow_call input per §3.1   |
| `$AGENT_NAME` | Hard-coded per agent (`enforcer`, `alignment`, `mechanic`, …) |

`$GH_TOKEN` must also be set to `${{ secrets.AOPS_BOT_GH_TOKEN }}` so `gh api`
authenticates as the bot.

```bash
# Each agent's first real step. Assumes $REPO, $HEAD_SHA, $AGENT_NAME, $GH_TOKEN.
LATEST_STATUS=$(gh api "repos/$REPO/commits/$HEAD_SHA/statuses" \
  --jq "[.[] | select(.context == \"$AGENT_NAME-status\")] | sort_by(.created_at) | last")
PRIOR_TARGET_SHA=$(echo "$LATEST_STATUS" | jq -r '.target_url' | sed -n 's/.*target_sha=\([a-f0-9]*\).*/\1/p')

if [ "$PRIOR_TARGET_SHA" = "$HEAD_SHA" ]; then
  # Already reviewed this exact SHA. Re-post success with same target_sha (idempotent).
  gh api "repos/$REPO/statuses/$HEAD_SHA" \
    -f state=success -f context="$AGENT_NAME-status" \
    -f description="Skipped: SHA already reviewed" \
    -f target_url="https://github.com/$REPO/actions/runs/$GITHUB_RUN_ID?target_sha=$HEAD_SHA"
  exit 0
fi
```

Then the agent reviews **the actual HEAD diff**, regardless of who authored HEAD. The `target_sha` query-param convention encodes "which SHA this verdict applies to" into the status's `target_url` (commit statuses have no native field for this; we piggyback on the URL).

This replaces the v1 anti-pattern:

```bash
# v1 — BROKEN
LAST_MSG=$(git log -1 --format='%B')
if echo "$LAST_MSG" | grep -qE '(Enforcer-By|Autofix-By|Merge-Prep-By):'; then
  echo "skip"  # ← black-holes the human diff every time merge-prep merges main in
fi
```

#### Failure mode this closes (PR #1037 / `aops-638a351e`)

1. Human pushes commit `H1` to PR branch. Enforcer reviews `H1`, posts `enforcer-status: success`, `Enforcer-By: agent` trailer on no-op fix commit `H2`.
2. Merge-prep merges `origin/main` into the branch as `M3` (`Merge-Prep-By: agent` trailer).
3. New `synchronize` event fires the pipeline. Enforcer's loop-check sees `Merge-Prep-By` trailer on HEAD (`M3`) → **skips** without verdict.
4. Merge-prep runs, sees no failing checks, no `CHANGES_REQUESTED` reviews, approves the PR, sets `merge-prep-status: success`.
5. Branch protection requires `merge-prep-status` (not `enforcer-status` directly) — gate passes.
6. Human approves. PR merges. **Zero axiom review on the diff between `H1` and `M3`.**

v2 closes this structurally on two fronts:

- (a) Enforcer's SHA-based skip checks "have I already reviewed _this exact SHA_?" — `M3` is a new SHA, so enforcer reviews it (the diff against base `M3..origin/main` is empty modulo the merge, so the review is a fast no-op success — but it's a real verdict on the real SHA).
- (b) Branch protection requires `enforcer-status` directly — there is no transitive substitution path through merge-prep / mechanic.

## 4. Pauli alignment surface — design

This is the most novel and risky component. GHA cannot reach the Tailscale-internal PKB MCP (a Tailscale magic-DNS endpoint — see `.agents/CAPABILITIES.md` for the address), so pauli — whose value is precisely the PKB context — cannot run inside a GHA runner. Two designs were considered:

### Option A — GHA posts pending; host-side cron (polecat) picks up and posts back

```
GHA workflow (workflow_call)
  └─→ post commit status: alignment-status = pending
        target_url=<work-queue entry URL or stable PR URL>
        description="Awaiting host-side pauli (queued at <timestamp>)"
  └─→ exit 0   (mechanical step done)

[time passes]

Host cron (every 5 min)
  └─→ scan all open PRs across watched repos for alignment-status=pending
  └─→ for each: dispatch polecat run with task spec "review PR #N for alignment"
  └─→ polecat container: PKB-equipped pauli reviews diff against PKB context
  └─→ pauli posts PR review (APPROVED / CHANGES_REQUESTED / COMMENTED)
  └─→ pauli posts commit status: alignment-status = success | failure
```

**Trade-offs:**

- (+) Decentralised by construction. The "GHA can't reach PKB" constraint becomes a feature: alignment lives where the PKB lives.
- (+) Reuses existing polecat infrastructure (`polecat run -p aops -t <task-id>`). The "task" is a per-PR review task, not a code-change task.
- (+) Idempotent: GHA posts `pending`, host posts terminal — race-free.
- (+) Pauli's session artifacts land in `$AOPS_SESSIONS` like every other polecat run.
- (−) Latency: PR sees `alignment-status=pending` for up to 5 min (cron tick) plus polecat run time (~3-10 min for a typical alignment review). Total p95 ~15 min.
- (−) Requires host availability. If the cron host is down, alignment-status sits at `pending` forever; branch protection blocks merge. Mitigation: a watchdog issue gets opened after 1 hour of `pending`.
- (−) Adds a new cron consumer to maintain (the "alignment dispatcher"). Sibling to `merge-prep-cron.yml` but on the host, not GHA.

### Option B — GHA runs pauli with `PKB_MCP_URL` pointing at a public/tunnelled endpoint

```
GHA workflow (workflow_call)
  └─→ run claude-code-action with pauli prompt
        env: PKB_MCP_URL = https://pkb-public.example.com/mcp  (NEW)
  └─→ pauli reviews PR with full PKB context
  └─→ post review + alignment-status = success | failure
  └─→ exit 0
```

**Trade-offs:**

- (+) Synchronous, simple, no second cron. Verdict lands when the workflow exits.
- (+) Reuses existing GHA agent harness identical to enforcer.
- (−) Requires standing up a public/tunnelled PKB MCP endpoint. Tailscale Funnel is the obvious mechanism but it pierces the network-isolation property the PKB has today (the entire reason the PKB lives on a Tailnet).
- (−) Auth: PKB MCP currently has no authn. A public endpoint needs auth (token-gated, GitHub OIDC + ID-token verification) before exposure is safe.
- (−) Failure modes are network failures inside a 30-min job timeout — opaque to debug compared to a polecat session you can re-run by hand.
- (−) Centralises the "where does pauli run" decision at the GHA edge, undoing the decentralisation we want elsewhere.

### Decision: **Option A** for MVP

- The decentralisation property is load-bearing for the framework's design intent, not incidental.
- We already have polecat dispatch infrastructure, including the watchdog patterns (`aops-7c27457a`).
- Phase 2 ships a feature flag — `PKB_MCP_PUBLIC_URL` — that enables Option B if Option A's latency turns out to be unacceptable in practice. We do not pre-build it; we measure first.

### 4.1 Implementation interface (Option A, normative)

**GHA side** (`.github/workflows/agent-alignment.yml`):

```yaml
name: "Agent: Alignment (Pauli)"
on:
  workflow_call:
    inputs:
      pr_number: { required: true, type: string }
      ref:       { required: true, type: string }
      sha:       { required: true, type: string }
    secrets:
      AOPS_BOT_GH_TOKEN: { required: true }

jobs:
  signal:
    runs-on: ubuntu-latest
    permissions: { statuses: write, pull-requests: write }
    env:
      GH_TOKEN:   ${{ secrets.AOPS_BOT_GH_TOKEN }}
      REPO:       ${{ github.repository }}
      SHA:        ${{ inputs.sha }}
      PR_NUMBER:  ${{ inputs.pr_number }}
      AGENT_NAME: alignment
    steps:
      - name: SHA-skip check
        # ... §3.6 logic. Uses $REPO / $SHA / $AGENT_NAME from job env.
      - name: Post pending + work-queue entry
        run: |
          gh api "repos/$REPO/statuses/$SHA" \
            -f state=pending -f context=alignment-status \
            -f description="Queued for host-side pauli review" \
            -f target_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID?target_sha=$SHA"
          # The work-queue surface is a GitHub Issue labelled `alignment:queued`.
          # Rationale: alignment-status is per-SHA, not enumerable across PRs;
          # the dispatcher needs a cross-PR queryable list of pending reviews.
          # Commit statuses do not provide that surface; labelled issues do.
          # The issue is auxiliary state, NOT the gate — the gate is the commit
          # status. Issue closure on completion is bookkeeping.
          gh issue create --label alignment:queued \
            --title "Alignment review: $REPO#$PR_NUMBER@$SHA" \
            --body "Auto-filed. Closed when alignment-status terminal."
```

**Host side** (new: `aops-core/scripts/alignment-dispatcher.sh`, run by cron every 5 min):

```bash
# Pseudocode — actual implementation lives in aops-core/scripts/alignment-dispatcher.sh.
# Inputs (env): $WATCHED_REPO is the host-config-defined repo whose alignment
# queue this dispatcher drains (e.g. `nicsuzor/academicOps`). Multiple repos
# can be drained by running multiple cron entries with different $WATCHED_REPO.
# $GH_TOKEN is the bot PAT (AOPS_BOT_GH_TOKEN equivalent on host).
#
# Iterate alignment:queued issues with NUL-safe parsing (issue titles may contain
# whitespace or shell metacharacters; do not splat over `for ... in $(...)`).

gh issue list --label alignment:queued --repo "$WATCHED_REPO" \
  --json number,title --jq '.[] | [.number, .title] | @tsv' \
  | while IFS=$'\t' read -r issue_number title; do

  # Title format (deterministic — produced by §4.1 GHA snippet):
  #   "Alignment review: <repo>#<pr_number>@<sha>"
  parsed=$(printf '%s\n' "$title" \
    | sed -nE 's|^Alignment review: ([^#]+)#([0-9]+)@([a-f0-9]+)$|\1 \2 \3|p')
  [ -z "$parsed" ] && { echo "skip: malformed title: $title" >&2; continue; }
  read -r REPO PR SHA <<<"$parsed"

  # Reconcile against the authoritative state (the commit status, not the issue):
  # only dispatch if alignment-status is still `pending` for this SHA. If a
  # previous tick has already posted a terminal status, the issue is stale and
  # gets closed as a bookkeeping no-op.
  current=$(gh api "repos/$REPO/commits/$SHA/statuses" \
    --jq '[.[] | select(.context=="alignment-status")] | sort_by(.created_at) | last.state')
  if [ "$current" != "pending" ]; then
    gh issue close "$issue_number" --repo "$WATCHED_REPO" \
      --comment "alignment-status already terminal ($current); closing stale queue entry."
    continue
  fi

  # Dispatch polecat with an aops-prefixed task id (enforced by the
  # create_task prefix guard in polecat/pkb_bridge.py; see ENFORCEMENT-MAP).
  task_id="aops-alignment-$(echo "$REPO-$PR-$SHA" | sha1sum | cut -c1-8)"
  polecat run -p aops -t "$task_id" \
    --workflow alignment-review \
    --prompt "$(cat aops-core/agents/pauli.md .github/agents/alignment.agent.md)" \
    --params "repo=$REPO,pr=$PR,sha=$SHA"

  # polecat run posts terminal alignment-status + PR review per §3.2.
  # Issue closure is bookkeeping (the gate is the commit status).
  gh issue close "$issue_number" --repo "$WATCHED_REPO"
done
```

**State-channel note.** The labelled issue is _queue infrastructure_, not state.
The single source of truth for whether a PR has passed alignment is the
`alignment-status` commit status on the HEAD SHA — which is what branch
protection gates on (§5). The issue is a cross-PR enumeration surface because
GitHub commit statuses are not enumerable by label/state across SHAs. If GitHub
ever ships such an API, this queue layer becomes redundant; the gate semantics
do not change.

**Pauli prompt** (`.github/agents/alignment.agent.md`) — wraps `aops-core/agents/pauli.md` with the PR-review framing: read CORE, load PKB context for the touched specs, run Strategic Review against the diff, post the review + status using the agent's PAT, then exit. Mirrors the structure of `merge-prep.agent.md`.

**Failure semantics:**

- If the host is unreachable for >1 hour, the watchdog flips `alignment-status` to `failure` with description "Host-side pauli unreachable — see issue #N" so branch protection produces a clear, actionable signal rather than indefinite `pending`.
- If pauli's polecat run errors, the run handler posts `failure` with the error class (mirrors enforcer's `Propagate agent exit status` step).

## 5. Branch protection — required status checks

The v2 ruleset (`.github/rulesets/pr-review-and-merge.yml`) lists every framework-agent status directly. There is no transitive gating.

```yaml
- type: required_status_checks
  parameters:
    required_status_checks:
      # Mechanical CI — names defined by §6 contract; emitted by consumer repo
      - context: "lint-status"
      - context: "typecheck-status"
      - context: "test-status"
      # Framework agents — each owns its own AND-gate slot
      - context: "enforcer-status"
      - context: "alignment-status"
      - context: "mechanic-status"

- type: pull_request
  parameters:
    required_approving_review_count: 1
    # Just the human. Merge-prep / mechanic no longer count as an approving
    # review — they have a status, not an approval.
```

**Rationale for naming each status directly** (the "no triage" principle made operational): if branch protection requires only `merge-prep-status`, then merge-prep becomes the de-facto AND-gate evaluator — and any agent it forgets to wait for (or that self-skips) falls out of the gate silently. v2 makes branch protection the gate; merge-prep / mechanic become peer agents.

**Rationale for `required_approving_review_count: 1`** (down from v1's 2): v1 needed two because merge-prep counted as approval #1. With v2 there is no bot approval — the human is the only approver. Each agent's verdict lives in its `-status` slot.

## 6. Mechanical-CI naming contract

The framework declares the contract; consumers implement it.

| Status name        | Required? | Semantic                                                                                                                                 |
| ------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `lint-status`      | required  | Style + format checks pass. Consumer chooses tools (ruff/eslint/clippy/...).                                                             |
| `typecheck-status` | required  | Static type checks pass (basedpyright/tsc/...). Consumer may emit `success` with description "n/a (untyped language)" if not applicable. |
| `test-status`      | required  | Test suite passes. Consumer chooses framework.                                                                                           |
| `build-status`     | optional  | Build/compile/distribution check. Required by consumer if applicable.                                                                    |

Each status is a regular GitHub commit status posted to PR HEAD by the consumer's CI. Branch protection requires the names; the framework does not require the consumer use any particular GHA action, runner, or reusable workflow.

### 6.1 Reference example: `examples/python-mechanical/`

A copy-paste-ready Python pipeline emitting the four statuses, for documentation only. Structure:

```
examples/python-mechanical/
  README.md                            # how to install + customise
  .github/workflows/
    mechanical-pipeline.yml            # orchestrator (sequential lint→type→test)
    lint.yml                           # ruff + black; emits lint-status
    typecheck.yml                      # basedpyright; emits typecheck-status
    test.yml                           # pytest; emits test-status
```

The framework **does not import** or otherwise reference `examples/python-mechanical/`. It is documentation, not infrastructure. The current academicOps repo will continue to use its own (`.github/workflows/lint.yml` etc.) — unchanged in this PR — but those files will be re-described as "academicOps-owned mechanical CI emitting the framework's naming contract" rather than "framework-shipped CI workflows".

## 7. Cross-repo install pattern

A consumer repo installs **only the agents it wants**. Each agent has its own one-file shim. Example: install enforcer + alignment but not mechanic (consumer prefers human merge-prep):

```yaml
# consumer-repo/.github/workflows/triggers/enforcer.yml
name: "Trigger: Enforcer"
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  enforce:
    uses: nicsuzor/academicOps/.github/workflows/agent-enforcer.yml@enforcer-v1
    with:
      pr_number: ${{ github.event.pull_request.number }}
      ref:       ${{ github.event.pull_request.head.ref }}
      sha:       ${{ github.event.pull_request.head.sha }}
    secrets:
      AOPS_BOT_GH_TOKEN: ${{ secrets.AOPS_BOT_GH_TOKEN }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

```yaml
# consumer-repo/.github/workflows/triggers/alignment.yml
name: "Trigger: Alignment"
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  align:
    uses: nicsuzor/academicOps/.github/workflows/agent-alignment.yml@alignment-v1
    with:
      pr_number: ${{ github.event.pull_request.number }}
      ref:       ${{ github.event.pull_request.head.ref }}
      sha:       ${{ github.event.pull_request.head.sha }}
    secrets:
      AOPS_BOT_GH_TOKEN: ${{ secrets.AOPS_BOT_GH_TOKEN }}
```

The triggers/ directory is the **only** consumer-side concern. Each shim is one job, one `uses:`, one set of inputs/secrets. Add or remove an agent by adding or deleting a shim file — no wider workflow rewrite.

Mechanical CI is consumer-owned (§6), so consumer triggers/ also contains whatever shape that takes:

```yaml
# consumer-repo/.github/workflows/triggers/mechanical.yml
on:
  pull_request: { types: [opened, synchronize, ready_for_review, reopened] }
jobs:
  pipeline:
    uses: ./.github/workflows/mechanical-pipeline.yml   # consumer-owned
```

## 8. Loop-skip protocol (formal)

This section consolidates §3.6 into a normative spec each agent implementer must follow.

### 8.1 The contract

For an agent named `<name>` reviewing PR HEAD SHA `H`:

1. Before any expensive work, fetch the agent's own latest commit status on `H`:
   ```
   GET /repos/{owner}/{repo}/commits/{H}/statuses
   filter: context == "<name>-status"
   sort: created_at desc, take first
   ```
2. Parse `target_sha` from the latest status's `target_url` (query param `?target_sha=<sha>`).
3. **If** `target_sha == H`: skip. Re-post `success` with the same `target_sha=H` and a description like `"Skipped: SHA already reviewed at <prior timestamp>"`. Exit 0.
4. **Else**: review HEAD. Post terminal status with `target_url` ending in `?target_sha=H`.

### 8.2 What's not in the contract

- Author identity. The agent **does not** care who pushed `H`. Loop-skip is about whether _this exact diff_ has already been judged, not about who wrote it. v1 conflated the two and produced the #1037 black-hole.
- Trailers. v1 used `Enforcer-By:` / `Merge-Prep-By:` / `Autofix-By:` trailers as the loop signal. These are advisory metadata for humans reading `git log`; v2 does not use them as control flow. Consumer-side commits with these trailers are reviewed exactly like any other commit.

### 8.3 Failure mode this closes (formalised)

The pathology in §1 (P2) reduces to: _v1 used "is this commit author one of our bots?" as a stand-in for "have we already reviewed this diff?"_ — a confusion of two distinct signals. Once a bot commit appears anywhere in the chain (including a benign merge-from-main), the agent stops reviewing forever, even though the diff has changed.

v2's protocol decouples the signals: the question is always "have we judged this SHA?" and the answer is recorded on the SHA itself. Bot commits are reviewed; agent self-loops are still prevented (because a re-trigger on the same SHA finds the prior verdict and short-circuits).

### 8.4 Migration note

The `target_url`-as-state-channel pattern is mildly ugly (commit statuses have no proper "previous SHA reviewed" field). Alternatives considered:

- **Issue/PR comment as state.** Costlier to query, harder to keep clean.
- **Repository variable.** Per-PR state in a per-repo variable doesn't scale.
- **External KV store.** Overengineering for this scope.

The `target_url` query-param convention is documented as v2's chosen channel; if GitHub ever adds a proper field, the migration is a one-line change in each agent.

## 9. MVP scope and migration plan

MVP includes: **enforcer**, **alignment**, **mechanic** (rebase-only), **dispatcher** (existing cron, scope-clarified).

MVP excludes: notifier (post-merge celebration / changelog / release coordination). Folded into a Phase 6+ epic when the v2 contract is stable.

### Migration plan (sketch — not binding sequencing)

The user has explicitly said this is a sketch. The actual sequencing is decided per-phase as evidence comes in.

**Phase 1 — Enforcer rewrite (worked example, fixes the #1037 bug structurally).**
Why enforcer first: it is the agent that _actually misfired_ in the worked example, so its rewrite is the proof point for the v2 contract. Also: the v1 enforcer is the loose-trigger waste source (`aops-638a351e`), so the cache-cost win is biggest here too.

Tasks for Phase 1:

- Write `.github/workflows/agent-enforcer.yml` v2 (workflow_call only, SHA-skip, named status, agent-prompt mount).
- Write `.github/agents/enforcer.agent.md` (wraps `aops-core/agents/rbg.md`).
- Write `.github/workflows/triggers/enforcer.yml` (academicOps's own shim).
- Tag `enforcer-v1`.
- Add `enforcer-status` to the ruleset; remove `merge-prep-status` from required set if and only if mechanic ships in the same phase (else: keep both required for now).
- Run for 2 weeks of real PRs; verify zero #1037-class incidents.

**Phase 2 — Alignment agent (pauli on host).**
Build the host-side dispatcher (`alignment-dispatcher.sh`), the GHA-side pending-poster, the polecat task spec, the watchdog. Test on a single PR end-to-end before adding `alignment-status` to required checks.

**Phase 3 — Mechanic (rebase-only merge-prep).**
Strip `agent-merge-prep.yml` down to: rebase, conflict resolution, post `mechanic-status`. Remove its triage/approval/auto-merge logic. The "wait until X minutes after last commit" bazaar window stays in the dispatcher.

**Phase 4 — Dispatcher rationalisation.**
The existing `merge-prep-cron.yml` is renamed to `mechanic-cron.yml` (single responsibility: dispatch mechanic on a bazaar window). Document explicitly that it is _not_ a generic agent dispatcher — alignment has its own host-side dispatcher (Phase 2), enforcer needs no dispatcher (PR triggers fire it).

**Phase 5 — Cross-repo rollout.**
Install the v2 reusables on `nicsuzor/mem` (Rust consumer — proves §6 mechanical-CI naming contract works for non-Python). Then user-owned repos.

**Phase 6+ — Notifier, QA agent (marsha), additional named agents.**
Out of MVP. File as separate epics under `aops-10d5b344` when needed.

## 10. Open questions

These are deferred for human resolution. The spec does not commit to an answer.

1. ~~**Does `enforcer-status` _require_ the rbg agent to actually run, or can a no-op static rule (e.g. "skip if diff is markdown-only") suffice?**~~ **Resolved**: the status _is_ the contract. Any token authorised to post `enforcer-status` (or any named status) is, by that posting permission, trusted to have done the work the status represents. The spec does not add trust-anchoring, token-provenance checks, or recursive validators-of-validators. If a consumer wires a dummy emitter, that is a permissions problem (revoke the token), not a workflow-design problem. Marsha's downstream runtime verification remains the check on _whether the claim is true_; the gate only checks that the named status is `success`.

2. **What happens when `alignment-status` sits at `pending` because the host is down?** **Resolved: fail closed.** The watchdog flips `pending → failure` after 1h. PRs wait until the host is back. Rationale: integrity of the alignment gate is worth more than merge throughput; if the framework's pauli surface is unreachable, the framework is degraded and PRs should not auto-pass through that degradation.

3. **Does the mechanic still need the `MAX_MERGE_PREP_RUNS` ceiling?** v1's ceiling caught runaway loops where merge-prep kept making commits without stabilising. With mechanic doing only rebase (not arbitrary fixes), the loop surface is much smaller. Spec leaves the ceiling in for now; Phase 3 can revisit.

4. **Should `target_sha` live in `target_url`, or in a separate parallel status (`enforcer-target-sha`)?** Cleaner separation, but doubles the status count and more network calls. v2 picks the URL hack for parsimony; revisit if a consumer-of-consumer (e.g. dashboard) needs to query target-sha cleanly.

5. **Cross-repo prompt drift.** Each agent prompt file (`.github/agents/<name>.agent.md`) contains both a wrapping (PR-context framing) and the canonical agent body (e.g. `rbg.md`). If a consumer pins `enforcer-v1` but the canonical `rbg.md` evolves on `main`, the consumer gets the v1 frozen rbg. Is this the desired behaviour, or should the prompt source the _current_ rbg.md by ref? **Default in spec**: frozen at the agent's release tag (predictability over freshness) — flagged for human override.

## 11. Cross-references

- [[pr-pipeline]] — v1 spec; this v2 supersedes once Phase 5 completes (see "supersession protocol" below)
- W3a (`task-9f179cfb`) — reusable workflow refactor, the substrate this builds on
- `aops-638a351e` — loose triggers waste evidence (~130M cache_r/wk)
- Issue #1039 — dual-surface ATTN exit, the #1037 worked example
- Issue #1034 — alignment review gap
- PR #1037 — the worked example: enforcer skipped on agent HEAD, merge-prep substituted approval
- `.github/rulesets/pr-review-and-merge.yml` (in `nicsuzor/academicOps`) — the ruleset to update in Phase 1 / Phase 3
- `.agents/ENFORCEMENT-MAP.md` (in `nicsuzor/academicOps`) — updated alongside this spec (see "PR-pipeline agents" section)

### Supersession protocol

This document sits alongside [[pr-pipeline]] — not replacing it yet. v1 stays the operative description until Phase 5 ships. At that point:

- [[pr-pipeline]] (v1 note) is rewritten as a "historical / migrated" stub pointing here.
- This document either stays at `pr-pipeline-v2` (with a "v2" tag) or is renamed to `pr-pipeline` (canonical). User decides at Phase 5; either is consistent with the rest of the framework.

The choice to ship as `pr-pipeline-v2` rather than overwriting v1 is deliberate: v1 references are widespread in PKB; an overwrite during the migration window would invalidate them. v2 sitting alongside lets us migrate references progressively per phase.
