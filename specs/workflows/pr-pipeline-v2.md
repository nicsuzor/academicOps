---
id: pr-pipeline-v2
title: "PR Pipeline v2"
type: spec
created: 2026-05-15T02:07:45.675923357+00:00
modified: 2026-06-06T00:00:00.000000000+00:00
alias:
  - "pr-pipeline-v2-pr-pipeline-v2"
  - "pr-pipeline-v2"
permalink: pr-pipeline-v2
status: operative-phased
tags:
  - workflow
  - pr-pipeline
  - v2
supersedes: "pr-pipeline.md"
---

# PR Pipeline v2 — Two-Stage, Environment-Gated, Convergent

> Status: **operative (phased rollout)**. v2 Phase 1 has shipped — the enforcer
> (`agent-enforcer.yml` + `trigger-enforcer.yml`) is already a `workflow_call`-only
> reusable that posts `enforcer-status` with SHA-based loop-skip. This document is
> the contract for the remaining phases. v1 ([[pr-pipeline]]) stays the operative
> _description of merge-prep_ only until Phase 4 (mechanic) ships; everything else
> here is the live target.
>
> Epic: `aops-10d5b344` (Modular GHA agent pipeline v2)

## 1. Why v2 — and why it can now be simpler

v1 collapsed three concerns into two workflows: mechanical CI, axiom enforcement,
and a monolithic `merge-prep` that read everyone's reviews, fixed what it could,
approved, set the _required_ `merge-prep-status`, and armed auto-merge.

The pathologies this produced:

| #  | Pathology                                                                                                                           | Evidence                                   |
| -- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| P1 | Loose triggers waste cache (`pull_request` + `workflow_run` + … fan-out)                                                            | `aops-638a351e` (~130M cache_r/wk)         |
| P2 | Enforcer self-skipped on agent-authored HEAD → merge-prep substituted its own approval for an absent verdict → PR landed unreviewed | PR #1037 → issue #1039                     |
| P3 | Pauli (alignment) cannot run from GHA (no PKB MCP reachability) → alignment verdict missing from the gate                           | issue #1034                                |
| P4 | Cross-repo install is "copy three workflow files", not "pick the agents you want"                                                   | `examples/cross-repo-shim/`                |
| P5 | **merge-prep runs as a no-op on every green PR** — a full runner + two full-history checkouts to make ~4 API calls on its fast-path | PR #1614 (docs-only) is the worked example |

**The v1 improvements change the economics.** Since v2 was first drafted, v1 gained
an `initialize` job that holds `merge-prep-status` pending until triage (with
carry-forward on `synchronize`), a working fast-path, and the enforcer rewrite. That
means v2 no longer needs the heavy "triage agent that decides mergeability" — most of
that work is now either mechanical or belongs to the named agents directly. v2 can be
both **simpler** (no triage LLM, no per-PR mechanic timer) and **stronger** (a real
human "good idea" gate, convergence that never re-runs heavy agents on cheap fixes).

v2 reframes around three structural decisions:

- **One LLM agent ≡ one `workflow_call`-only reusable ≡ one named status check.** No
  anonymous Claude runs. No agent self-triggers (this is the anti-cascade substrate;
  see §4.1, §10). The enforcer already obeys this.
- **Two stages with one human gate between them.** Cheap triage runs on every commit;
  the expensive development loop runs _only after a human admits the PR_ as a good idea
  (§3). We never spend development effort on a bad idea.
- **The merge gate is a cheap human-approval status, not an agent.** The required
  `admit-status` is set by an Environment-gated job (no checkout, no LLM) — this is
  what removes P5's no-op merge-prep run.

