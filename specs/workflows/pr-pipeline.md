---
id: pr-pipeline
title: "PR Pipeline"
type: spec
created: 2026-05-15T02:07:45.675923357+00:00
modified: 2026-06-09T00:00:00.000000000+00:00
alias:
  - "pr-pipeline-v2"
permalink: pr-pipeline
status: operative
tier: workflow
supersedes: pr-process.md
tags:
  - workflow
  - pr-pipeline
---

# PR Pipeline — Two-Stage, Environment-Gated, Convergent (single SSoT)

> Status: **operative**. This is the **single source of truth** for the PR **merge**
> pipeline (PR opened → squash-merged to `dev`). It consolidates the former
> `pr-pipeline.md` (v1, the merge-prep model) and `pr-pipeline-v2.md` (the two-stage
> convergent model) into one target-state contract; both predecessors are retired into
> this file. The **release/publish** half (merge → tag → artifacts) lives in
> [[release-publish-pipeline]] and is cross-referenced here, never duplicated.
>
> **Honesty discipline (load-bearing).** This is a _target-state_ spec. Every claim is
> flagged **LIVE** (verified on `origin/dev` and/or the live GitHub ruleset today) or
> **SPEC-ONLY** (the target, not yet wired). Do not read a SPEC-ONLY claim as current
> reality, and do not silently upgrade one to LIVE. The LIVE/SPEC-ONLY flags in this
> file were re-verified against the actual workflow files, the live ruleset
> (`gh api repos/.../rulesets/13762049`), and the live Environment list on 2026-06-09 —
> not inherited from prior session-synthesis.
>
> Epic: `aops-10d5b344` (Modular GHA agent pipeline v2).

## 0. What is LIVE vs SPEC-ONLY today (the honest summary)

Read this table first; the sections below carry the detail and repeat the flags inline.

| Capability                                                                                                                                                                                                                                                                                                                                                                                                        | State         | Evidence (2026-06-09)                                                                                                                                                                            |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Stage-1 triage orchestrator (`pr-pipeline.yml`): cost-order `lint → enforcer → qa`, `committed`-output short-circuit, read-only `typecheck`/`pytest`                                                                                                                                                                                                                                                              | **LIVE**      | `.github/workflows/pr-pipeline.yml`                                                                                                                                                              |
| **Pre-admission mechanical responder** (§3.8): `check-mechred` gate + `agent-pre-admission-responder.yml` clear mechanically-fixable red pre-admission; judgment calls and recusal flags surface to the human gate; no-op-on-green guard; MAX_RESPONDER_RUNS=3 ceiling                                                                                                                                            | **LIVE**      | `pr-pipeline.yml` `check-mechred` + `pre-admission-responder` jobs; `agent-pre-admission-responder.yml`; `scripts/ci/check-mechanical-red.sh`; `.github/agents/pre-admission-responder.agent.md` |
| Enforcer (rbg) per-agent contract: `workflow_call`-only agent file, `enforcer-status`, per-SHA loop-skip via `?target_sha=`                                                                                                                                                                                                                                                                                       | **LIVE**      | `agent-enforcer.yml` + `trigger-enforcer.yml`                                                                                                                                                    |
| QA (marsha) per-agent contract: `workflow_call`-only, `qa-status`, per-SHA loop-skip, never commits                                                                                                                                                                                                                                                                                                               | **LIVE**      | `agent-qa.yml` + `trigger-qa.yml` + `.github/agents/qa.agent.md`                                                                                                                                 |
| The human gate: a maintainer's PR **review approval**; `admit-on-review.yml` (`on: pull_request_review`) authorises, sets `admit-status`, arms auto-merge, dispatches the mechanic's first pass                                                                                                                                                                                                                   | **LIVE**      | `admit-on-review.yml` + `scripts/ci/admit-on-review.sh` + `tests/test_admit_on_review.py`                                                                                                        |
| **Request-changes response path** (§3.10): a write-class maintainer's CHANGES_REQUESTED review dispatches the mechanic in `review-response` mode — comment-scoped, no admission, no auto-merge, CHANGES_REQUESTED stands until human re-reviews                                                                                                                                                                   | **LIVE**      | `admit-on-review.yml` `authorize-changes` + `mechanic-review-response` jobs; `agent-mechanic.yml` `mode: review-response`; `mechanic.agent.md` review-response section                           |
| **RETIRED human gate:** `pr-fix-loop` GitHub Environment + in-pipeline `admit` job that parked on it                                                                                                                                                                                                                                                                                                              | **RETIRED**   | retired 2026-06-16 — undiscoverable approval UI + stranded mechanic dispatch (no re-trigger event), worked example PR #1858 (§3.2)                                                               |
| Branch-protection ruleset: required = `Lint / Lint`, `Pytest / Pytest`, `enforcer-status`, `qa-status`, `review-attestation`, `admit-status`; `required_approving_review_count: 0`; `enforcement: active`                                                                                                                                                                                                         | **LIVE**      | live ruleset ID `13762049` (API-verified 2026-06-19)                                                                                                                                             |
| **Draft-PR guard**: expensive jobs (`enforcer`, `qa`, `pre-admission-responder`, `review-attestation`) have explicit `draft == false` guards; `admit-on-review.yml` approve path and `changes_requested` path also carry explicit draft guards; the `pr-pipeline.yml` `mechanic` is draft-safe via dependency-starvation cascade (no explicit guard needed — see §3.9); `ready_for_review` is the activation edge | **LIVE**      | `pr-pipeline.yml` + `admit-on-review.yml` `if:` guards; §3.9                                                                                                                                     |
| **Sticky admission**: `admit-status` carries forward across every push (agent or human) until a terminal state (merge / §3.6 exhaustion / §3.10 changes-requested); a push never re-judges admission (§5)                                                                                                                                                                                                         | **LIVE**      | `pr-pipeline.yml` `initialize` job; worked example PR #2005 (non-bot `botnicbot` push stranded admission under the old reset-on-human-push rule)                                                 |
| **Code-owner review request** on PR open (`.github/CODEOWNERS` → GitHub auto-requests the maintainer); **Force Review** manual escape hatch (`force-review.yml`, §3.12) re-runs enforcer/qa on demand                                                                                                                                                                                                             | **LIVE**      | `.github/CODEOWNERS`; `.github/workflows/force-review.yml`                                                                                                                                       |
| **Stage-2 dev/mechanic agent** appended to the cost order (real development + conflict resolution inside an admitted run)                                                                                                                                                                                                                                                                                         | **LIVE**      | `agent-mechanic.yml` + `.github/agents/mechanic.agent.md` + `pr-pipeline.yml` `mechanic` job gated on `admit-status=success` (Phase 5)                                                           |
| `mechanic-status` informational status                                                                                                                                                                                                                                                                                                                                                                            | **LIVE**      | posted by `agent-mechanic.yml`; NEVER in the required-checks list                                                                                                                                |
| **Stage-2 re-verify contract** (enforcer + qa re-run per mechanic SHA; §3.5)                                                                                                                                                                                                                                                                                                                                      | **LIVE**      | mechanic stamps `Mechanic-By:`, enforcer/qa use per-SHA loop-skip on the new SHA (§10)                                                                                                           |
| **Stage-2 bounded loop + exhaustion escalation** (§3.6)                                                                                                                                                                                                                                                                                                                                                           | **LIVE**      | `MAX_MECHANIC_RUNS=5` (counts `Mechanic-By:`); `timeout-minutes: 55`; exhaustion handler resets `admit-status` + escalation review                                                               |
| Alignment (pauli) advisory marker — orchestrator posts `alignment-status: pending` on HEAD                                                                                                                                                                                                                                                                                                                        | **LIVE**      | `pr-pipeline.yml` `alignment-queue` job (pending-status step only)                                                                                                                               |
| Alignment `alignment:queued` issue-queue surface — one issue per PR for a host drainer to consume                                                                                                                                                                                                                                                                                                                 | **DISABLED**  | removed in aops-956c1842 — write-only spam while the drainer is unbuilt; do NOT restore until §6.2 ships (follow-up aops-8f42f33d)                                                               |
| Alignment host-side cron + polecat-pauli dispatcher (drains the queue, posts the terminal `alignment-status`)                                                                                                                                                                                                                                                                                                     | **SPEC-ONLY** | no host cron / dispatcher wired; live stand-in is manual `/strategic-review --critic` (§6)                                                                                                       |
| **v1 fixer** = `agent-merge-prep.yml` + `merge-prep-cron.yml` + `merge-prep.agent.md`                                                                                                                                                                                                                                                                                                                             | **RETIRED**   | all three files deleted at Phase 5; vestigial `merge-prep-status` carry-forward removed from `pr-pipeline.yml` `initialize`                                                                      |
| **v2 separate-dispatch admission** = `stage2-admission.yml` + `dispatch-admission` job                                                                                                                                                                                                                                                                                                                            | **RETIRED**   | superseded twice: first folded into the in-pipeline `admit` job, now into `admit-on-review.yml` (review-approval, §3.2)                                                                          |

As of Phase 5 (this consolidation+P5 PR), the Stage-2 fix loop is now wired end-to-end:
the orchestrator appends `mechanic` after `qa` gated on `admit-status=success`; the
v1 `merge-prep` + cron-driven dispatch is **retired** (all three files deleted), so a
green docs-only PR no longer spawns a no-op runner on the green path (pathology P5 / PR
1614 closed). The §3.5 re-verify contract (enforcer + qa re-run per mechanic SHA) and
§3.6 bound-+-escalate (`MAX_MECHANIC_RUNS=5`, exhaustion → reset `admit-status` + post
escalation review + request maintainer) are implemented inside `agent-mechanic.yml` and
`.github/agents/mechanic.agent.md`. The remaining SPEC-ONLY items are alignment (Phase 6)
and the §12 open questions (loop-driver scratch-PR validation, `MAX_MECHANIC_RUNS`
calibration over real PRs, `target_sha` channel, advisory-finding tracking).

> **Post-P5 wiring defect (found + fixed, aops-5938db00).** As shipped, the in-pipeline
> `admit` and `check-admit` jobs gated on `needs.enforcer.result == 'success' &&
> needs.qa.result == 'success'` — i.e. on a **green verdict**, not on convergence. Because
> the enforcer reusable hard-fails its job on a red verdict (`result == 'failure'`), any PR
> that converged RED never parked at `pr-fix-loop` and never dispatched the mechanic — so the
> Stage-2 loop, despite being wired, was **unreachable for its primary purpose** (clearing
> red). This is the §3.4(5)/§3.7 success-gate inversion, on the gate jobs. PR #1747 (converged
> red after a dev-merge, dead-ended) is the worked example. **Fixed** by re-keying both jobs on
> convergence — `(enforcer.result == 'success' || == 'failure')` and likewise for qa, plus the
> existing `committed != 'true'` guards — so a converged-red PR parks and the mechanic runs
> (§3.2, §3.4 pt 5). Until this fix the "wired end-to-end" claim above held only on the green path.

## 1. Why this shape — and why it can now be simpler

v1 collapsed three concerns into two workflows: mechanical CI, axiom enforcement, and a
monolithic `merge-prep` that read everyone's reviews, fixed what it could, approved, set
the _required_ `merge-prep-status`, and armed auto-merge.

The pathologies this produced:

| #  | Pathology                                                                                                                           | Evidence                                   |
| -- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| P1 | Loose triggers waste cache (`pull_request` + `workflow_run` + … fan-out)                                                            | `aops-638a351e` (~130M cache_r/wk)         |
| P2 | Enforcer self-skipped on agent-authored HEAD → merge-prep substituted its own approval for an absent verdict → PR landed unreviewed | PR #1037 → issue #1039                     |
| P3 | Pauli (alignment) cannot run from GHA (no PKB MCP reachability) → alignment verdict missing from the gate                           | issue #1034                                |
| P4 | Cross-repo install is "copy three workflow files", not "pick the agents you want"                                                   | `examples/cross-repo-shim/`                |
| P5 | **merge-prep runs as a no-op on every green PR** — a full runner + two full-history checkouts to make ~4 API calls on its fast-path | PR #1614 (docs-only) is the worked example |

**The v1 improvements changed the economics.** v1 gained an `initialize` job that holds a
required status pending until triage (with carry-forward on `synchronize`), a working
fast-path, and the enforcer rewrite. That means the pipeline no longer needs a heavy
"triage agent that decides mergeability" — most of that work is now either mechanical or
belongs to the named agents directly. The pipeline can be both **simpler** (no triage LLM,
no per-PR mechanic timer) and **stronger** (a real human "good idea" gate; convergence
that never re-runs heavy agents on cheap fixes).

