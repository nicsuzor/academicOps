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

| Capability                                                                                                                                                                                | State                   | Evidence (2026-06-09)                                                                      |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------ |
| Stage-1 triage orchestrator (`pr-pipeline.yml`): cost-order `lint → enforcer → qa`, `committed`-output short-circuit, read-only `typecheck`/`pytest`, `dispatch-admission` on convergence | **LIVE**                | `.github/workflows/pr-pipeline.yml`                                                        |
| Enforcer (rbg) per-agent contract: `workflow_call`-only agent file, `enforcer-status`, per-SHA loop-skip via `?target_sha=`                                                               | **LIVE**                | `agent-enforcer.yml` + `trigger-enforcer.yml`                                              |
| QA (marsha) per-agent contract: `workflow_call`-only, `qa-status`, per-SHA loop-skip, never commits                                                                                       | **LIVE**                | `agent-qa.yml` + `trigger-qa.yml` + `.github/agents/qa.agent.md`                           |
| The human gate: `pr-fix-loop` GitHub Environment **exists** with required reviewer `nicsuzor`; `stage2-admission.yml` parks, sets `admit-status`, arms auto-merge                         | **LIVE**                | `gh api .../environments/pr-fix-loop` + `stage2-admission.yml`                             |
| Branch-protection ruleset: required = `Lint / Lint`, `Pytest / Pytest`, `enforcer-status`, `qa-status`, `admit-status`; `required_approving_review_count: 0`; `enforcement: active`       | **LIVE**                | live ruleset ID `13762049` (API-verified, matches the in-repo file)                        |
| `admit-status` carry-forward across agent commits / reset on human push; `merge-prep-status` initialize carry-forward                                                                     | **LIVE**                | `pr-pipeline.yml` `initialize` job                                                         |
| **Stage-2 dev/mechanic agent** appended to the cost order (real development + conflict resolution inside an admitted run)                                                                 | **SPEC-ONLY**           | `agent-mechanic.yml` / `mechanic.agent.md` **absent**                                      |
| `mechanic-status` informational status                                                                                                                                                    | **SPEC-ONLY**           | not posted by any workflow                                                                 |
| **Stage-2 re-verify contract** (enforcer + qa re-run per mechanic SHA; §3.5)                                                                                                              | **SPEC-ONLY**           | governs the mechanic when Phase 5 ships                                                    |
| **Stage-2 bounded loop + exhaustion escalation** (§3.6)                                                                                                                                   | **SPEC-ONLY**           | carries v1's `MAX_MERGE_PREP_RUNS=5` precedent forward                                     |
| Alignment (pauli) queue surface — orchestrator posts `alignment-status: pending` and files an `alignment:queued` issue per PR                                                             | **LIVE**                | `pr-pipeline.yml` `alignment-queue` job                                                    |
| Alignment host-side cron + polecat-pauli dispatcher (drains the queue, posts the terminal `alignment-status`)                                                                             | **SPEC-ONLY**           | no host cron / dispatcher wired; live stand-in is manual `/strategic-review --critic` (§6) |
| **Live fixer today** = v1 `agent-merge-prep.yml` + `merge-prep-cron.yml` (cron `*/30` + `workflow_run`), still posts (now non-required) `merge-prep-status`                               | **LIVE (transitional)** | both files present; retired at Phase 5 (§11)                                               |

The single most important honest caveat: **the "Stage 2 fix loop" as a dev/mechanic agent
inside an admitted orchestrator run is not built.** Today, the fixing/conflict-resolution
work is still performed by the v1 `merge-prep` agent on a cron, in parallel with the new
two-stage scaffolding. The gate, the convergence orchestrator, the two reviewer agents,
and the ruleset are all LIVE; the post-admission _developer_ is not. Nic's two new design
decisions (§3.5, §3.6) are therefore **SPEC-ONLY contracts the mechanic must implement at
Phase 5** — they are written here so Phase 5 can be built without re-deriving them.

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
  `admit-status` is set by an Environment-gated job (no checkout, no LLM) — this is what
  removes P5's no-op merge-prep run.

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
│  THE GATE — `pr-fix-loop` GitHub Environment (required reviewer = you) │   LIVE
│  Stage-2 run PARKS here. You read the statuses + reviews + pauli's     │
│  verdict and Approve (admit) or Reject. "All green or I click" → click.│
│  Admission = the single human decision: "good idea — make it mergeable"│
└───────────────────────────────────────────────────────────────────────┘
                                 │ approved
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — FIX LOOP  (post-admission, the "new environment")           │   SPEC-ONLY*
│  same orchestrator + short-circuit + convergence, now WITH:           │
│     … → dev/mechanic agent (real development) + conflict resolution    │
│  enforcer + qa RE-VERIFY each mechanic SHA (§3.5) · bounded (§3.6)     │
│  required-green to merge: cheap checks + enforcer + qa + no conflicts  │
│  CONVERGED + all-green → MERGE   |   loop bound exhausted → escalate    │
│  admission armed `gh pr merge --auto`; merge fires when checks green   │
└───────────────────────────────────────────────────────────────────────┘
   * the gate + armed auto-merge are LIVE; the dev/mechanic agent is not yet built.
     Today the post-admission fixer is still the v1 merge-prep agent on cron (§8).