## 2. Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — TRIAGE  (GHA, every push, cheap, one convergence, no dev)   │
│                                                                       │
│  orchestrator runs committing agents in COST ORDER, short-circuit:    │
│     lint (autofix) → enforcer/rbg → qa/marsha                         │
│  read-only checks (typecheck, pytest) post status, never commit       │
│  pauli/alignment runs ONCE host-side → advisory verdict (not a gate)  │
│                                                                       │
│  each agent: fix what it can (commit) · red status for what it can't  │
│  a pass stops at the FIRST agent that commits; its push = next pass    │
│  CONVERGED = a full pass with zero commits → statuses fresh on HEAD    │
└───────────────────────────────────────────────────────────────────────┘
                                 │ on convergence, dispatch a Stage-2 run
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  THE GATE — `pr-fix-loop` GitHub Environment (required reviewer = you) │
│  Stage-2 run PARKS here. You read the statuses + reviews + pauli's     │
│  verdict and Approve (admit) or Reject. "All green or I click" → click.│
│  Admission = the single human decision: "good idea — make it mergeable"│
└───────────────────────────────────────────────────────────────────────┘
                                 │ approved
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — FIX LOOP  (GHA, post-admission, the "new environment")      │
│  same orchestrator + short-circuit + convergence, now WITH:           │
│     … → dev/mechanic agent (real development) + conflict resolution    │
│  required-green to merge: cheap checks + enforcer + qa + no conflicts  │
│  CONVERGED + all-green → MERGE   |   CONVERGED + still-red → reject     │
│  admission armed `gh pr merge --auto`; merge fires when checks green   │
└───────────────────────────────────────────────────────────────────────┘
```

Key properties:

- **No triage box.** Branch protection AND-gates the named statuses mechanically;
  there is no LLM whose job is "decide whether the verdicts add up to mergeable."
- **No mechanic-on-a-timer.** The dev/mechanic agent runs only _inside_ an admitted
  fix loop, and conflict resolution only when the PR is `CONFLICTING`. There is no
  per-PR no-op run.
- **Alignment is an input to the human gate, not a required check.** A host outage
  degrades advice, never deadlocks a merge.

## 3. The two stages and the gate

### 3.1 Stage 1 — Triage (every push)

A single **triage orchestrator** (the role today's `pr-pipeline.yml` plays) is the
only workflow triggered by `pull_request` (`opened`, `synchronize`,
`ready_for_review`, `reopened`). It runs the committing agents in cost order under the
**ordered short-circuit** rule (§3.4). The dev/mechanic agent does **not** run in
Stage 1 — triage is cheap by construction.

Each agent **fixes what it can and leaves its status red for what it can't.** There is
no clean "autofixer vs reviewer" split: `lint` autofixes formatting but goes red on a
lint error needing a real code change; `enforcer` autofixes some violations but goes
red on the ones needing judgement or development. **A red status is a handoff** — the
next agent down the chain (ultimately the dev agent in Stage 2) is who clears it.

`pauli`/`alignment` runs once, host-side (§6), and posts an advisory review verdict.

Stage 1 ends when the pass converges (§3.4). The orchestrator then dispatches a
Stage-2 run that parks at the gate (§3.2).

### 3.2 The gate — `pr-fix-loop` GitHub Environment

Admission to the development loop is a **GitHub Environment with a required reviewer**
(the maintainer), reusing the `production`-style environment pattern already used for
release-please gating (`pr-pipeline.yml` `gate` job).

On Stage-1 convergence, a Stage-2 run is dispatched whose first job targets the
`pr-fix-loop` environment and **pauses**. The maintainer reads the triage statuses,
the agents' reviews, and pauli's alignment verdict, then **Approves (admit) or
Rejects**. "If it's all green or I click the button" — approving the pending
deployment _is_ the button. This is the single human decision in the pipeline: _this
is a good idea; make it mergeable._

> An Environment-gated job pauses the whole run awaiting approval. Stage 2 is
> therefore a **separately dispatched run** that parks at the gate — never a job
> inside the Stage-1 run (which would leave Stage 1 hanging).

### 3.3 Stage 2 — Fix loop (post-admission)

The admitted run uses the **same orchestrator, ordered short-circuit, and
convergence** as Stage 1, with two additions:

- the **dev/mechanic agent** is appended last in the cost order — it does real
  development to clear the red that the autofixers couldn't; and
- **conflict resolution** runs when the PR is `CONFLICTING` (`git merge origin/<base>`).

Required-green to merge is **cheap checks + `enforcer` + `qa` + no conflicts** —
**not** alignment. The loop iterates to convergence:

- **converged + all-green → merge** (auto-merge was armed at admission, §5).
- **converged + still-red → the dev agent could not fix it** (or the approach is
  wrong) → post a rejection/escalation review and stop.

### 3.4 Convergence and the ordered short-circuit (normative)

This is the mechanism that makes the loop cheap. The cascade failure ("rbg re-runs on
every lint fix") is an artifact of giving each agent its own push trigger. v2 forbids
that (§4.1) and runs agents only from the orchestrator:

1. Within a pass, committing agents run in **cost order**: `lint → enforcer → qa
   [→ dev, Stage 2 only]`. Each agent job exposes a boolean output `committed`.
2. A pass **stops at the first agent that commits**: every downstream agent job is
   guarded `if: <no upstream agent in this pass committed>`. The single push from that
   agent starts the next pass from the cheapest agent.
3. **Convergence** = a pass in which the chain runs all the way through and **no agent
   commits**. At that point every agent has posted an authoritative status on the
   _current_ HEAD SHA.
4. Read-only checks (typecheck, pytest) never commit, so they never end a pass; they
   only contribute statuses.

Because autofixes are idempotent, convergence is fast (passes ≈ the depth of the
fix-dependency chain, typically 1–3). Heavy agents never run "on every lint fix"
because a lint commit ends the pass before they are reached. A short debounce on
Stage-1 entry — `concurrency: cancel-in-progress: true` keyed on the PR — collapses
rapid human pushes before heavy agents are reached.

Worked trace (a PR needing a lint autofix and an enforcer-fixable issue):

```
pass 1: lint commits a format fix → STOP (push)
pass 2: lint no-op, enforcer commits an axiom fix → STOP (push)
pass 3: lint no-op, enforcer no-op, qa no-op → CONVERGED; all statuses fresh on HEAD
```

`enforcer` ran **once**, not once per lint fix.

## 4. Per-agent contract (locked)

Every agent in the pipeline — enforcer, qa, mechanic, alignment, and any future agent
— obeys these rules. The enforcer already implements them; they are the template.

### 4.1 `workflow_call` is the only invocation surface

The agent's workflow file declares **only** `workflow_call`. No `pull_request`, no
`workflow_run`, no `schedule`, no `push`. Triggers are a separate concern: the
orchestrator (Stage 1/2) and consumer shims (§9) compose them. This is what guarantees
no agent self-triggers, which is what makes §3.4 convergence possible.

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

### 4.2 One named commit status, posted to HEAD SHA

The status name **equals** the agent name with `-status`:

| Agent                           | Status name        | Required gate?        |
| ------------------------------- | ------------------ | --------------------- |
| Enforcer (rbg)                  | `enforcer-status`  | yes                   |
| QA (marsha)                     | `qa-status`        | yes                   |
| Mechanic / dev (was merge-prep) | `mechanic-status`  | no (work, not a gate) |
| Alignment (pauli)               | `alignment-status` | **no** (advisory, §6) |

Skip is a **success outcome with descriptive text** — never `exit 1`. Examples:
`success` / "Skipped: HEAD SHA already reviewed" (§10); `failure` / "2 axiom
violations — see review" (real verdict).

### 4.3 One row in `specs/ENFORCEMENT-MAP.md`

Every agent declares which axioms / rules / lifecycle points it covers, under the
"PR-pipeline agents" section. A PR adding an agent that omits its enforcement-map row
fails enforcer review.

### 4.4 One `.github/agents/<name>.agent.md` prompt file

The prompt file is the agent's behaviour contract. It sources the canonical personality
(e.g. `aops-core/agents/rbg.md`) and adds PR-context wrapping (read `.agents/CORE.md`,
run `gh pr view`, format the review). Orchestration (the workflow) and behaviour (the
prompt) version independently.

### 4.5 Versioned ref per agent

Each agent ships under its own ref (`enforcer-v1`, `qa-v1`, `mechanic-v1`,
`alignment-v1`). Consumers pin to refs, never `@main`. Breaking changes ship as a new
tag with a migration note and a deprecation window.

### 4.6 Per-pass SHA-based loop-skip

Every agent checks "have I already reviewed _this exact SHA_?" before doing expensive
work — never "was the last commit authored by a bot?" (the v1 anti-pattern that caused
P2). Full protocol in §10.

## 5. Graduation — `admit-status` + armed auto-merge

Graduation is deliberately cheap: no bot approval, no agent, no checkout.

- The Environment-gated admission job (§3.2) does two things on approval:
  1. sets the required **`admit-status`** commit status to `success` on HEAD, and
  2. arms `gh pr merge --auto --squash --delete-branch`.
- The merge fires the moment **all required checks are green and the PR is mergeable**
  — immediately for an already-green PR, or after the Stage-2 loop converges green.
- **`admit-status` replaces v1's `merge-prep-status`** as the required gate. Because it
  is set by a human-approval-driven job rather than a merge-prep run, the no-op runner
  on every green PR (P5) is gone.
- **Carry-forward.** Once admitted at SHA _X_, `admit-status` carries forward across
  _agent-authored_ fix commits during the loop (the admission decision stands) — reuse
  the carry-forward logic in `pr-pipeline.yml`'s `initialize` job (success carries to a
  new SHA on `synchronize` unless a new `CHANGES_REQUESTED` arrived since). A new
  **human** push resets admission to pending (a substantive change must be re-judged).
- **`required_approving_review_count: 2 → 0`.** v1 needed two approvals because
  merge-prep counted as approval #1. v2 has no bot approval — the Environment gate plus
  `admit-status` is the human decision point. There is no review-approval to count.

> Sequencing: `admit-status` must be added to required checks in the _same_ change that
> drops approvals to 0 — otherwise there is a window where green checks alone permit a
> manual merge that bypasses the gate.

## 6. Alignment (pauli) — advisory, host-side, not a gate

Pauli's value is PKB context, and GHA cannot reach the Tailnet-internal PKB MCP. So
pauli runs **host-side** (where the PKB lives), dispatched by a light host cron, and
posts a **review verdict** that informs the human gate (§3.2). It is **not** a required
status check.

This is the deliberate simplification over the original draft, which specced alignment
as a required, fail-closed gate with a watchdog. In the two-stage model the **human
Environment approval is the alignment decision point** — the maintainer reads pauli's
verdict and decides. Consequences:

- No host-availability deadlock: if pauli has not (or cannot) run, the maintainer
  admits on their own judgement.
- No watchdog, no `pending → failure` flip, no required-status machinery.

Mechanism (light Option A): the triage orchestrator posts `alignment-status: pending`
and files an `alignment:queued` issue (cross-PR enumeration surface, since commit
statuses are not enumerable by label across SHAs); a host cron drains the queue,
dispatches `polecat run … pauli`, and pauli posts the review + a terminal
`alignment-status` (informational). The `alignment-status` value is advisory only.

> If pauli later proves reliable enough to gate on, promoting `alignment-status` to a
> required check is a one-line ruleset change — but that is explicitly out of scope for
> this version.

## 7. Branch protection — required status checks

The v2 ruleset (`.github/rulesets/pr-review-and-merge.yml`, applied to `refs/heads/dev`)
requires:

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
      # NOTE: merge-prep-status is removed (replaced by admit-status).

- type: pull_request
  parameters:
    required_approving_review_count: 0   # Env gate + admit-status is the human gate
    dismiss_stale_reviews_on_push: false
```