This pipeline reframes around three structural decisions:

- **One LLM agent ≡ one `workflow_call`-only reusable ≡ one named status check.** No
  anonymous Claude runs; no agent self-triggers (the anti-cascade substrate; §4.1, §10).
  Enforcer and qa already obey this (**LIVE**).
- **Two stages with one human gate between them.** Cheap triage runs on every commit; the
  expensive development loop runs _only after a human admits the PR_ as a good idea (§3).
  We never spend development effort on a bad idea.
- **The merge gate is a cheap human-approval status, not an agent.** The required
  `admit-status` is set by `admit-on-review.yml` on a maintainer's PR review approval (no
  checkout, no LLM) — this is what removes P5's no-op merge-prep run.

## 2. Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — TRIAGE  (GHA, every push, cheap, one convergence, no dev)   │   LIVE
│                                                                       │
│  orchestrator runs committing agents in COST ORDER, short-circuit:    │
│     lint (autofix) → enforcer/rbg → qa/marsha                         │
│  read-only checks (typecheck, pytest) post status, never commit       │
│  pauli/alignment: SPEC-ONLY (manual /strategic-review today, §6)      │
│                                                                       │
│  each agent: fix what it can (commit) · red status for what it can't  │
│  a pass stops at the FIRST agent that commits; its push = next pass    │
│  CONVERGED = a full pass with zero commits → statuses fresh on HEAD    │
└───────────────────────────────────────────────────────────────────────┘
                                 │ on convergence, dispatch a Stage-2 run
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  THE GATE — your PR **review approval** (admit-on-review.yml)          │   LIVE
│  You read the statuses + reviews + pauli's verdict and click Approve   │
│  on the PR. The approval event sets admit-status, arms auto-merge, and │
│  dispatches the mechanic. Admission = "good idea — make it mergeable". │
└───────────────────────────────────────────────────────────────────────┘
                                 │ approved (pull_request_review)
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — FIX LOOP  (post-admission, the "new environment")           │   LIVE*
│  same orchestrator + short-circuit + convergence, now WITH:           │
│     … → dev/mechanic agent (real development) + conflict resolution    │
│  enforcer + qa RE-VERIFY each mechanic SHA (§3.5) · bounded (§3.6)     │
│  required-green to merge: cheap checks + enforcer + qa + no conflicts  │
│  CONVERGED + all-green → MERGE   |   loop bound exhausted → escalate    │
│  admission armed `gh pr merge --auto`; merge fires when checks green   │
└───────────────────────────────────────────────────────────────────────┘
   * Phase 5 complete: dev/mechanic agent (`agent-mechanic.yml`) is built and
     wired into the admitted Stage-2 loop; the v1 merge-prep cron is retired (§8).
```

Key properties:

- **No triage box.** Branch protection AND-gates the named statuses mechanically; there is
  no LLM whose job is "decide whether the verdicts add up to mergeable." **LIVE.**
- **No mechanic-on-a-timer.** The dev/mechanic agent runs only _inside_ an
  admitted fix loop, and conflict resolution only when the PR is `CONFLICTING`; no per-PR
  no-op run. **LIVE** (Phase 5) — `agent-mechanic.yml` is `workflow_call`-only, dispatched
  by `pr-pipeline.yml`'s `mechanic` job gated on `admit-status=success`; the v1 cron-driven
  merge-prep is retired (§8, §11).
- **Alignment is an input to the human gate, not a required check.** A host outage
  degrades advice, never deadlocks a merge. **LIVE for the "not required" part; the
  host-side dispatch is SPEC-ONLY** (§6).

## 3. The two stages and the gate

### 3.1 Stage 1 — Triage (fire-once on ready, then re-verify only when admitted) — **LIVE**

A single **triage orchestrator** (`pr-pipeline.yml`) is the workflow triggered by
`pull_request` (`opened`, `synchronize`, `ready_for_review`, `reopened`). It runs the
committing agents in cost order under the **ordered short-circuit** rule (§3.4). The
dev/mechanic agent does **not** run in Stage 1 — triage is cheap by construction.

**Fire-once gate (the expensive reviewers do NOT run on every push).** `lint`,
`typecheck`, and `pytest` run on every push (they are cheap). The expensive named
reviewers — `enforcer` and `qa` — are gated so they fire **once when the PR is marked
ready, and then NOT AGAIN until the PR is admitted.** Concretely, the `enforcer` job's
`if:` adds, on top of the pre-existing lint-not-committed and not-draft guards, the clause:

```
(github.event_name != 'pull_request' || github.event.action != 'synchronize' || needs.initialize.outputs.admitted == 'true')
```

So the reviewers run on `opened`/`ready_for_review`/`reopened` (a non-`synchronize`
action), and on a `synchronize` **only** when `initialize` carried admission forward
(`admitted == 'true'`, i.e. a post-admission mechanic fix SHA that Stage-2 must
re-verify, §3.5). On a **pre-admission `synchronize`** `admitted` is `'false'`, so
`enforcer` skips and — via the dependency-starvation cascade (§3.9) — `qa`,
`check-mechred`, `check-admit` and the in-pipeline `mechanic` skip with it. `initialize`
exposes `admitted` as a job output computed from the same admit-status carry-forward it
already performs (§5).

**Why.** A churning PR that takes many pre-admission pushes used to re-run the full
reviewer panel on every one of them, re-litigating the same open findings against
unrelated commits (forensic: PR #1970 — one enforcer finding re-emitted identically
across six push-triggered cycles over ~35h). Under the fire-once gate the panel runs
once at ready, the maintainer reads it and pushes/iterates freely without burning
reviewer invocations, and the reviewers re-engage at the admission boundary (§5) and
then on every mechanic fix SHA inside the Stage-2 loop (§3.5). `review-attestation` (a
cheap script, not an agent) still runs on every push and reads red while the reviewers
are absent — harmless, since a pre-admission PR is ungated by `admit-status` regardless;
the admission boundary re-posts it green on the admitted SHA (§5).

Each agent **fixes what it can and leaves its status red for what it can't.** There is no
clean "autofixer vs reviewer" split: `lint` autofixes formatting but goes red on a lint
error needing a real code change; `enforcer` autofixes some violations but goes red on the
ones needing judgement or development. **A red status is a handoff** — the next agent down
the chain (ultimately the mechanic in Stage 2) is who clears it. (Today, qa never commits —
it verifies only; `committed` is always `false` — so the only Stage-1 committers are lint
and enforcer.)

`pauli`/`alignment` runs as an out-of-chain advisory surface, not inside the lint→enforcer→qa
chain. The orchestrator's `alignment-queue` job posts `alignment-status: pending` on HEAD
(**LIVE**); the `alignment:queued` issue-queue surface it used to file is **DISABLED**
(removed in aops-956c1842 — see §6.1), because the host-side cron + polecat-pauli dispatcher
that would drain the queue is **SPEC-ONLY** and unbuilt. Until that drainer ships the live
stand-in is the manual `/strategic-review --critic` skill the maintainer runs by hand before
admitting (§6).

Stage 1 ends when the pass converges (§3.4). The orchestrator's in-pipeline `admit` job
then parks at the gate (§3.2) on the same workflow run.

### 3.2 The gate — a PR **review approval** — **LIVE**

Admission to the development loop is a maintainer's **PR review approval**. Clicking the
PR's **"Approve"** button is the single human decision in the pipeline: _this is a good
idea; make it mergeable._ The maintainer reads the triage statuses, the agents' reviews,
and pauli's alignment verdict (if they ran `/strategic-review` by hand), then Approves
(admit) or requests changes / leaves it.

> **PR timeline readability.** On a PASS verdict, enforcer and qa post a **marker-only**
> review body (`## Enforcer Review — clean` / `# QA Verification — VERIFIED`) with no
> reasoning prose — the PR conversation stays uncluttered. The human-readable summary moves
> into the commit-status `description` (clickable from the PR's status row). On a REVISE
> verdict, the full reasoning remains in the review body so the mechanic and the maintainer
> can read what must change. See §4.2 for the full contract.

**Surfacing PRs to the gate (code-owner review request).** The maintainer should not have to
_discover_ PRs by browsing. `.github/CODEOWNERS` (`* @nicsuzor`) makes GitHub **auto-request a
review from the code owner** the moment a PR is opened, so every PR lands in the owner's
"Review requested" queue — the native affordance that feeds this admission gate. (GitHub never
requests review from the PR's own author, so this fires for agent/bot-authored PRs, e.g.
opened as `botnicbot`, which are exactly the ones needing a human look.) This drives the
review _request_ only; it is intentionally **not** wired as a "require code-owner review"
branch-protection rule — `admit-status`, not a GitHub review count, remains the merge gate
(`required_approving_review_count: 0`).

This is handled by a small event-driven workflow, **`admit-on-review.yml`**
(`on: pull_request_review: types: [submitted]`). It has **two paths** on review submission:

**Approve path (admission):** On an `approved` review it: (1) checks the reviewer is
authorised (write-class repo permission, or the explicit maintainer allowlist — the
default-deny policy lives in `scripts/ci/admit-on-review.sh`, unit-tested in
`tests/test_admit_on_review.py`); (2) sets the required `admit-status` to `success` on
the admitted SHA (re-read live, since the PR may have advanced since the review); (3)
arms `gh pr merge --auto --squash --delete-branch`; and (4) dispatches the mechanic's
**first** pass on the admitted SHA (skipping it when enforcer + qa are already green —
auto-merge handles that, no development to do).

**Request-changes path (comment-scoped response, §3.10):** On a `changes_requested`
review from a write-class maintainer on a ready (non-draft) PR, `admit-on-review.yml`
dispatches the mechanic in `review-response` mode (§3.10). This path does NOT set
`admit-status`, does NOT arm auto-merge, and does NOT approve the PR. The reviewer's
CHANGES_REQUESTED review stands until the reviewer re-reviews. Merge happens only via a
subsequent human Approve (the approve path above).

The two paths are mutually exclusive within a single review event (a review is either
`approved` or `changes_requested`, never both). Both paths apply the same write-class
authorization and the same draft guard (§3.9).

> **Superseded design — the `pr-fix-loop` GitHub Environment gate (RETIRED 2026-06-16).**
> Admission used to be a GitHub **Environment with a required reviewer** (`pr-fix-loop`),
> approved via an in-pipeline `admit` job that parked on it. It was retired for two
> reasons, both demonstrated on PR #1858 (run 27625186358):
>
> 1. **Discoverability.** The Environment approval surfaced only as "Review deployments →
>    Approve" buried inside an Actions run — not on the PR. The design _claimed_ it was
>    "PR-attached, one click from the PR page," but GitHub's UI does not render Environment
>    approvals on the PR conversation tab, so the maintainer had to hunt through runs.
> 2. **Stranded dispatch (the load-bearing defect).** Approving an Environment emits **no
>    event**, so nothing re-triggered the pipeline on the admitted SHA. Worse, the parked
>    `admit` job and the mechanic's `check-admit` dispatch gate were **siblings** off
>    `[lint, enforcer, qa]`, running concurrently: `check-admit` read `admit-status=pending`
>    and skipped the mechanic ~2 min **before** the human approval set it to `success` in
>    the same run. The admission could never be seen by that run's mechanic gate, and no
>    later run re-entered on the admitted SHA — so **the mechanic never dispatched** and
>    admission stranded. (Observed on PR #1858: `check-admit` skipped at 14:44:21;
>    `admit-status=success` posted at 14:46:26.)
>
> A `pull_request_review` **is** a workflow trigger, so the review-approval model fixes
> both by construction: the prominent Approve button is discoverable, and the approval
> event re-enters the pipeline on the admitted SHA and dispatches the mechanic directly —
> with no parked sibling job to race. The retired surfaces — the in-pipeline `admit` job,
> its `environment: pr-fix-loop` binding, the `initialize` job's `already_admitted` output,
> and the separate-dispatch `stage2-admission.yml` before it — are all gone. The
> `pr-fix-loop` Environment object can be deleted in repo Settings; it is no longer
> referenced by any workflow.
>
> **Admission keys on the maintainer's judgement, never on a green verdict (normative; same
> rule as §3.4 pt 5 / §3.7).** A maintainer may (and routinely should) approve a
> converged-**red** PR: that is the whole point of the two-stage model — the human admits a
> good idea even with red on the board, and the Stage-2 mechanic clears the red (§3.3/§3.5).
> Approving on red is safe because the armed auto-merge fires only once **all required checks
> are green**; an un-cleared red simply never merges. The same "convergence, not
> green-verdict" rule governs the `check-admit → mechanic` dispatch for passes 2…N (§3.3):
> it keys on lint succeeded + enforcer AND qa each having **run and produced a verdict**
> (`success` _or_ `failure`) with no agent commit — never on `result == 'success'`, which
> would make the mechanic (the agent that clears red) unreachable on exactly the PRs that
> need it. (Earlier success-gate-inversion defect on the gate jobs: aops-5938db00; worked
> example PR #1747.)
>
> **Authorisation (fail-closed).** Only an `approved` review from a write-class
> collaborator (or an allowlisted maintainer) admits. A comment, a changes-requested
> review, or an approval from a read-only / non-collaborator account is a `skip` —
> default-deny. The reviewer's permission is resolved live via
> `repos/{repo}/collaborators/{login}/permission`; an unresolved permission denies. Fork
> PRs are skipped at the workflow `if:` (no bot write token).
>
> **Persistence across the fix loop — admission is sticky ("approved in-principle").**
> Admission does not depend on GitHub keeping the review "fresh." `required_approving_review_count`
> stays `0`, so the approval is not a merge-gate review and "dismiss stale reviews" is
> irrelevant. Admission persists as the `admit-status` commit status, which **carries
> forward across every subsequent commit — agent or human — until a terminal state ends
> it** (§5). The maintainer's approval means _"this PR is approved in principle; proceed to
> the merge pipeline,"_ and from there the loop runs to a terminal outcome (merge, §3.6
> exhaustion, or §3.10 changes-requested) without asking the maintainer to re-approve each
> time a commit lands. This is safe because **enforcer + qa re-verify code quality on every
> SHA inside the loop (§3.5)** — a carried admission never means an unreviewed diff merges;
> it only persists the _in-principle_ decision. (Earlier model reset admission on any
> non-bot push; that misclassified the `botnicbot` service account — GitHub type `User` —
> as a human push and silently stranded admitted PRs mid-loop. Worked example: PR #2005.)

### 3.3 Stage 2 — Fix loop (post-admission) — **LIVE** (Phase 5)

The admitted run uses the **same orchestrator, ordered short-circuit, and convergence**
as Stage 1, with two additions:

- the **dev/mechanic agent** is appended last in the cost order — it does real development
  to clear the red that the autofixers couldn't; and
- **conflict resolution** runs when the PR is `CONFLICTING` (`git merge origin/<base>`). A
  conflicting PR reaches the mechanic only via the review-approval admission path — it never
  gets a `pull_request` triage run (§3.11).

**LIVE:** `agent-mechanic.yml` is invoked by `pr-pipeline.yml`'s `mechanic` job (gated on
`admit-status=success` via a tiny `check-admit` precursor); `.github/agents/mechanic.agent.md`
is the behaviour contract; the v1 `merge-prep` agent and its cron dispatcher are deleted
(§8 is now retrospective documentation of inherited behaviour, not a description of a
live workflow). The §3.5 re-verify contract and §3.6 bound + exhaustion handler govern
the mechanic and are implemented in the workflow + agent files.