```

Key properties:

- **No triage box.** Branch protection AND-gates the named statuses mechanically; there is
  no LLM whose job is "decide whether the verdicts add up to mergeable." **LIVE.**
- **No mechanic-on-a-timer (target).** The dev/mechanic agent runs only _inside_ an
  admitted fix loop, and conflict resolution only when the PR is `CONFLICTING`; no per-PR
  no-op run. **SPEC-ONLY** — until Phase 5, the cron-driven merge-prep still runs (§8, §11).
- **Alignment is an input to the human gate, not a required check.** A host outage
  degrades advice, never deadlocks a merge. **LIVE for the "not required" part; the
  host-side dispatch is SPEC-ONLY** (§6).

## 3. The two stages and the gate

### 3.1 Stage 1 — Triage (every push) — **LIVE**

A single **triage orchestrator** (`pr-pipeline.yml`) is the workflow triggered by
`pull_request` (`opened`, `synchronize`, `ready_for_review`, `reopened`). It runs the
committing agents in cost order under the **ordered short-circuit** rule (§3.4). The
dev/mechanic agent does **not** run in Stage 1 — triage is cheap by construction.

Each agent **fixes what it can and leaves its status red for what it can't.** There is no
clean "autofixer vs reviewer" split: `lint` autofixes formatting but goes red on a lint
error needing a real code change; `enforcer` autofixes some violations but goes red on the
ones needing judgement or development. **A red status is a handoff** — the next agent down
the chain (ultimately the mechanic in Stage 2) is who clears it. (Today, qa never commits —
it verifies only; `committed` is always `false` — so the only Stage-1 committers are lint
and enforcer.)

`pauli`/`alignment` runs as an out-of-chain advisory surface, not inside the lint→enforcer→qa
chain. The orchestrator's `alignment-queue` job is **LIVE** (it posts `alignment-status:
pending` on HEAD and files an `alignment:queued` issue per PR); the host-side cron +
polecat-pauli dispatcher that drains the queue is **SPEC-ONLY**, so until it ships the live
stand-in is the manual `/strategic-review --critic` skill the maintainer runs by hand before
admitting (§6).

Stage 1 ends when the pass converges (§3.4). The orchestrator's `dispatch-admission` job
then dispatches a Stage-2 admission run that parks at the gate (§3.2).

### 3.2 The gate — `pr-fix-loop` GitHub Environment — **LIVE**

Admission to the development loop is a **GitHub Environment with a required reviewer**
(`pr-fix-loop`, required reviewer `nicsuzor` — verified to exist on 2026-06-09), reusing
the `production`-style environment pattern already used for release-please gating
(`pr-pipeline.yml` `gate` job).

On Stage-1 convergence, `dispatch-admission` dispatches `stage2-admission.yml` as a
**separate run** whose only job targets the `pr-fix-loop` environment and **pauses**. The
maintainer reads the triage statuses, the agents' reviews, and pauli's alignment verdict
(if they ran `/strategic-review` by hand), then **Approves (admit) or Rejects**.
"If it's all green or I click the button" — approving the pending deployment _is_ the
button. This is the single human decision in the pipeline: _this is a good idea; make it
mergeable._

On approval, `stage2-admission.yml` (with the bot PAT) does two things: (a) sets the
required `admit-status` to `success` on HEAD, and (b) arms
`gh pr merge --auto --squash --delete-branch`.

> An Environment-gated job pauses the whole run awaiting approval. Admission is therefore a
> **separately dispatched run** that parks at the gate — never a job inside the Stage-1 run
> (which would leave Stage 1 hanging). `pr-pipeline.yml`'s `dispatch-admission` is
> idempotent: it dispatches only when `admit-status` is not already `success`, so
> carry-forward (§5) keeps the gate from re-parking on every later convergence.
>
> **Enforcement caveat (verified):** the `pr-fix-loop` Environment exists _with_ a required
> reviewer, so the run genuinely parks. If that Environment were ever deleted or stripped of
> its reviewer, `environment: pr-fix-loop` would resolve to an unprotected environment and
> the admit job would run **without pausing** — silently setting `admit-status` and arming
> auto-merge with no human in the loop. The gate's integrity depends on that Environment's
> protection rule, which lives in repo Settings (out of any worktree).

### 3.3 Stage 2 — Fix loop (post-admission) — gate LIVE, dev/mechanic **SPEC-ONLY**

The admitted run is intended to use the **same orchestrator, ordered short-circuit, and
convergence** as Stage 1, with two additions:

- the **dev/mechanic agent** is appended last in the cost order — it does real development
  to clear the red that the autofixers couldn't; and
- **conflict resolution** runs when the PR is `CONFLICTING` (`git merge origin/<base>`).

**SPEC-ONLY status:** `agent-mechanic.yml` / `mechanic.agent.md` do not exist. Until
Phase 5 ships, the post-admission fixing is performed by the LIVE v1 `merge-prep` agent
(`agent-merge-prep.yml` dispatched by `merge-prep-cron.yml`), whose folded behaviour is
documented in §8. The two new contracts below (§3.5 re-verify, §3.6 bound) define how the
mechanic must behave once built.

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

### 3.5 Stage-2 re-verification contract — enforcer + qa run _inside_ the fix loop (Nic, 2026-06-09) — **SPEC-ONLY**

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

### 3.6 Stage-2 bounded loop + exhaustion escalation (Nic, 2026-06-09 — NEW) — **SPEC-ONLY**

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
  post-mortem).
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
   merge on the stale "good idea" decision, and the next Stage-1 convergence re-parks it at
   `pr-fix-loop` for the maintainer to re-judge (re-admit after intervening, or reject). It
   is a third admit-status transition alongside §5's "carry across agent commits / reset on
   human push".
4. **The PR is left un-merged.** Because the required reviewer status(es) are red **and**
   `admit-status` is now pending, the armed auto-merge cannot fire. No silent merge.
5. **The maintainer is pinged** (`gh pr edit --add-reviewer nicsuzor`) so the escalation
   is visible, not buried.
6. **The loop stops auto-dispatching the mechanic.** Resumption requires an explicit human
   action: either (a) a **new human push** (which independently resets `admit-status` to
   pending per §5 and re-enters the gate), or (b) a **manual `workflow_dispatch`**
   re-invocation of the mechanic with a force flag. This mirrors v1's "manual retry resets
   the halt" semantics.

> Net: on exhaustion the PR sits **admitted-no-more, reviewer-red, un-merged, with a named
> escalation review and the maintainer requested.** A reader can implement this without
> guessing the cap (`MAX_MECHANIC_RUNS = 5`, counting `Mechanic-By:` commits) or the
> on-exhaustion state (mechanic-status=failure, admit-status=pending, no merge, escalation
> review posted, maintainer pinged, auto-dispatch stopped).

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

| Agent                           | Status name        | Required gate?        | State         |
| ------------------------------- | ------------------ | --------------------- | ------------- |
| Enforcer (rbg)                  | `enforcer-status`  | yes                   | **LIVE**      |
| QA (marsha)                     | `qa-status`        | yes                   | **LIVE**      |
| Mechanic / dev (was merge-prep) | `mechanic-status`  | no (work, not a gate) | **SPEC-ONLY** |
| Alignment (pauli)               | `alignment-status` | **no** (advisory, §6) | **SPEC-ONLY** |

> **Naming reality check.** The agent name is settled as **`mechanic`** (status
> `mechanic-status`) — a locked decision. But the **live file is still
> `agent-merge-prep.yml`** and the **live status it posts is still `merge-prep-status`**
> (now a _non-required_ status — it was removed from the ruleset at Phase 4, §7). The rename
> `agent-merge-prep.yml → agent-mechanic.yml` and `merge-prep-status → mechanic-status` is
> **Phase 5, pending** (§11). Do not read "mechanic" as a live file name.
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

### 4.3 One row in `specs/ENFORCEMENT-MAP.md`

Every agent declares which axioms / rules / lifecycle points it covers, under the
"PR-pipeline agents" section. A PR adding an agent that omits its enforcement-map row fails
enforcer review.

### 4.4 One `.github/agents/<name>.agent.md` prompt file

The prompt file is the agent's behaviour contract. It sources the canonical personality
(e.g. `aops-core/agents/rbg.md`) and adds PR-context wrapping (read `.agents/CORE.md`, run
`gh pr view`, format the review). Orchestration (the workflow) and behaviour (the prompt)
version independently.

### 4.5 Versioned ref per agent

Each agent ships under its own ref (`enforcer-v1`, `qa-v1`, `mechanic-v1`, `alignment-v1`).
Consumers pin to refs, never `@main`. Breaking changes ship as a new tag with a migration
note and a deprecation window.

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

Graduation is deliberately cheap: no bot approval, no agent, no checkout.

- The Environment-gated admission job (`stage2-admission.yml`, §3.2) does two things on
  approval: (1) sets the required **`admit-status`** to `success` on HEAD, and (2) arms
  `gh pr merge --auto --squash --delete-branch`.
- The merge fires the moment **all required checks are green and the PR is mergeable** —
  immediately for an already-green PR, or after the Stage-2 loop converges green.
- **`admit-status` replaces v1's `merge-prep-status`** as the required gate. Because it is
  set by a human-approval-driven job rather than a merge-prep run, the no-op runner on every
  green PR (P5) is gone.
- **Carry-forward (LIVE, in `pr-pipeline.yml`'s `initialize` job).** Once admitted at SHA
  _X_, `admit-status` carries forward across _agent-authored_ fix commits during the loop
  (the admission decision stands). The live rule: on `synchronize`, if the previous HEAD had
  `admit-status: success` and the new HEAD commit was authored/committed by a bot (account
  type `Bot` or a `[bot]` login suffix), carry `success` forward; **a new human push resets
  admission to `pending`** (a substantive human change must be re-judged at the gate). A
  **third reset trigger** is added by §3.6: **loop exhaustion resets `admit-status` to
  pending.** (The `initialize` job also still manages a `merge-prep-status` pending/
  carry-forward transition; that status is now non-required and is vestigial pending the
  Phase 5 cleanup — see §8/§11.)
- **`required_approving_review_count: 2 → 0` (LIVE).** v1 needed two approvals because
  merge-prep counted as approval #1. This pipeline has no bot approval — the Environment
  gate plus `admit-status` is the human decision point. There is no review-approval to count.

> Sequencing (already done): `admit-status` was added to required checks in the _same_ change
> that dropped approvals to 0 — otherwise there would be a window where green checks alone
> permit a manual merge that bypasses the gate. This is **LIVE** in ruleset `13762049`.

## 6. Alignment (pauli) — advisory, host-side, not a gate — **PARTIALLY LIVE** (queue surface LIVE; host dispatch SPEC-ONLY)

Pauli's value is PKB context, and GHA cannot reach the Tailnet-internal PKB MCP (P3). The
**target**: pauli runs **host-side** (where the PKB lives), dispatched by a light host cron,
and posts a **review verdict** that informs the human gate (§3.2). It is **not** a required
status check.

**LIVE today:** the orchestrator's `alignment-queue` job (`pr-pipeline.yml`) posts
`alignment-status: pending` on HEAD and files (or refreshes) a single `alignment:queued`
GitHub issue per PR. This is plumbing: the queue surface exists and is being kept current on
every push. The **host-side cron + polecat-pauli dispatcher that drains the queue is not yet
wired** — until it ships, the queue surface is the to-do list, not an actual alignment read.
The live way for the maintainer to get an alignment read remains the **manual
`/strategic-review --critic` skill** (`aops-core/skills/strategic-review/SKILL.md`), which
they invoke by hand before admitting a PR. So alignment is **advisory input to the human
admit gate, produced manually**, until the host-side dispatch ships.

This is the deliberate simplification over an earlier draft that specced alignment as a
required, fail-closed gate with a watchdog. In the two-stage model the **human Environment
approval is the alignment decision point** — the maintainer reads pauli's verdict (or runs
it themselves) and decides. Consequences: no host-availability deadlock (if pauli has not
run, the maintainer admits on their own judgement); no watchdog, no `pending → failure`
flip, no required-status machinery.

### 6.1 Queue surface — **LIVE** (orchestrator `alignment-queue` job)

The triage orchestrator's `alignment-queue` job runs in parallel with the lint→enforcer→qa
chain (it never delays the merge-gate agents) and does exactly two things on every same-repo
push:

1. **Set `alignment-status: pending`** on the HEAD SHA via the GitHub statuses API. Skipped
   if `alignment-status` is already terminal (`success`/`failure`/`error`) on this SHA — that
   means pauli has already reviewed it and we must not overwrite the verdict.
2. **Upsert one `alignment:queued` issue per PR.** Deterministic title:
   `alignment:queued PR #<num>` (one PR ↔ one issue). The body is a stable
   `<!-- aops:alignment-queue -->`-fenced block carrying `PR`, `Repository`, `Head ref`,
   `Head SHA`, and `Queued` timestamp — everything the host dispatcher needs to dispatch
   pauli without re-querying the PR API per entry. On a new push the body is refreshed to
   the new HEAD SHA; if the issue was closed by the dispatcher last time, it is reopened (a
   new SHA = a new alignment review is needed).

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
   against PKB design intent and posts a PR review verdict (the maintainer reads this at the
   Env gate, §3.2) plus a terminal `alignment-status` (informational only — see §6.3).