**No transitive gating.** Each agent owns its status directly; there is no single
`merge-prep-status` that an agent could forget to wait for or silently substitute.

## 8. Mechanical-CI naming contract

The framework declares a naming contract; consumers implement it from whatever pipeline
they like. academicOps itself **keeps check-run names** (`Lint / Lint`,
`Pytest / Pytest`) — they already exist, the ruleset already gates on them, and
re-emitting them as commit statuses is pure churn for a single repo.

For **cross-repo consumers** with heterogeneous stacks (Rust/Node/…), the portable form
is a commit status per concern:

| Status name        | Required? | Semantic                                         |
| ------------------ | --------- | ------------------------------------------------ |
| `lint-status`      | required  | Style/format checks pass (ruff/eslint/clippy/…). |
| `typecheck-status` | required  | Static type checks pass (or `success` + "n/a").  |
| `test-status`      | required  | Test suite passes.                               |
| `build-status`     | optional  | Build/compile/dist check.                        |

"The name is the contract" — branch protection requires the name; the framework does
not require any particular action/runner. A consumer may satisfy the contract with
either check-run names or `-status` commit statuses.

## 9. Cross-repo install

A consumer installs **only the agents it wants**, each via a one-file shim in
`.github/workflows/` (never a nested subdirectory — GitHub ignores nested workflow
files). Example — enforcer + qa, no mechanic:

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