Required-green to merge is **cheap checks + `enforcer` + `qa` + no conflicts** — **not**
alignment. The loop iterates to convergence:

- **converged + all-green → merge** (auto-merge was armed at admission, §5).
- **loop bound exhausted + still-red → escalate and stop** (§3.6) — post a
  rejection/escalation review, leave the PR un-merged, surface back to the human gate.

### 3.4 Convergence and the ordered short-circuit (normative) — **LIVE**

This is the mechanism that makes the loop cheap. The cascade failure ("rbg re-runs on every
lint fix") is an artifact of giving each agent its own push trigger. This pipeline forbids
that (§4.1) and runs agents only from the orchestrator:

1. Within a pass, committing agents run in **cost order**: `lint → enforcer → qa
   [→ mechanic, Stage 2 only]`. Each agent job exposes a boolean output `committed`.
2. A pass **stops at the first agent that commits**: every downstream agent job is guarded
   `if: <no upstream agent in this pass committed>` (live form in `pr-pipeline.yml`:
   `needs.lint.outputs.committed != 'true'`, `&& needs.enforcer.outputs.committed != 'true'`,
   …). The single push from that agent starts the next pass from the cheapest agent.
3. **Convergence** = a pass in which the chain runs all the way through and **no agent
   commits**. At that point every agent has posted an authoritative status on the _current_
   HEAD SHA.
4. Read-only checks (typecheck, pytest) never commit, so they never end a pass; they only
   contribute statuses. (Typecheck is **not** a required gate — §7, debt `aops-1c3de214`.)
   **They are mutually independent** — each `needs: [lint]` and runs once lint has not
   committed; **neither gates the other.** `pytest` must NOT be `needs: [typecheck]`: pytest
   is a _required_ check while typecheck is _not_, so a `needs` edge let a non-required
   typecheck failure **skip** the required `Pytest` job (status never posted → PR wedged for a
   reason unrelated to tests). Worked example: PR #1747 (typecheck red on a docs-only PR →
   `Pytest` SKIPPED). Fixed under aops-5938db00.
5. **The short-circuit keys on `committed`, never on the VERDICT colour (#1450, §3.7).** A
   guard that conditioned a downstream reviewer on an upstream reviewer's _success_ (e.g.
   `qa` gated on `needs.enforcer.result == 'success'`) inverts the review gradient: an
   enforcer-RED PR would get _less_ review (qa skipped), routing the deepest review away from
   the riskiest PRs. The correct guard is "did the upstream agent COMMIT (change the SHA)?",
   not "was its verdict green?". A red verdict is a **handoff**, not a stop — every named
   reviewer that _ran on this SHA_ still runs; a failing PR gets **more** review, not less.
   (Live form: `qa` runs on `needs.enforcer.result == 'success' || == 'failure'` and only
   short-circuits on `needs.enforcer.outputs.committed != 'true'`.)

Because autofixes are idempotent, convergence is fast (passes ≈ the depth of the
fix-dependency chain, typically 1–3). Heavy agents never run "on every lint fix" because a
lint commit ends the pass before they are reached. A short debounce on Stage-1 entry —
`concurrency: cancel-in-progress: true` keyed on the PR — collapses rapid human pushes
before heavy agents are reached.

Worked trace (a PR needing a lint autofix and an enforcer-fixable issue):

```
pass 1: lint commits a format fix → STOP (push)
pass 2: lint no-op, enforcer commits an axiom fix → STOP (push)
pass 3: lint no-op, enforcer no-op, qa no-op → CONVERGED; all statuses fresh on HEAD
```

`enforcer` ran **once**, not once per lint fix.

### 3.5 Stage-2 re-verification contract — enforcer + qa run _inside_ the fix loop (Nic, 2026-06-09) — **LIVE** (Phase 5)

This makes explicit a property the convergence machinery already guarantees, stated as a
**contract** the mechanic and orchestrator must uphold — not merely an emergent side
effect:

1. **Enforcer (rbg) and qa (marsha) run inside the Stage-2 fix loop, not only in Stage 1.**
   The admitted run uses the _same_ orchestrator and cost order, so every Stage-2 pass runs
   `lint → enforcer → qa → mechanic`. The reviewers are not "Stage-1 only".
2. **They re-run whenever the SHA changes.** Per the per-SHA loop-skip protocol (§10), an
   agent skips _only_ when re-triggered on a SHA it has already judged. The mechanic's fix
   is a **new commit → new HEAD SHA**, which neither enforcer nor qa has judged, so on the
   next pass they **review the new SHA** (they do _not_ skip). Author identity is
   irrelevant (this is exactly the P2 fix): "have we judged _this diff_?" never "was the
   author a bot?".