4. **Closes the issue** when pauli's terminal status is posted on the current HEAD.

The dispatcher script lives outside this repo's worktree by design — PKB MCP reachability is
its precondition, and that lives host-side.

### 6.3 What pauli posts — **SPEC-ONLY**

Pauli posts (a) a PR review verdict the maintainer reads at the human Env gate (§3.2), and
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
      # Human gate (Environment approval, §5) — NOT an agent
      - context: "admit-status"
      # NOTE: alignment-status is advisory (§6) and is NOT required.
      # NOTE: merge-prep-status is REMOVED (replaced by admit-status).

- type: pull_request
  parameters:
    required_approving_review_count: 0   # Env gate + admit-status is the human gate
    dismiss_stale_reviews_on_push: false
```

**No transitive gating.** Each agent owns its status directly; there is no single
`merge-prep-status` that an agent could forget to wait for or silently substitute.

> `mechanic-status` is **not** in this list and must never be added — the mechanic does work,
> not a verdict (§4.2). The reviewer statuses (`enforcer-status`, `qa-status`) are what
> ensure the mechanic's output is verified before merge (§3.5).

## 8. Live merge-prep behaviour folded in (transitional) — **LIVE** until Phase 5

Until the mechanic (Phase 5) is built, the post-admission fixing — and, today, most fixing
generally — is done by the v1 `merge-prep` agent: `agent-merge-prep.yml` (the worker) +
`merge-prep-cron.yml` (the dispatcher: `*/30` cron + `workflow_run` on "Agent: Merge Prep"
completions) + `.github/agents/merge-prep.agent.md` (the behaviour). This section preserves
the **still-live behaviour** so it is not lost on the v1 spec's deletion; **every item here
becomes the mechanic's responsibility at Phase 5** (and the mechanic adds the §3.5 re-verify
discipline and the §3.6 bound on top).

Folded live behaviour (each is a contract the mechanic inherits):

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
    uses: nicsuzor/academicOps/.github/workflows/agent-enforcer.yml@enforcer-v1
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
- **Phase 4 — Environment gate + `admit-status` + graduation. DONE / LIVE.** `pr-fix-loop`
  Environment created with required reviewer; `stage2-admission.yml` parks and (on approval)
  sets `admit-status` + arms auto-merge; `dispatch-admission` job in `pr-pipeline.yml`.
  Ruleset: `merge-prep-status → admit-status`, added `qa-status`, approvals `2 → 0`, in one
  atomic change (verified live on ruleset `13762049`).
- **Phase 5 — Stage-2 dev/mechanic. PENDING / SPEC-ONLY.** Repurpose `agent-merge-prep.yml`
  into the admitted-loop dev agent `agent-mechanic.yml` (development to clear red +
  conflict resolution only when `CONFLICTING`); fold in §8's F1–F10; implement §3.5
  (re-verify) and §3.6 (bound + exhaustion). Rename `merge-prep-status → mechanic-status`
  (non-required). Delete the v1 fast-path/graduation steps. Retire `merge-prep-cron.yml`'s
  per-PR dispatch and the vestigial `merge-prep-status` writes in `initialize`. Fix the
  hardcoded `origin/main` base (F1 / release-publish §9 C5).
- **Phase 6 — Alignment (pauli) advisory. PARTIALLY LIVE.** In-repo queue surface LIVE
  (orchestrator `alignment-queue` job: posts `alignment-status: pending`, files
  `alignment:queued` issue with deterministic title `alignment:queued PR #<num>` — §6.1).
  Host-side cron + polecat-pauli dispatcher still SPEC-ONLY — drains the queue, reconciles
  against the commit status, dispatches pauli, closes stale issues (§6.2). `alignment-status`
  must remain advisory (NOT in the branch-protection ruleset — §6, §7). Cleanup of any
  remaining dead v1 references lands here.

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
- `.github/workflows/{pr-pipeline,stage2-admission,agent-enforcer,trigger-enforcer,agent-qa,trigger-qa}.yml`
  — the LIVE two-stage scaffolding.
- `.github/workflows/{agent-merge-prep,merge-prep-cron}.yml` + `.github/agents/merge-prep.agent.md`
  — the LIVE transitional fixer (retired at Phase 5; behaviour folded into §8).
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