Mechanical CI is consumer-owned (§8). Add or remove an agent by adding or deleting a
shim file — no wider rewrite.

## 10. Loop-skip protocol (normative)

For an agent `<name>` invoked by the orchestrator on PR HEAD SHA `H`:

1. Fetch the agent's own latest status on `H`:
   `GET /repos/{owner}/{repo}/commits/{H}/statuses`, filter `context == "<name>-status"`,
   sort `created_at` desc, take first.
2. Parse `target_sha` from that status's `target_url` (query param `?target_sha=<sha>`).
3. **If `target_sha == H`:** skip. Re-post `success` with the same `target_sha=H` and a
   "Skipped: SHA already reviewed" description. Exit 0. `committed=false`.
4. **Else:** review HEAD; fix what you can (`committed=true` if you pushed); post a
   terminal status with `target_url` ending `?target_sha=H`.

**Not in the contract:** author identity (the agent does not care _who_ pushed `H`,
only whether _this diff_ has been judged — conflating the two caused P2) and commit
trailers (advisory metadata for humans, never control flow).

This decouples "have we judged this SHA?" from "is the author a bot?" A benign
merge-from-base produces a new SHA, so the agent reviews it (a fast no-op verdict on the
real SHA); a re-trigger on the _same_ SHA short-circuits.