3. **A red re-verdict returns the loop to the mechanic.** If, on the mechanic's new SHA,
   `enforcer-status` or `qa-status` comes back red, the pass converges with a red required
   check; the mechanic (the agent that clears red the autofixers can't) is dispatched again
   to address it. The fix loop is precisely "mechanic fixes → rbg+marsha re-verify → if red,
   mechanic again", bounded by §3.6.
4. **Merge requires `enforcer-status` AND `qa-status` green on the _final_ SHA.** Unlike
   `admit-status` (which carries forward across agent commits, §5), the reviewer statuses
   do **not** carry forward — each is re-posted per SHA (§4.6, §10). Therefore the armed
   auto-merge can fire only when the **latest** SHA carries fresh green `enforcer-status`
   _and_ `qa-status` (plus green cheap checks and `admit-status`). The convergence property
   guarantees this; this clause makes it a stated requirement so an implementer cannot
   "optimise" the reviewers out of the post-admission passes.

**Why state it explicitly.** A tempting but wrong optimisation is to treat enforcer/qa as
"already passed at admission" and skip them after the mechanic commits — which is the P2
failure (a fix lands unreviewed). The carry-forward in §5 is deliberately scoped to
`admit-status` _only_; the reviewer verdicts must always reflect the SHA that actually
merges.

### 3.6 Stage-2 bounded loop + exhaustion escalation (Nic, 2026-06-09 — NEW) — **LIVE** (Phase 5)

Stage 2 must **not iterate forever**. The fix loop is bounded on two independent axes; the
first is the primary contract, the second is a backstop:

**(A) Convergence-pass cap (primary).** Count the mechanic's own fix-commits on the branch
since it diverged from the base:

```bash
git fetch origin "$DEFAULT_BRANCH"
MECH_COUNT=$(git log "origin/$DEFAULT_BRANCH..HEAD" --grep="^Mechanic-By:" --oneline | wc -l)
```

The cap is **`MAX_MECHANIC_RUNS = 5`** mechanic fix-commits. This carries forward v1's
proven `MAX_MERGE_PREP_RUNS = 5` ceiling unchanged (which counts `Merge-Prep-By:` commits;
the mechanic's trailer is `Mechanic-By:`). Justification for the value and the mechanism:

- **5 is conservative.** A healthy convergent fix loop produces 1–3 mechanic commits.
  Reaching 5 without converging green is strong evidence of a structural problem (a fix the
  agent keeps re-attempting, an approach the reviewers keep rejecting, or a genuinely
  human-judgement issue) — exactly the case that should escalate, not spin.
- **Mathematically bounded.** Counting actual commits caps total mechanic activity
  regardless of the success/failure mix — a convergent oscillation (e.g. mechanic ↔ lint)
  cannot exceed `MAX_MECHANIC_RUNS` mechanic commits.
- **Label-free, comment-parsing-free, transparent.** The count is derived from immutable
  git history (`git log --grep`), visible to any reader, with no external state to query —
  the same robustness argument that retired v1's comment-counted cascade limit (PR 582
  post-mortem). The same principle governs PASS review bodies: no prose is posted in a
  PASS review body (§4.2 PASS body contract) — the reasoning lives in the commit-status
  `description`, which is compact, clickable, and carries no prose to parse.
- **Calibrate after real PRs.** 5 is provisional; review actual `Mechanic-By:` counts over
  the first ~20 admitted PRs and adjust. Too low → false escalations; too high → defeats the
  purpose.

**(B) Per-pass wall-clock cap (backstop).** Each mechanic invocation runs under the GHA job
`timeout-minutes` ceiling (carry v1's `timeout-minutes: 55` on `agent-merge-prep.yml`).
This bounds the worst-case duration of a _single_ pass (GitHub cancels the job at the
limit); it does **not** bound the aggregate loop — that is axis (A)'s job. A cancelled pass
is treated as a failed pass for the purpose of the exhaustion handler.

**On exhaustion — the loop STOPS and ESCALATES (never silently merges, never silently
abandons).** When `MECH_COUNT >= MAX_MECHANIC_RUNS` and the PR is still not green
(any of `enforcer-status` / `qa-status` / a required cheap check red, or the PR
`CONFLICTING`), the loop terminates with this **exact end state**:

1. **The mechanic agent does not commit, does not approve, does not merge.** It posts a
   single **escalation/rejection PR review** (state `REQUEST_CHANGES` or `COMMENT` with a
   clear "loop ceiling reached" heading) that names **each still-red signal individually**
   (which of enforcer / qa / which cheap check / conflicts), what it attempted across the
   passes, and precisely what a human must decide or do to unblock.
2. **The workflow's exhaustion handler** (the post-agent step, holding `AOPS_BOT_GH_TOKEN`
   — the agent's own token lacks `statuses: write`, §4.7) sets `mechanic-status: failure`
   on HEAD with a descriptive message
   (`"Halted: Stage-2 loop ceiling reached (N mechanic commits)"`).
3. **`admit-status` is reset to `pending`** by the same handler. This is the mechanism that
   "surfaces the PR back to the human admit gate": resetting admission means the PR cannot
   merge on the stale "good idea" decision, and the maintainer must **re-approve the PR** to
   re-admit (after intervening), or decline. Because admission is otherwise **sticky** (§5 —
   a push never revokes it), loop exhaustion is one of the two terminal events that does (the
   other being a §3.10 changes-requested review).
4. **The PR is left un-merged.** Because the required reviewer status(es) are red **and**
   `admit-status` is now pending, the armed auto-merge cannot fire. No silent merge.
5. **The maintainer is pinged** (`gh pr edit --add-reviewer nicsuzor`) so the escalation
   is visible, not buried.
6. **The loop stops auto-dispatching the mechanic.** Resumption requires an explicit human
   action: **re-approve the PR** to re-admit (after intervening), or use the **Force Review**
   escape hatch (§3.12) to re-run the reviewers directly. This mirrors v1's "manual retry
   resets the halt" semantics.

> Net: on exhaustion the PR sits **admitted-no-more, reviewer-red, un-merged, with a named
> escalation review and the maintainer requested.** A reader can implement this without
> guessing the cap (`MAX_MECHANIC_RUNS = 5`, counting `Mechanic-By:` commits) or the
> on-exhaustion state (mechanic-status=failure, admit-status=pending, no merge, escalation
> review posted, maintainer pinged, auto-dispatch stopped).

### 3.8 Pre-admission mechanical responder — **LIVE** (Phase 8)

The pre-admission mechanical responder is the carried-forward value of the old `merge-prep` step: clearing mechanically-fixable red **before** the human admission click, so the maintainer sees a clean picture of what actually needs judgment, not noise from fixable issues.

**Design rationale (Nic, 2026-06-17).** Admission = the human's "this is a good idea — make it mergeable." After Phase 5 shipped the Stage-2 mechanic (post-admission), nothing responded to a fixable REVISE before the human clicked Approve — a converged-red pre-admission PR would sit waiting even when the red was purely mechanical. This section restores that response, correctly shaped.

The responder is **NOT** the Stage-2 mechanic run earlier. It is a distinct, tightly-scoped agent (option (a) per design decision [[mem-b282d863]]):

| Property            | Pre-admission responder (§3.8)                              | Stage-2 mechanic (§3.3/§3.6)                      |
| ------------------- | ----------------------------------------------------------- | ------------------------------------------------- |
| When                | Pre-admission, Stage 1 converged with red                   | Post-admission (`admit-status=success`)           |
| Budget              | `timeout-minutes: 30`, `MAX_RESPONDER_RUNS=3`               | `timeout-minutes: 55`, `MAX_MECHANIC_RUNS=5`      |
| Scope               | Mechanical fixes only — NO judgment calls, NO full dev work | Real development to clear any red                 |
| Conflict resolution | **NO** — unreachable on conflicting PRs (§3.11)             | YES — full mechanic treatment                     |
| Status              | `responder-status` (informational, never required)          | `mechanic-status` (informational, never required) |

**The mechanical/judgment boundary is load-bearing.** The responder reuses the enforcer's existing classification (`.github/agents/enforcer.agent.md` §3):

- **Mechanical** (fix and commit): typos, missing required frontmatter, orphan files, misnamed tools, wrong paths, failing CI that needs a deterministic code fix. (Merge conflicts are **out of scope** for the responder — a conflicting PR never reaches it; see §3.11. Conflict resolution is the post-admission mechanic's job alone.)
- **Judgment** (do NOT touch): design trade-offs, scope objections, strategic concerns, recusal flags (`#recusal`), anything where "what is correct?" requires human decision.

Judgment-call and recusal REVISEs must surface to the human gate **unmodified**. The responder must not attempt to auto-apply them, and must not dismiss them.

**Dispatch triggers — enforcer, qa, AND Pytest red (#1965).** The responder exists to clear mechanically-fixable red pre-admission, and **failing CI is explicitly mechanical** (per `enforcer.agent.md` §3 / the §3.8 boundary table: "failing CI that needs a deterministic code fix"). The eligible dispatch triggers on HEAD are therefore:

- `enforcer-status == failure`, OR
- `qa-status == failure`, OR
- the `Pytest` check-run `== failure` **and that failure is attributable to the PR's own diff** (see the base-broken guard below).

**Why Pytest is read differently from enforcer/qa.** `Pytest` is a **GitHub Actions check-run**, not a commit status, so it never appears in the `commits/{sha}/statuses` API that `check-mechanical-red.sh` reads for `enforcer-status`/`qa-status`/`admit-status`. This was the root cause of #1965: a PR whose only red was Pytest satisfied neither status condition, so the no-op-on-green guard fired and **no responder was dispatched** — the PR sat stranded red (observed on #1955/#1956/#1957, 2026-06-24). The fix passes HEAD's Pytest result into the gate deterministically as `PYTEST_RESULT` (the `needs.pytest.result` of the same `pr-pipeline.yml` run). `check-mechred` now declares `needs: [lint, enforcer, qa, pytest]`, so the `Pytest` check-run is **terminal** when the gate evaluates — no polling, no race. `pytest` finishes well before the slow enforcer/qa agents, so it adds no critical-path latency.

**Base-broken Pytest guard (the #1965 aggravating factor — anti-thundering-herd).** A test broken on the **base branch** reddens Pytest on _every_ PR. Naively dispatching the responder for it would spawn a thundering herd of useless runs, because the responder **cannot fix a base failure from a PR branch**. So a Pytest failure is an eligible trigger **only when Pytest is not also failing on the base branch**. `check-mechanical-red.sh` determines this conservatively: when (and only when) enforcer + qa are both green and `PYTEST_RESULT == failure`, it queries the latest **completed** `Pytest` check-run on `origin/$BASE_BRANCH` (live via the check-runs API; injectable as `BASE_CHECK_RUNS_JSON` for tests):

- base Pytest `failure` → **not attributable** to the PR → skip, surface to human.
- base Pytest `success`, or no completed base run found → **attributable** to the PR's diff → dispatch.
- base state **unverifiable** (live API error) → **fail closed** (skip, surface to human) rather than risk a herd.

This is deliberately conservative: a PR that introduces a _new_ Pytest failure on top of an already-broken base is also suppressed (it cannot be distinguished from inherited base breakage without per-test diffing, which is out of scope). That trades a few missed dispatches for hard protection against the herd; such PRs surface to the human like any other un-cleared red. When the base is fixed, the next push re-evaluates and the responder dispatches normally.

**No-op-on-green guard (the crux — PR #1614 / P5 applied pre-admission).** The `check-mechred` job in `pr-pipeline.yml` reads `enforcer-status` and `qa-status` on HEAD using `scripts/ci/check-mechanical-red.sh`. If both are `success` **and there is no PR-attributable Pytest red**, the guard fires (`has_mechanical_red=false`) and `pre-admission-responder` is **skipped immediately**. This is the same cost pathology that motivated P5 — a green PR must never spawn a runner for the responder, no matter what.

**Stage-2 guard.** `check-mechanical-red.sh` also checks `admit-status`. If `admit-status=success` (PR already admitted), the responder is skipped and the Stage-2 mechanic (§3.3) handles any remaining red. The responder must not run alongside the Stage-2 loop — `check-admit`'s `needs: [pre-admission-responder]` ensures the responder completes (or is skipped) before `check-admit` dispatches the mechanic.

**Ceiling guard.** `check-mechanical-red.sh` counts `Responder-By:` commits on the branch since it diverged from the base (`git log "origin/$BASE_BRANCH..HEAD" --grep="^Responder-By:"`). At `MAX_RESPONDER_RUNS = 3`, the guard fires and the PR surfaces to the human even with mechanical red remaining — pre-admission budget is bounded tighter than Stage-2 because this is work on un-blessed changes the maintainer may still reject.

**How it fits in the Stage-1 cost order.** The responder is appended to Stage 1's cost order AFTER `qa`:

```
lint → enforcer → qa → [check-mechred] → [pre-admission-responder]
```

`check-mechred` runs after Stage-1 convergence (same convergence precondition as `check-admit`) and additionally `needs: [..., pytest]` so HEAD's `Pytest` check-run is terminal when the gate reads `PYTEST_RESULT` (#1965). If the responder commits a fix, it stamps `Responder-By:` and pushes; the new `synchronize` cancels the current run and restarts Stage 1 on the new SHA. Enforcer + qa re-verify the new SHA per the normal loop-skip protocol (§10).

**Dispatch sequence.** `check-admit` now `needs: [lint, enforcer, qa, pre-admission-responder]`. For Stage-2 passes (admitted PRs), `check-mechred` immediately returns `has_mechanical_red=false` (Stage-2 guard fires), `pre-admission-responder` is skipped, and `check-admit` proceeds with only a ~5s `check-mechred` overhead — negligible on the Stage-2 critical path.

**`responder-status`** is informational and must **never** be added to the branch-protection ruleset (§7). It is a diagnostic surface for the SHA-skip check and for human readers of the Actions log; it does not gate merge.

### 3.9 Draft-PR guard — expensive jobs skip on drafts; fire on `ready_for_review` — **LIVE**

Draft PRs are WIP. Running the full agent pipeline on a draft burns expensive invocations before the author has even marked the work ready for review.

**Which jobs skip on a draft PR:**

| Job                                                         | Guard mechanism                                                                                 |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `enforcer`                                                  | `github.event.pull_request.draft == false` (explicit)                                           |
| `qa`                                                        | `github.event.pull_request.draft == false` (explicit)                                           |
| `pre-admission-responder`                                   | `github.event.pull_request.draft == false` (explicit)                                           |
| `mechanic` in `admit-on-review.yml` approve path            | `github.event.pull_request.draft == false` (explicit, on the `mechanic` job)                    |
| `authorize` + `admit` in `admit-on-review.yml` approve path | `github.event.pull_request.draft == false` (explicit, on the `authorize` job; `admit` inherits) |
| `authorize-changes` + `mechanic-review-response` (§3.10)    | `github.event.pull_request.draft == false` (explicit, on `authorize-changes`)                   |
| `review-attestation`                                        | `github.event_name != 'pull_request' \|\| github.event.pull_request.draft == false` (explicit)  |
| `mechanic` in `pr-pipeline.yml` (`check-admit → mechanic`)  | **Dependency-starvation cascade** — no explicit draft guard needed (see below)                  |

**Which jobs continue running on drafts (cheap mechanical checks):** `gate`, `guard-no-dist`, `initialize`, `alignment-queue`, `lint`, `typecheck`, `pytest`, `check-mechred`, `check-admit`.

**Why the `pr-pipeline.yml` mechanic has no explicit draft guard — and why it is still safe.**

The `mechanic` job in `pr-pipeline.yml` is gated solely on `needs.check-admit.outputs.admitted == 'true'`. There is no `draft == false` condition on this job, and none is needed:

1. On a draft PR, `enforcer` and `qa` are **skipped** (their explicit `draft == false` guards fire), so `needs.enforcer.result == 'skipped'` and `needs.qa.result == 'skipped'`.
2. `check-admit`'s `if:` requires `(needs.enforcer.result == 'success' || needs.enforcer.result == 'failure')` and likewise for `qa`. Neither `'skipped'` value satisfies either branch.
3. Therefore `check-admit` is **never satisfied on a draft** — its `if:` is false, the job is skipped, and its output `admitted` defaults to `''` (not `'true'`).
4. The mechanic's `if: needs.check-admit.outputs.admitted == 'true'` is therefore false and the mechanic **never runs on a draft**.

This is the **dependency-starvation cascade**: the draft guard on `enforcer`/`qa` propagates upward through `check-admit` to starve the mechanic of admission, without requiring a redundant draft guard on the mechanic job itself. Commit `5c02d639` removed the previously-redundant explicit guard; the safety invariant is structural, not a condition string.

The `admit-on-review.yml` approve-path mechanic retains its own explicit `draft == false` guard because that path is triggered by a review event (not the push-driven pipeline) and has a shorter dependency chain that does not benefit from the same starvation cascade.

**The activation edge is `ready_for_review`.** The `pull_request` trigger already includes `types: [opened, synchronize, ready_for_review, reopened]` — keep it. When the author converts a draft to ready, the `ready_for_review` event fires the pipeline and all expensive jobs run on HEAD SHA.

> **The draft guard is not the only guard on `enforcer`/`qa`.** On a _ready_ (non-draft) PR the expensive reviewers are _additionally_ gated by the **fire-once gate (§3.1)**: they fire on `ready_for_review`/`opened`/`reopened` and at the admission boundary (§5), but **not** on a pre-admission `synchronize`. The same dependency-starvation cascade documented above carries that skip through `qa`/`check-mechred`/`check-admit`/`mechanic`. So a green pre-admission push does not re-run the panel; see §3.1 for the gate clause and §5 for the admission-boundary re-fire.

**Behaviour on a draft PR.** `enforcer-status`, `qa-status`, and `review-attestation` are NOT posted while the PR is a draft. `review-attestation` also carries the draft guard so it does NOT run on a draft — this avoids a permanent red required-check on every WIP PR (it would otherwise fail closed because the reviewer statuses are absent). Draft PRs cannot merge regardless of required-check state; when the PR is marked ready, `ready_for_review` re-runs the pipeline and attestation posts on HEAD SHA.

**`workflow_call` path is unaffected.** The draft guard is conditioned on the event being a `pull_request` event (`github.event_name != 'pull_request' || github.event.pull_request.draft == false`). When `pr-pipeline.yml` is invoked via `workflow_call`, `github.event_name` is `workflow_call`, the left-hand side is true, and the expensive jobs run normally.

### 3.10 Request-changes response path — comment-scoped mechanic — **LIVE**

When a write-class maintainer submits a **`CHANGES_REQUESTED`** review on a ready (non-draft) PR, `admit-on-review.yml` dispatches the mechanic in `mode: review-response` via a second path parallel to the approve path. This is the "address the feedback" complement to the "admit the idea" path.

**What this path does:**

1. `authorize-changes` job verifies the reviewer is write-class (same permission check + ADMIT_ALLOWLIST as the approve path). Skips for non-write-class reviewers, for draft PRs, and if the pre-admission responder is currently in-progress on HEAD SHA (de-conflict guard, see below).
2. Re-reads live HEAD SHA (the PR may have advanced since the review was submitted).
3. Dispatches `agent-mechanic.yml` with `mode: review-response` — the mechanic's `AGENT_NAME` becomes `review-response`, its status context becomes `review-response-status` (informational, never required).

**What the `review-response` mechanic does (scope-constrained):**

- Addresses ONLY: (a) the body of all standing CHANGES_REQUESTED reviews, (b) unresolved inline review threads, (c) other reviewers' outstanding comments.
- Commits fixes with the standard `Mechanic-By:` trailer and replies to each addressed thread.
- Subject to the same `MAX_MECHANIC_RUNS = 5` ceiling (combined `Mechanic-By:` count across all mechanic passes on the branch).

**What the `review-response` mechanic MUST NOT do (explicit prohibitions):**

- Set `admit-status` — this path never admitted the PR.
- Arm `gh pr merge --auto` — the PR is not admitted.
- Approve the PR — `gh pr review --approve` is forbidden.
- Dismiss the triggering CHANGES_REQUESTED review — dismissal is the reviewer's decision alone.
- Broaden scope into work not specifically requested by the reviewer.

**After the mechanic commits:** the `synchronize` event re-triggers Stage 1 (lint → enforcer → qa). The reviewer re-reviews. If the reviewer then Approves, the approve path admits and arms auto-merge. The CHANGES_REQUESTED review stands until the reviewer explicitly re-reviews; the mechanic never overrides it.

**De-conflict with the pre-admission responder (§3.8, load-bearing boundary):**

| Agent                    | Triggered by       | Scope                                                        | Status context           |
| ------------------------ | ------------------ | ------------------------------------------------------------ | ------------------------ |
| pre-admission-responder  | push (synchronize) | mechanical CI red, pre-admission only (no conflicts — §3.11) | `responder-status`       |
| review-response mechanic | review submitted   | human reviewer comments, any admission state                 | `review-response-status` |

These two agents address orthogonal concerns and are triggered by different events, so they cannot both fire on the same event. The race scenario (review submitted while a responder run is already in-progress on the same SHA) is guarded: `authorize-changes` reads `responder-status` on HEAD before dispatching — if `pending`, the review-response dispatch is skipped for this review event. The mechanic workflow's concurrency group (`agent-mechanic-{PR}`) also queues review-response runs behind any in-flight Stage-2 mechanic run for the same PR.

**`review-response-status`** is informational — posted by `agent-mechanic.yml` using the mode-derived AGENT_NAME — and is NEVER added to the branch-protection ruleset (§7). It is a diagnostic surface for SHA-skip and for human readers.

### 3.7 Fail-closed liveness + named-reviewer-on-this-SHA attestation (#1450) — **LIVE** (in-repo)

The autonomous-trust model treats "the documented review-agent chain executed" as a
load-bearing merge signal. The forensic RCA behind issue #1450 found two ways that signal
silently lies, and §3.7 closes both:

**Reason A — a dead pipeline is invisible-by-default.** When the deep-review pipeline is in
`startup_failure` (e.g. a missing required input to a reusable workflow pinned to a moving
`@main`), it produces **no notification and no status** — the named review status is simply
_absent_ on the merged SHA, and **absence is silently treated as a pass**. The named reviewer
statuses (`enforcer-status`, `qa-status`) are required, so in _this_ repo a dead run normally
leaves them absent → unmergeable; but absence is a fragile signal (a consumer that forgets to
require a status, or a single failed run that never re-posts, reads as "nothing wrong").

**Reason B — the success-gate inverts the review gradient.** When the deepest reviewers are
gated on "checks are green", a red PR gets **less** review, not more — review is routed away
from exactly the riskiest PRs. (§3.4 fixes the in-repo instance: a red enforcer _verdict_ no
longer suppresses `qa`.)

**The fix — one explicit, fail-closed, required attestation.** The orchestrator's
`review-attestation` job (`if: always()`, after `enforcer` + `qa`) **independently re-reads
each named reviewer's commit status on the exact head SHA** and posts a single
`review-attestation` status:

- `success` **only if** every named reviewer (`enforcer-status`, `qa-status`) posted a genuine
  terminal `success` whose §10 `target_sha` query-param equals **this** head SHA — i.e. a
  _named_ reviewer _provably ran on this exact diff_. This is the AC1 attestation.
- `failure` otherwise — **absent**, pending, red, or **stale** (a success whose `target_sha`
  is a _different_ SHA). Default-deny: anything short of positive proof of a live pass on this
  SHA fails closed. This is the AC2 liveness guarantee.

Why this is stronger than "just require the two statuses":

1. **It converts silent absence into an explicit signal.** Because the job runs `if:
   always()`, whenever the workflow runs at all it posts an explicit `review-attestation`
   (RED when a reviewer is absent/stale), rather than leaving the reader to notice a missing
   status. The decision does **not** trust the enforcer/qa _job results_ — it re-reads the
   _posted status on the SHA_, so a skipped job, a crashed status step, or a stale carry can't
   launder into "attested".
2. **A startup_failure still cannot read as a pass.** `review-attestation` is a **required**
   check (ruleset `13762049`). If the whole workflow fails to start (posts nothing), the
   required check is unsatisfied → the PR is **unmergeable**. Absence → blocked, never pass.
3. **Stale-SHA defence.** Keying on the `target_sha` channel (§10) means a green verdict
   carried from an _earlier_ SHA does not attest the diff that actually merges (the §3.5
   property, enforced as a gate rather than relied on as an emergent side effect).

The decision logic is the pure, unit-tested `scripts/ci/review-attestation.sh` (the `gh api`
fetch is isolated behind `STATUSES_JSON` so the genuineness/staleness/absence rules are tested
without a `gh` stub — `tests/test_review_attestation.py`). The reviewer set is configurable
(`REVIEWERS`, default `enforcer-status qa-status`) so cross-repo consumers (§9) attest their
own named reviewer set.

**Actionable failure message.** The commit-status `description` is length-capped, so it
carries only the terse per-reviewer token list (`enforcer-status:absent qa-status:stale …`).
On failure the script additionally writes a **cause-and-remedy breakdown to the GitHub
Actions run summary** (`$GITHUB_STEP_SUMMARY` — the check/Actions UI): a per-reviewer state
table plus what each state means and how to fix it (`absent` → the PR is likely un-admitted,
approve it or run **Force Review** §3.12; `stale` → reviewed a different commit; `failure`
→ a genuine red verdict to address). This keeps the required check terse while making the
"why is this red and what do I do" answer visible where the maintainer actually looks.

> **Scope honesty.** The in-repo deliverables — the `review-attestation` job, the fail-closed
> decision script + tests, and the `review-attestation` entry in the ruleset _file_ — are
> **LIVE in the repo**. _Applying_ that ruleset entry to the live branch protection is a
> deploy step (`scripts/sync-ruleset.sh`, admin token), the same as every prior ruleset change
> (§7). Two residual integrity dependencies live in repo Settings, **out of any worktree** and
> therefore out of scope here: the `bypass_actors` admin role (an admin can still force a merge
> — a deliberate, visible act, not a silent default). (The `pr-fix-loop` Environment that used
> to be a third such dependency is retired — admission is now a PR review approval, §3.2.)
> §3.7 closes the _silent-absence-reads-as-pass_ hole; it does not, and cannot from a worktree,
> override a deliberate admin bypass.

### 3.11 Admitting a conflicting PR — GitHub's merge-ref constraint — **LIVE**

A PR that is `CONFLICTING` with its base never receives a `pull_request` workflow run.
GitHub builds the `refs/pull/N/merge` ref that a `pull_request` run checks out by
test-merging head into base; a merge conflict makes that ref un-buildable, so GitHub
**silently never creates the run** — no jobs, no logs, no status, no notification. This is
GitHub platform behaviour, not a pipeline choice (community discussions
[#11265](https://github.com/orgs/community/discussions/11265),
[#26304](https://github.com/orgs/community/discussions/26304)).

> **Worked example — PR #2005 (branch `agy`).** Opened CONFLICTING with `dev`. Its `opened`
> event, and a later manual close/reopen, each fired **only** the `pull_request_target`
> retarget check; the `pull_request` PR Review Pipeline produced **zero** runs on the head
> SHA. Author had `write` access and the PR was non-draft — the sole cause was the conflict.

**Consequences (normative):**

1. **Stage-1 triage (§3.1) and the pre-admission responder (§3.8) never see a conflicting
   PR.** Both live in `pr-pipeline.yml` on the `pull_request` event, which does not fire.
   Conflict resolution is therefore **not** the responder's job — the responder is
   unreachable on exactly the PRs that have a conflict, and its dispatch gate
   (`check-mechanical-red.sh`) has no conflict trigger anyway (§3.8 lists its triggers:
   enforcer/qa/Pytest red only). Conflict resolution belongs **solely to the post-admission
   mechanic** (§3.3).
2. **A conflicting PR can still be admitted.** The events that DO fire on a conflicting PR
   are `pull_request_target` (the retarget guard) and `pull_request_review`. Admission is a
   review approval handled by `admit-on-review.yml` on `pull_request_review` (§3.2), which
   fires regardless of mergeability. The maintainer approves a conflicting PR exactly as any
   other — "good idea; make it mergeable" explicitly includes "resolve the conflict."
3. **On admission, the mechanic is dispatched directly by `admit-on-review.yml`** (the review
   event re-enters on the admitted SHA), not by a `pull_request` run that would never fire.

**The dispatch rule (load-bearing).** `admit-on-review.yml`'s `decide-mechanic` job dispatches
the mechanic when the PR is `CONFLICTING` **even if the named reviewers are both green**.
Mergeability is an INDEPENDENT merge gate; "reviewers green" is not sufficient to skip the
mechanic on a conflicting PR. Keying the first-dispatch decision on reviewer colour ALONE was
a deadlock: a conflicting-but-green PR got `need_mechanic=false`, armed an auto-merge that can
never fire (`CONFLICTING` is unmergeable), and nothing ever resolved the conflict. The job now
reads `gh pr view --json mergeable` (polling until it settles) alongside the reviewer statuses
and dispatches when red/pending reviewers remain **OR** the PR is `CONFLICTING`.

**Resumption.** Once the mechanic merges `origin/<base>` into the head and pushes (§3.3, §1 of
`mechanic.agent.md`), the PR becomes `MERGEABLE`. That push is a `synchronize` that **does**
fire the normal `pull_request` pipeline, so Stage-2 re-verification (§3.5), passes 2…N
(`check-admit → mechanic`), and the armed auto-merge all resume the standard flow. The
conflicting-state special case is confined to the **first** dispatch, on the review-approval
path.

> **Residual edge.** If the mechanic's resolution does not fully clear the conflict (the base
> advanced again mid-loop, or a squash-merge ghost conflict — `mechanic.agent.md` §1b), the new
> head SHA is still `CONFLICTING`, so no `pull_request` run re-fires and the auto-loop stalls.
> The PR is re-entered by the next review approval (re-dispatches via this same path), by a
> human push, or by the **Force Review** escape hatch (§3.12). The §3.6 exhaustion handler still
> bounds repeated mechanic passes within a single admission.

### 3.12 Force Review — manual escape hatch (Nic, 2026-06-29) — **LIVE**

When a PR is **wedged** — the pipeline failed to start, a reviewer status is stuck
`absent`/`stale`, or admission/triage state is inconsistent — a maintainer needs a way to
**force the named merge-gate reviewers to run** without fighting the normal event flow.
`.github/workflows/force-review.yml` is that hatch:

- **Trigger:** `workflow_dispatch` (Actions → _Force Review_ → Run workflow → enter the PR
  number; pick `enforcer + qa`, `enforcer only`, or `qa only`).
- **Mechanism:** a `resolve` job reads the PR's live head `ref`/`sha` from the number, then
  calls the **same reusable reviewer workflows the pipeline uses** (`agent-enforcer.yml`,
  `agent-qa.yml`) with explicit inputs. The verdicts they post (`enforcer-status`,
  `qa-status`) are byte-identical to a normal run and satisfy `review-attestation` on that
  SHA once green (§3.7).
- **Bypasses admission ON PURPOSE.** The hatch exists precisely for when admission/triage
  state is broken, so it does not consult `admit-status`. It does **not** merge anything — it
  only re-runs the reviewers; merge still requires all required checks green **and** admission
  (`admit-status`). So the escape hatch can unstick the _reviewers_ without weakening the
  _merge gate_.

This is the remedy the §3.7 `review-attestation` failure summary points the maintainer to
when reviewers read `absent`/`stale`.

## 4. Per-agent contract (locked)

Every agent in the pipeline — enforcer, qa, mechanic, alignment, and any future agent —
obeys these rules. Enforcer and qa already implement them (**LIVE**); they are the template
the mechanic must follow (**SPEC-ONLY** until Phase 5).

### 4.1 `workflow_call` is the only invocation surface — **LIVE** (enforcer, qa)

The agent's workflow file declares **only** `workflow_call`. No `pull_request`, no
`workflow_run`, no `schedule`, no `push`. Triggers are a separate concern: the orchestrator
(Stage 1/2) and consumer shims (§9) compose them. This is what guarantees no agent
self-triggers, which is what makes §3.4 convergence possible.

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
    outputs:
      committed:
        description: "true if this agent pushed a commit in this pass (drives §3.4 short-circuit)"
        value: ${{ jobs.<job>.outputs.committed }}
```

> **Known LIVE wart (transitional).** Today both `trigger-enforcer.yml`/`trigger-qa.yml`
> (which fire on `pull_request`) **and** the `pr-pipeline.yml` orchestrator (which calls
> `agent-enforcer.yml`/`agent-qa.yml` via `needs:`) dispatch the same agents on each push.
> The per-SHA loop-skip (§10) dedupes the _review work_ (the second invocation on the same
> SHA short-circuits to a no-op success), but the double _dispatch_ is real and is a tracked
> cleanup (release-publish §9 C4). The agent files themselves remain `workflow_call`-only;
> the duplication is in the trigger surfaces.

### 4.2 One named commit status, posted to HEAD SHA — **LIVE** (enforcer, qa)

The status name **equals** the agent name with `-status`:

| Agent                           | Status name        | Required gate?                                 | State         |
| ------------------------------- | ------------------ | ---------------------------------------------- | ------------- |
| Enforcer (rbg)                  | `enforcer-status`  | yes                                            | **LIVE**      |
| QA (marsha)                     | `qa-status`        | yes                                            | **LIVE**      |
| Pre-admission responder (§3.8)  | `responder-status` | **no** (work, not a gate — informational only) | **LIVE**      |
| Mechanic / dev (was merge-prep) | `mechanic-status`  | no (work, not a gate)                          | **LIVE**      |
| Alignment (pauli)               | `alignment-status` | **no** (advisory, §6)                          | **SPEC-ONLY** |

> **Naming reality check.** The agent name is settled as **`mechanic`** (status
> `mechanic-status`) — a locked decision, now **LIVE**: `agent-mechanic.yml` +
> `.github/agents/mechanic.agent.md` exist; the v1 `agent-merge-prep.yml`,
> `merge-prep-cron.yml`, and `merge-prep.agent.md` are **deleted**. `merge-prep-status` is
> no longer written by any workflow; `mechanic-status` is what the post-admission agent
> posts (informational, never required).
>
> **`mechanic-status` necessity (resolving v2's open question).** The mechanic does work,
> not a verdict, so it is **not** a required gate. But §3.6 needs a surface to record the
> exhaustion/halt outcome, so `mechanic-status` exists as a **non-required, informational**
> status (`pending` while working, `success` on a clean converged pass, `failure` on loop
> exhaustion). It never gates the merge — the merge gate is enforcer + qa + cheap checks +
> admit.

Skip is a **success outcome with descriptive text** — never `exit 1`. Examples: `success` /
"Skipped: HEAD SHA already reviewed" (§10); `failure` / "2 axiom violations — see review"
(real verdict).

**PASS review body contract (readability).** On a PASS (APPROVED) verdict, the agent posts a
**marker-only** review body — no reasoning block. On a REVISE (CHANGES_REQUESTED) verdict,
the full reasoning lives in the review body (the mechanic consumes it). The two formats:

| Path              | Review body                                                                      | Status `description`                                                     |
| ----------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| APPROVE           | `## Enforcer Review — clean` / `# QA Verification — VERIFIED` (marker line only) | `"Axiom-clean"` / `"3/3 dimensions pass"`                                |
| CHANGES_REQUESTED | Full reasoning + violation list (mechanic reads this)                            | `"Violations found — see review"` / `"Verification failed — see review"` |

The marker token (`## Enforcer Review` / `# QA Verification`) MUST remain in every body —
the SHA-skip check and dismiss step grep `.body` for it; an empty/missing body silently
breaks idempotency. The reasoning surface for a PASS is the commit-status `description`;
do not duplicate it in the review body. No consumer parses PASS review bodies: gating reads
review `.state` (APPROVED / CHANGES_REQUESTED) and the mechanic only reads CHANGES_REQUESTED
bodies.

### 4.3 One row in `specs/ENFORCEMENT-MAP.md`

Every agent declares which axioms / rules / lifecycle points it covers, under the
"PR-pipeline agents" section. A PR adding an agent that omits its enforcement-map row fails
enforcer review.

### 4.4 One `.github/agents/<name>.agent.md` prompt file

The prompt file is the agent's behaviour contract. It sources the canonical personality
(e.g. `aops-core/agents/rbg.md`) and adds PR-context wrapping (read `.agents/CORE.md`, run
`gh pr view`, format the review). Orchestration (the workflow) and behaviour (the prompt)
version independently.

### 4.5 Canonical consumer ref — `@dev` (branch) — **LIVE** (decision Nic, 2026-06-23; mem-94ad94c1)

Satellite-repo trigger shims call the aops reusable workflows by **branch ref `@dev`**, not
versioned tags (`@enforcer-v1`, `@qa-v1`, `@pipeline-v1`).

**Rationale (single-owner fix-forward fleet):** versioned tags (`-vN`) earn their cost only
when you must run two pipeline versions simultaneously — a public-action concern, not ours.
We own every satellite repo and fix forward; we would never deliberately leave a satellite on
an old pipeline. A moving tag (`@pipeline`, advanced manually on every green change) was the
other candidate but requires discipline that is easy to forget. A branch ref (`@dev`)
auto-updates with zero maintenance. Tradeoff accepted: satellites following `@dev` inherit
dev's churn (a half-finished pipeline commit can momentarily break satellites). Acceptable
because the fleet is small, single-owner, and fix-forward; breakage is caught on the first
satellite and fixed at HEAD.

### 4.6 Per-pass SHA-based loop-skip — **LIVE** (enforcer, qa)

Every agent checks "have I already reviewed _this exact SHA_?" before doing expensive work
— never "was the last commit authored by a bot?" (the v1 anti-pattern that caused P2). Full
protocol in §10.

### 4.7 Graduation/status writes are workflow-owned, not agent-owned — **LIVE**

The Claude agent runs under the `anthropics/claude-code-action@v1` token (the Claude GitHub
App installation token), which **lacks `statuses: write`** — any `gh api .../statuses/$SHA`
call from inside the agent returns `403 Resource not accessible by integration`. So all
status writes and merge arming live in the **workflow's** shell steps, which hold
`AOPS_BOT_GH_TOKEN` (a bot PAT with `statuses: write`). The agent's job ends at "post the
review / commit fixes"; the workflow's post-agent steps set the statuses and arm auto-merge.
This split is intentional and applies to enforcer, qa, the admission job, and (at Phase 5)
the mechanic's exhaustion handler (§3.6). The defunct `summary-and-merge.yml` dispatch and
the agent-side `merge-prep-status` write that v1 instructions once carried were removed for
exactly this reason (PRs #735/#754).

## 5. Graduation — `admit-status` + armed auto-merge — **LIVE**

Graduation is deliberately cheap for an already-reviewed PR: no agent, no checkout. When
the fire-once gate (§3.1) left the admitted SHA un-reviewed, the admission boundary also
re-fires the reviewers on it (the agent cost the pre-admission pushes saved is paid here,
once).

- `admit-on-review.yml` (§3.2), on a maintainer's PR **review approval**, does: (1) sets
  the required **`admit-status`** to `success` on the admitted SHA, (2) arms
  `gh pr merge --auto --squash --delete-branch`, then (3) classifies the named-reviewer
  state on the admitted SHA (`reviewers_green`) and acts on it:
  - **already green** (PR admitted right after its ready-review, no intervening pushes) →
    auto-merge handles the merge; no re-verification, no mechanic.
  - **not green** (absent because the §3.1 gate skipped the reviewers on pre-admission
    pushes, OR red) → **re-fire the reviewers on the admitted SHA** (`admit-enforcer` →
    `admit-qa`, the same reusable workflows the pipeline uses) and **recompute the
    required `review-attestation`** on that SHA (`admit-attestation`, post-only — it does
    not re-run the reviewer agents, just reads their posted statuses and posts attestation).
    not fail-closed-exit, so a legitimately-red re-verify does not fail the run). Then
    `decide-mechanic` re-reads the settled reviewer state and dispatches the mechanic's
    first pass **only if red/pending remains**; if the re-verify came back green,
    auto-merge fires with no mechanic.
- This re-fire is what makes the §3.1 fire-once gate safe against the fail-closed
  `review-attestation` required check (§3.7, §7): the admitted SHA always ends with
  `enforcer-status`, `qa-status`, and `review-attestation` posted on it, so auto-merge can
  fire for a clean PR **without** depending on the mechanic pushing a commit (the deadlock
  a naive "skip reviewers until admitted" gate would create when the mechanic has nothing
  to do).
- The merge fires the moment **all required checks are green and the PR is mergeable** —
  immediately for an already-green PR, or after the admission re-verify / Stage-2 loop
  converges green.
- **`admit-status` replaces v1's `merge-prep-status`** as the required gate. Because it is
  set by a human-approval-driven job rather than a merge-prep run, the no-op runner on every
  green PR (P5) is gone.
- **Carry-forward — STICKY admission (LIVE, in `pr-pipeline.yml`'s `initialize` job).** Once
  admitted at SHA _X_, `admit-status` carries forward across **every** subsequent commit —
  agent _or_ human — during the loop: admission is an _in-principle_ decision ("approved,
  proceed to the merge pipeline") made once, not re-judged on each push. The live rule: on
  `synchronize`, if the previous HEAD had `admit-status: success`, carry `success` forward to
  the new HEAD unconditionally. This is safe because enforcer + qa re-verify every SHA inside
  the loop (§3.5), so a carried admission never lets an unreviewed diff merge. Admission is
  revoked **only by a terminal state**, never by a push: (1) §3.6 **loop exhaustion** resets
  `admit-status` to pending, and (2) a §3.10 **changes-requested review** stops the loop.
  (Earlier model reset admission on any non-bot push; it keyed on GitHub account type `Bot` /
  `[bot]` login suffix, which misclassified the `botnicbot` service account — type `User` —
  as a human push and silently stranded admitted PRs. Worked example: PR #2005.)
- **`required_approving_review_count` stays `0` (LIVE).** v1 needed two approvals because
  merge-prep counted as approval #1. The merge gate is `admit-status` + the named-reviewer
  statuses, not a counted GitHub review. The review-approval admission model (§3.2)
  **reuses the Approve button as the admission _trigger_** without making it a counted
  merge-gate review: keeping the count at `0` means the approval drives `admit-on-review.yml`
  (which sets `admit-status`) but is not itself a required merge approval, so "dismiss stale
  reviews" semantics never bear on admission — admission persists as `admit-status` (sticky
  carry-forward until a terminal state, above).

> Sequencing (already done): `admit-status` was added to required checks in the _same_ change
> that dropped approvals to 0 — otherwise there would be a window where green checks alone
> permit a manual merge that bypasses the gate. This is **LIVE** in ruleset `13762049`.

## 6. Alignment (pauli) — advisory, host-side, not a gate — **PARTIALLY LIVE** (pending marker LIVE; issue queue DISABLED; host dispatch SPEC-ONLY)

Pauli's value is PKB context, and GHA cannot reach the Tailnet-internal PKB MCP (P3). The
**target**: pauli runs **host-side** (where the PKB lives), dispatched by a light host cron,
and posts a **review verdict** that informs the human gate (§3.2). It is **not** a required
status check.

**LIVE today:** the orchestrator's `alignment-queue` job (`pr-pipeline.yml`) posts
`alignment-status: pending` on HEAD — a cheap advisory marker that documents intent.

**DISABLED (aops-956c1842):** the same job used to ALSO file (or refresh) a single
`alignment:queued` GitHub issue per PR as a queue surface for a host drainer to consume.
That drainer (§6.2) is **SPEC-ONLY** and was never built, so the issue surface was a
**write-only spam loop** — verified live 2026-06-11 at 48 open / 0 ever closed, growing
one-per-PR-run with no consumer. The label + issue-filing steps have been removed; only the
`alignment-status: pending` marker remains. **The issue-queue surface MUST NOT be restored
until the host-side drainer in §6.2 actually ships** (follow-up task `aops-8f42f33d`); a
future SSoT/spec-sync pass must not re-derive it from this section on its own.

The **host-side cron + polecat-pauli dispatcher that drains the queue is not yet wired** —
so the live way for the maintainer to get an alignment read remains the **manual
`/strategic-review --critic` skill** (`aops-core/skills/strategic-review/SKILL.md`), which
they invoke by hand before admitting a PR. So alignment is **advisory input to the human
admit gate, produced manually**, until the host-side dispatch ships.

This is the deliberate simplification over an earlier draft that specced alignment as a
required, fail-closed gate with a watchdog. In the two-stage model the **human Environment
approval is the alignment decision point** — the maintainer reads pauli's verdict (or runs
it themselves) and decides. Consequences: no host-availability deadlock (if pauli has not
run, the maintainer admits on their own judgement); no watchdog, no `pending → failure`
flip, no required-status machinery.

### 6.1 Queue surface — pending marker **LIVE**; issue queue **DISABLED**

The triage orchestrator's `alignment-queue` job runs in parallel with the lint→enforcer→qa
chain (it never delays the merge-gate agents) and, on every same-repo push:

1. **Sets `alignment-status: pending`** on the HEAD SHA via the GitHub statuses API
   (**LIVE**). Skipped if `alignment-status` is already terminal
   (`success`/`failure`/`error`) on this SHA — that means pauli has already reviewed it and
   we must not overwrite the verdict.

It **no longer** files an `alignment:queued` GitHub issue. The original design upserted one
issue per PR (deterministic title `alignment:queued PR #<num>`, body in a stable
`<!-- aops:alignment-queue -->`-fenced block carrying `PR`/`Repository`/`Head ref`/`Head
SHA`/`Queued`) as a queue for the host dispatcher to drain. **That issue surface was removed
in aops-956c1842** because its only consumer — the §6.2 host drainer — is SPEC-ONLY and was
never built, making it a write-only spam loop (48 open / 0 closed at removal). When the §6.2
drainer ships (follow-up `aops-8f42f33d`), the issue-upsert step may be restored _as part of
that change_, together with its consumer — never before. Re-adding it without a drainer just
recreates the spam.

Fork-origin PRs are skipped at the job's `if:` (no bot write token).

### 6.2 Host-side cron + dispatcher — **SPEC-ONLY**

A host cron (outside this repo's worktree, where the PKB MCP is reachable) drains the
`alignment:queued` queue across the repos it watches. For each open issue it:

1. **Parses the queue entry** — extracts repo / PR / head SHA from the issue body
   (`<!-- aops:alignment-queue -->` block).
2. **Reconciles against the commit status** — re-reads `alignment-status` on the current
   HEAD; only dispatches if still `pending` (if the PR closed, was merged, or pauli already
   posted a terminal status, the cron closes the issue and moves on — this is the "close
   stale issues" contract).
3. **Dispatches `polecat run … pauli`** with the PR context. Pauli reviews the PR diff
   against PKB design intent and posts a PR review verdict (the maintainer reads this before
   approving the PR, §3.2) plus a terminal `alignment-status` (informational only — see §6.3).
4. **Closes the issue** when pauli's terminal status is posted on the current HEAD.

The dispatcher script lives outside this repo's worktree by design — PKB MCP reachability is
its precondition, and that lives host-side.

### 6.3 What pauli posts — **SPEC-ONLY**

Pauli posts (a) a PR review verdict the maintainer reads before approving the PR (§3.2), and
(b) a terminal `alignment-status` on HEAD (`success`/`failure`/neutral) — informational
only. Because the merge gate does not require `alignment-status`, a `failure` verdict does
not block merge; it informs the maintainer's admission decision. A missing alignment review
(host cron down, pauli unreachable) likewise does not deadlock the gate — the maintainer
admits on their own judgement.

> If pauli later proves reliable enough to gate on, promoting `alignment-status` to a
> required check is a one-line ruleset change — explicitly out of scope here.

## 7. Branch protection — required status checks — **LIVE** (API-verified)

The live ruleset (`.github/rulesets/pr-review-and-merge.yml`, ID `13762049`,
`enforcement: active`, applied to `refs/heads/dev`) requires — verified against the live
GitHub API on 2026-06-09 (the in-repo file and the live ruleset match):

```yaml
- type: required_status_checks
  parameters:
    strict_required_status_checks_policy: false
    required_status_checks:
      # Mechanical CI — academicOps emits check-run names (§8)
      - context: "Lint / Lint"
      # - context: "Type Check / Type Check"   # DISABLED — debt task aops-1c3de214
      - context: "Pytest / Pytest"
      # Framework agents — each owns its AND-gate slot
      - context: "enforcer-status"
      - context: "qa-status"
      # Fail-closed liveness + named-reviewer-on-this-SHA attestation (§3.7, #1450)
      - context: "review-attestation"
      # Human gate (Environment approval, §5) — NOT an agent
      - context: "admit-status"
      # NOTE: alignment-status is advisory (§6) and is NOT required.
      # NOTE: merge-prep-status is REMOVED (replaced by admit-status).

- type: pull_request
  parameters:
    required_approving_review_count: 0   # PR review approval drives admit-status (the human gate); not a counted merge review
    dismiss_stale_reviews_on_push: false
```

**No transitive gating.** Each agent owns its status directly; there is no single
`merge-prep-status` that an agent could forget to wait for or silently substitute.

> `mechanic-status` is **not** in this list and must never be added — the mechanic does work,
> not a verdict (§4.2). The reviewer statuses (`enforcer-status`, `qa-status`) are what
> ensure the mechanic's output is verified before merge (§3.5).

## 8. v1 merge-prep behaviour inherited by the mechanic (retrospective) — RETIRED at Phase 5

The v1 `merge-prep` agent (`agent-merge-prep.yml` worker + `merge-prep-cron.yml` cron/
`workflow_run` dispatcher + `.github/agents/merge-prep.agent.md` behaviour) is **deleted**
as of Phase 5. This section is **retrospective**: it preserves the still-true behavioural
contracts that the v1 agent embodied so they are not lost on deletion, and **every item
here is now the mechanic's responsibility** (implemented in `agent-mechanic.yml` +
`.github/agents/mechanic.agent.md`). The mechanic adds the §3.5 re-verify discipline and
the §3.6 bound on top. F1–F10 below remain the contract the mechanic must satisfy.

Folded behavioural contracts (each is what the mechanic must do):

- **F1 — Conflict resolution by merge, never rebase; never force-push.** Resolve conflicts
  with `git fetch origin <base>; git merge origin/<base> --no-edit`. Force-push is
  prohibited (it would rewrite shared history and dismiss approvals). **Live bug to fix at
  Phase 5:** `merge-prep.agent.md` hardcodes `origin/main`; the base is now `dev` — change
  to the repo's default branch (release-publish §9 C5).
- **F2 — Squash-merge ghost conflicts.** When a PR was stacked on another PR's branch and
  that upstream PR squash-merged into the base, the branch carries the upstream's
  un-squashed commits; GitHub reports `mergeable: CONFLICTING` even though `git merge
  origin/<base>` reports "Already up to date" (nothing to merge locally). Diagnostic
  signature: `mergeable == CONFLICTING` **and** local merge is a no-op/clean **and**
  `git log --oneline origin/<base>..HEAD` shows subjects already squashed into the base.
  Resolve carefully with a merge commit (never a force-push); if the resolution needs author
  judgement, halt with a "Blocked: squash-merge ghost conflict" comment naming the upstream
  PR. The live failure path detects this annotation specifically.
- **F3 — Ground truth is the server, not the working tree.** Every "Conflicts: none / CI
  passing / approval standing" claim must be verified against server state
  (`gh pr view --json mergeable,mergeStateStatus`, `gh pr checks --required`) **after** the
  last write to the branch. A clean local merge is not proof; only `mergeable: MERGEABLE`
  counts. A false "success" is worse than an honest halt — it arms auto-merge on a PR GitHub
  will refuse to merge.
- **F4 — Conflict vs review-decision are different blocking conditions** (from PKB node
  `pr-3a3dbf43`). `mergeable: CONFLICTING` is mechanically fixable (F1/F2);
  `reviewDecision: CHANGES_REQUESTED` is **not** — it requires addressing the review
  content. A PR can be `MERGEABLE` yet blocked by a standing `CHANGES_REQUESTED`. In
  particular, **scope-violation reviews (P#5 — bundled unrelated changes) cannot be resolved
  mechanically**: the options are split the offending commits into their own PR, re-scope/
  re-title the PR to own all changes, or dismiss only if the reviewer is demonstrably wrong.
  Re-running the fixer never unblocks a scope violation.
- **F5 — Feedback triage at the intent level, not the surface words.** Read ALL reviews
  (framework agents + Gemini + Copilot + humans). For each: FIX genuine bugs / CI failures,
  FIX safe improvements, DISMISS false positives with written justification, DEFER scope
  creep with a comment. For every human `CHANGES_REQUESTED`: state the inferred intent in one
  sentence, find **all** surface forms of that intent across the diff (not just the cited
  line), fix every one, and verify completeness. **Repeat-request escalation:** if a
  reviewer re-raises a point after you "addressed" it, that is evidence of surface-only delta
  — do not re-justify the same partial fix; either find the missed surface forms or halt with
  a precise list (the PR #974 routing-table incident is the worked example).
- **F6 — Refuse to approve while any `CHANGES_REQUESTED` stands.** The success path counts
  the latest review per author; if any is `CHANGES_REQUESTED` and undismissed, it sets the
  status to `failure` and refuses to approve/merge (it does not silently approve over a
  standing objection). This guard is the LIVE mechanism that keeps a fatal finding from
  merging silently.
- **F7 — Late-review re-qualification (the race).** The fixer can declare success, then a
  `CHANGES_REQUESTED` review arrives _after_ (e.g. an enforcer run triggered by the fixer's
  own commit finishes late). The dispatcher re-qualifies a `success` PR when a
  `CHANGES_REQUESTED` review's `submitted_at` is later than the success status's
  `created_at`, and (cron-only) when the base advanced and the PR is now `CONFLICTING`
  (`UNKNOWN` mergeability does **not** re-qualify — it means GitHub hasn't computed it yet).
  In the two-stage model this race is structurally reduced because the reviewers re-run per
  SHA inside the loop (§3.5), but the late-arriving-review case is preserved as a
  re-qualification trigger.
- **F8 — Self-loop detection + runaway ceiling.** Skip a run whose HEAD commit carries the
  fixer's own trailer (`Merge-Prep-By:`, → `Mechanic-By:` at Phase 5). Halt permanently at
  the **ceiling of 5** fixer-commits in the branch (the §3.6 bound; v1 counts `Merge-Prep-By:`
  via `git log origin/<base>..HEAD --grep`). v1 also halts after **3 consecutive run
  failures** (dismiss approval, set `failure`, notify). Both are loud halts requiring manual
  retry — never silent abandonment.
- **F9 — Bounded polling, no indefinite waits.** Never use `gh pr checks --watch`,
  `gh run watch`, or `tail -f` inside a runner — they leak background processes that burn the
  job's wall-clock budget and cause "timed out" failures. Use a capped poll loop; if the cap
  expires, halt and report. (This is the per-pass wall-clock discipline behind §3.6 axis B.)
- **F10 — Session artifacts on every run.** Agent workflows upload Claude session files as
  GHA artifacts (`~/.claude/projects/`, `if: always()`, 30-day retention) so resource-
  exhaustion failures (e.g. `FatalTurnLimitedError`) are diagnosable post-hoc.

## 9. Cross-repo install

A consumer installs **only the agents it wants**, each via a one-file shim in
`.github/workflows/` (never a nested subdirectory — GitHub ignores nested workflow files).
Example — enforcer + qa, no mechanic:

```yaml
# consumer-repo/.github/workflows/trigger-enforcer.yml
name: "Trigger: Enforcer"
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  enforce:
    uses: nicsuzor/academicOps/.github/workflows/agent-enforcer.yml@dev
    with:
      pr_number: ${{ github.event.pull_request.number }}
      ref:       ${{ github.event.pull_request.head.ref }}
      sha:       ${{ github.event.pull_request.head.sha }}
    secrets:
      AOPS_BOT_GH_TOKEN: ${{ secrets.AOPS_BOT_GH_TOKEN }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

Mechanical CI is consumer-owned (the **naming contract** below). Add or remove an agent by
adding or deleting a shim file — no wider rewrite.

**Mechanical-CI naming contract.** The framework declares names; consumers implement them
from whatever pipeline they like. academicOps itself **keeps check-run names**
(`Lint / Lint`, `Pytest / Pytest`) — they already exist and the ruleset gates on them, so
re-emitting them as commit statuses is pure churn for one repo. For cross-repo consumers with
heterogeneous stacks (Rust/Node/…), the portable form is a commit status per concern:

| Status name        | Required? | Semantic                                         |
| ------------------ | --------- | ------------------------------------------------ |
| `lint-status`      | required  | Style/format checks pass (ruff/eslint/clippy/…). |
| `typecheck-status` | required  | Static type checks pass (or `success` + "n/a").  |
| `test-status`      | required  | Test suite passes.                               |
| `build-status`     | optional  | Build/compile/dist check.                        |

"The name is the contract" — branch protection requires the name; the framework does not
require any particular action/runner. A consumer may satisfy the contract with either
check-run names or `-status` commit statuses.

## 10. Loop-skip protocol (normative) — **LIVE** (enforcer, qa)

For an agent `<name>` invoked by the orchestrator on PR HEAD SHA `H`:

1. Fetch the agent's own latest status on `H`:
   `GET /repos/{owner}/{repo}/commits/{H}/statuses`, filter `context == "<name>-status"`,
   sort `created_at` desc, take first.
2. Parse `target_sha` from that status's `target_url` (query param `?target_sha=<sha>`).
3. **If `target_sha == H`:** skip. Re-post `success` with the same `target_sha=H` and a
   "Skipped: SHA already reviewed" description. Exit 0. `committed=false`.
4. **Else:** review HEAD; fix what you can (`committed=true` if you pushed); post a terminal
   status with `target_url` ending `?target_sha=H`.

**Not in the contract:** author identity (the agent does not care _who_ pushed `H`, only
whether _this diff_ has been judged — conflating the two caused P2) and commit trailers
(advisory metadata for humans, never control flow).

This decouples "have we judged this SHA?" from "is the author a bot?" A benign
merge-from-base produces a new SHA, so the agent reviews it (a fast no-op verdict on the
real SHA); a re-trigger on the _same_ SHA short-circuits. **This is precisely why §3.5
holds:** a mechanic fix is a new SHA, so enforcer + qa re-verify it; only an identical-SHA
re-trigger skips.

## 11. Migration plan (phased)

Each phase is independently shippable and leaves the pipeline working.

- **Phase 1 — Enforcer. DONE / LIVE.** `agent-enforcer.yml` (`workflow_call`-only, SHA-skip,
  `enforcer-status`) + `.github/agents/enforcer.agent.md` + `trigger-enforcer.yml`;
  `enforcer-status` required.
- **Phase 2 — QA agent (marsha) to parity. DONE / LIVE.** `agent-qa.yml` +
  `.github/agents/qa.agent.md` + `trigger-qa.yml`; posts `qa-status`; required check.
- **Phase 3 — Triage orchestrator + convergence. DONE / LIVE.** `pr-pipeline.yml` reworked
  into the triage orchestrator: `lint → enforcer → qa` via `needs:` + `committed`-output
  short-circuit (§3.4), keeping the `gate`/`guard-no-dist`/`initialize` jobs.
- **Phase 4 — Environment gate + `admit-status` + graduation. DONE, then SUPERSEDED by
  Phase 7.** `pr-fix-loop` Environment created with required reviewer; the in-pipeline
  `admit` job in `pr-pipeline.yml` parked at the Environment and (on approval) set
  `admit-status` + armed auto-merge. Originally shipped as a separate dispatched
  `stage2-admission.yml`; that detached the approval prompt from the PR for a falsified
  safety reason and was retired in favour of the in-pipeline form. Ruleset:
  `merge-prep-status → admit-status`, added `qa-status`, approvals `2 → 0`, in one atomic
  change (verified live on ruleset `13762049`). **The Environment gate itself is now
  RETIRED (Phase 7) — admission is a PR review approval; see §3.2.**
- **Phase 5 — Stage-2 dev/mechanic. DONE / LIVE.** `agent-mechanic.yml` +
  `.github/agents/mechanic.agent.md` are the admitted-loop dev agent (development to clear
  red + conflict resolution only when `CONFLICTING`); §8's F1–F10 are inherited; §3.5
  (re-verify) and §3.6 (bound + exhaustion) are implemented in the workflow. `merge-prep-status`
  → `mechanic-status` (non-required, informational). The v1 fast-path / bot-approval / armed
  auto-merge steps are **deleted** (those duties belong to the human Environment gate, not the
  fixer). `merge-prep-cron.yml` (per-PR no-op dispatch) and the vestigial `merge-prep-status`
  carry-forward in `pr-pipeline.yml`'s `initialize` are **deleted**. The hardcoded `origin/main`
  base is fixed (F1 — the mechanic resolves the PR's actual `base.ref` via the API, never assumes).
- **Phase 6 — Alignment (pauli) advisory. PARTIALLY LIVE.** In-repo `alignment-status:
  pending` marker LIVE (orchestrator `alignment-queue` job — §6.1). The `alignment:queued`
  issue-queue surface is **DISABLED** (removed in aops-956c1842): it was write-only spam
  while its consumer stayed unbuilt. Host-side cron + polecat-pauli dispatcher still
  SPEC-ONLY — drains the queue, reconciles against the commit status, dispatches pauli,
  closes stale issues (§6.2). The issue-upsert step is restored only when that drainer
  ships (follow-up `aops-8f42f33d`), never before. `alignment-status` must remain advisory
  (NOT in the branch-protection ruleset — §6, §7). Cleanup of any remaining dead v1
  references lands here.
- **Phase 8 — Pre-admission mechanical responder. DONE / LIVE.** `agent-pre-admission-responder.yml` + `.github/agents/pre-admission-responder.agent.md` + `scripts/ci/check-mechanical-red.sh` are the pre-admission mechanical fix agent. The orchestrator (`pr-pipeline.yml`) adds `check-mechred → pre-admission-responder` to Stage 1, appended after `qa` and guarded by `check-mechanical-red.sh` (no-op-on-green + Stage-2 guard + ceiling). `check-admit` is updated to also `needs: [pre-admission-responder]` so the Stage-2 mechanic never races the pre-admission responder. `MAX_RESPONDER_RUNS=3` (tighter than the mechanic's 5); `timeout-minutes: 30` (cheaper than the mechanic's 55). Judgment calls and recusal flags are NEVER auto-applied. Design rationale: [[mem-b282d863]].
- **Phase 7 — Admission via PR review approval; retire the Environment gate. DONE / LIVE.**
  The `pr-fix-loop` GitHub Environment gate + the in-pipeline `admit` job are **retired**
  (the Environment object can be deleted in repo Settings; no workflow references it).
  Admission is now a maintainer's PR **review approval**, handled by the event-driven
  `admit-on-review.yml` (`on: pull_request_review`): authorise (write-class /
  allowlist — `scripts/ci/admit-on-review.sh`, `tests/test_admit_on_review.py`) → set
  `admit-status` → arm auto-merge → dispatch the mechanic's first pass on the admitted SHA.
  Motivation (§3.2): the Environment approval UI was undiscoverable, and approving it
  emitted no event so the mechanic dispatch stranded (worked example PR #1858). The
  `initialize` carry-forward (§5) and the `check-admit → mechanic` passes 2…N are
  unchanged; the `already_admitted` output (only the parked `admit` job consumed it) is
  removed. `required_approving_review_count` stays `0`.

## 12. Open questions

1. **Stage-2 loop driver (SPEC-ONLY).** The fix loop re-triggers via the agents' pushes
   through the orchestrator (a new `synchronize` per pass). Confirm on a scratch PR that an
   admitted run re-enters cleanly and that `admit-status` carry-forward (§5) keeps the gate
   satisfied across agent commits without re-parking at the environment.
2. **`MAX_MECHANIC_RUNS` calibration.** 5 is provisional (§3.6); calibrate against actual
   `Mechanic-By:` counts over the first ~20 admitted PRs.
3. **`target_sha` channel.** The `target_url` query-param hack (§10) is ugly but
   parsimonious; revisit only if a downstream consumer needs to query target-sha cleanly.
4. **Advisory-finding tracking (open, owned by [[release-publish-pipeline]] §8.3).** Fatal
   findings are tracked (F6); non-fatal `COMMENT`-level reviews and "Deferred" triage rows
   have no machine mechanism ensuring closure. Undecided whether to require a PKB task id on
   every non-"Fixed" triage row. Recorded as a candidate, not adopted.

## 13. Cross-references

- [[release-publish-pipeline]] — the **release/publish** half (merge → tag → artifacts +
  version-sync). It owns topology, release-please, `build-extension.yml`, Docker, and the
  uv.lock discipline; it cross-references **this** spec for all merge-gate detail and must
  not duplicate it.
- `.github/rulesets/pr-review-and-merge.yml` — the live ruleset (ID `13762049`).
- `.github/workflows/{pr-pipeline,agent-enforcer,trigger-enforcer,agent-qa,trigger-qa,agent-mechanic}.yml`
  - `.github/agents/{enforcer,qa,mechanic}.agent.md` — the LIVE two-stage scaffolding.
    (`pr-pipeline.yml` carries the in-pipeline `admit` job; the standalone
    `stage2-admission.yml` was retired — see §3.2.)
- `.github/workflows/{agent-merge-prep,merge-prep-cron}.yml` + `.github/agents/merge-prep.agent.md`
  — the v1 transitional fixer (RETIRED at Phase 5; behaviour inherited per §8).
- `specs/ENFORCEMENT-MAP.md` — "PR-pipeline agents" rows (§4.3).
- PR #1037 / issue #1039 — the P2 worked example (enforcer skip + approval substitution).
- PR #1614 — the P5 worked example (no-op merge-prep on a docs PR).
- `aops-638a351e` — loose-trigger cache-waste evidence (P1).
- PR #974 — the surface-only-delta worked example (F5).
- PR 582 post-mortem — the cascade-loop incident behind the runaway ceiling (§3.6, F8).

### Consolidation record (2026-06-09)

This file is the single SSoT, consolidated from:

- **`pr-pipeline.md` (v1, the merge-prep model) — KILLED.** Its file content is replaced by
  this consolidated spec. Its still-live behaviour was extracted into §8 (F1–F10) and §5
  (the `initialize` carry-forward) so nothing live was lost on deletion.
- **`pr-pipeline-v2.md` (the two-stage model) — PROMOTED.** This spec _is_ v2, completed and
  promoted to the single SSoT; the `pr-pipeline-v2.md` file is deleted and its permalink is
  retained here as an alias.
- **PKB node `pr-pipeline-d5c0b611` ("PR Pipeline v2") — ARCHIVED.** Was already a relocated
  stub; archived so it cannot be mistaken for a live spec.
- **PKB node `pr-3a3dbf43` ("merge-prep behavior and late review handling") — ARCHIVED.** Its
  unique still-true content (conflict-vs-review-decision distinction; scope-violation
  reviews are not mechanically resolvable; graduation is workflow-owned) was folded into §8
  (F4, F6) and §4.7.

Two design decisions new in this consolidation (both Nic, 2026-06-09; both **SPEC-ONLY**,
governing the Phase-5 mechanic): the **Stage-2 re-verify contract** (§3.5) and the
**Stage-2 bounded loop + exhaustion escalation** (§3.6).