## 11. Migration plan (phased)

Each phase is independently shippable and leaves the pipeline working. **Phase 1
(enforcer) has shipped.** The no-op merge-prep (P5) is gone as of **Phase 3** (gate
becomes a cheap human-approval status) + **Phase 4** (retire the cron's no-op dispatch).

- **Phase 1 — Enforcer (DONE).** `agent-enforcer.yml` (`workflow_call`-only, SHA-skip,
  `enforcer-status`) + `.github/agents/enforcer.agent.md` + `trigger-enforcer.yml`;
  `enforcer-status` required. _Shipped._
- **Phase 2 — QA agent (marsha) to parity.** `agent-qa.yml` + `.github/agents/qa.agent.md`
  - `trigger-qa.yml`, modelled on enforcer; posts `qa-status` (§4); add to required checks.
- **Phase 3 — Triage orchestrator + convergence.** Rework `pr-pipeline.yml` into the
  triage orchestrator: chain lint → enforcer → qa via `needs:` + `committed`-output
  short-circuit (§3.4), keeping the existing `gate`/`guard-no-dist`/`initialize` jobs.
- **Phase 4 — Environment gate + `admit-status` + graduation.** Create the
  `pr-fix-loop` environment; add the env-gated admission job (sets `admit-status` with
  carry-forward, arms auto-merge, §5). Ruleset: `merge-prep-status → admit-status`, add
  `qa-status`, approvals `2 → 0`. **Sequence the `admit-status` add + approvals drop in
  one change** (§5 note).
- **Phase 5 — Stage-2 dev/mechanic.** Repurpose `agent-merge-prep.yml` into the
  admitted-loop dev agent (development to clear red + conflict resolution only when
  `CONFLICTING`); delete its fast-path/graduation steps. Retire `merge-prep-cron.yml`'s
  per-PR no-op dispatch.
- **Phase 6 — Alignment (pauli) advisory.** Light host-side dispatch (§6); not a
  required check. Plus cleanup of dead v1 references.

## 12. Open questions

1. **Stage-2 loop driver.** The fix loop re-triggers via the agents' pushes through the
   orchestrator (a new `synchronize` per pass). Confirm on a scratch PR that the
   admitted run re-enters cleanly and that `admit-status` carry-forward (§5) keeps the
   gate satisfied across agent commits without re-parking at the environment.
2. **`mechanic-status` necessity.** Mechanic does work, not a verdict (§4.2). Decide
   whether it needs a status at all, or whether its outcome is visible purely through
   the cheap-check + enforcer + qa statuses it re-greens.
3. **`MAX_MERGE_PREP_RUNS`-style ceiling.** Keep a convergence cap on the Stage-2 loop
   (carry over v1's ceiling) to bound runaway development loops; calibrate after real
   PRs.
4. **`target_sha` channel.** The `target_url` query-param hack (§10) is ugly but
   parsimonious; revisit only if a downstream consumer needs to query target-sha cleanly.

## 13. Cross-references

- [[pr-pipeline]] — v1 spec; describes the operative merge-prep until Phase 5 ships.
- `.github/rulesets/pr-review-and-merge.yml` — the ruleset to edit in Phase 4.
- `specs/ENFORCEMENT-MAP.md` — "PR-pipeline agents" rows (§4.3).
- PR #1037 / issue #1039 — the P2 worked example (enforcer skip + approval substitution).
- PR #1614 — the P5 worked example (no-op merge-prep on a docs PR).
- `aops-638a351e` — loose-trigger cache-waste evidence (P1).

### Supersession protocol

v2 sits alongside [[pr-pipeline]] until Phase 5. At that point [[pr-pipeline]] is
rewritten as a historical stub pointing here. The choice to keep `pr-pipeline-v2` as the
permalink (rather than overwriting v1) preserves the widespread v1 references during the
migration window.
