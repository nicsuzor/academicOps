---
id: spec-partial-work-contract
title: "Spec contract: Partial-work / decentralised tight-loop delivery doctrine"
type: spec
status: draft
parent: aops-ee633abb
permalink: spec-partial-work-tight-loop-delivery
tags:
  - spec
  - polecat
  - doctrine
  - partial-work
  - decomposition
  - review
  - terminal-state
  - tight-loop
---

# Spec contract: Partial-work / decentralised tight-loop delivery doctrine

**Graph anchor:** [[spec-partial-work]] (PKB node). **Epic:** [[aops-2e5105f5]]. **Stage-1 stories:** [[note-2b773bde]]. **Recon (file map):** [[note-0e871b87]]. **Reconciled specs:** [[note-36c15a69]] (the companion roadmap-tracker note, `spec-64352eac-planner-pre-dispatch-decomposition-gate.md`, was a planning artifact retired during the 2026-07 simplification pass -- see git history).

**Revision log:** Stage 2 authored (pauli). Stage 3 independent review ([[aops-7f8b5920]]) returned REVISE. **Stage 4 (this file) closes the two FAILs + two seam-tightenings and resolves the §5 fork to NARROW** per Nic's working-default authorization (via junior). Honest about residual risk in §8. **2026-07-19:** aligned with Nic's ratified rulings ([[note_ad2ed3d2]]): `partial` made surface-agnostic (the draft PR is now the GitHub-surface projection, not the definition), refuse-and-attempt homed here as first-class (R2), §5 re-cut from epic-tiering to a composable rule pauli records when assembling the task's workflow (R1/R3/R4), and the inherited merge invariant restated as the human-approval one-way-door (R7).

> **Substance note (honest, surfaced not buried):** the Stage-2 task recorded that this contract file existed at this path. It did not — only the PKB anchor node was written. Stage 4 authored the actual contract here. The anchor node's compressed headlines were the real Stage-2 deliverable; this file is their expansion plus the Stage-3 fixes. Trust Version Control: this is the single source of truth from here; no `_v2`.

---

## 1. Thesis

It is legitimate — sometimes encouraged — for a worker on any surface (polecat container, in-session subagent, agent team; R1) to leave work unfinished: ship the **finished component** as a discrete reviewable chunk, decompose the rest into follow-up tasks, hand off. Less central pre-planning; more decentralised tight loops grounded in running code. Trust smart workers + version control; stop paying twice (plan-in-detail, then re-implement). The same doctrine covers decision limits, not just scope seams: **refuse-and-attempt** (R2, first-class in §3) makes handing back a partially-completed task after refusing non-derivable choices an expected, legal terminal outcome — not a failure.

This is **not** a licence to ship broken work behind a "draft" label. The whole contract is the discriminator (§3) between _a smaller whole thing, honestly disclosed_ and _the claimed thing with a defect laundered into "scope."_

## 2. Reconciliation (what this EXTENDS / NARROWS — no invariant altered)

- **EXTENDS [[note-36c15a69]]** (supervision architecture). Adds a fourth terminal shape, `partial`, to the autonomous trust gate. **Inherits every locked invariant unchanged.** Stated surface-agnostically (R3/R7), the invariant is: **a partial deliverable never enters the human-approval one-way-door queue.** The single `APPROVED`-on-SHA merge trigger (note-36c15a69 §"Decisions locked"), per-repo merge policy (the policy table), clean-build "green", and per-SHA reviewer attestation are how the currently-deferred GitHub executor happens to enforce that invariant — GH is one optional executor; the PKB review task + receipt is the system of record. `partial` never satisfies any of these — it is _by construction_ not approval-ready (§4).
- **NARROWS feature-dev's "No partial success"** (`.agents/skills/aops/references/feature-dev-details.md` L34/L211/L278). That rule scopes to **a single claimed leaf**: _the claimed unit_ works completely or doesn't ship. It does **not** forbid cutting a large brief into a smaller whole leaf and shipping that. The in-place edit to feature-dev-details.md (Stage 5 chunk) must state this scoping explicitly — the rule is narrowed where it lives, not contradicted at a distance. **Refuse-and-attempt (§3, R2) goes beyond this NARROWed scoping:** a worker that refuses non-derivable decisions hands back at `partial` even though the claimed unit is not complete — legal because the refused decisions are surfaced through clauses 2b/3/4, not laundered as scope.
- **The pre-dispatch decomposition gate** (the current decompose skill, `aops/skills/decompose/SKILL.md`) is **live, default, mandatory**. Its collision with "thin briefs, worker plans" was resolved to **NARROW** (a DECISION:Nic fork, decided reversibly) and has since been **re-cut in §5** per the 2026-07-19 rulings: eligibility is now a composable rule pauli records when assembling the task's workflow at decomposition, not a two-tier epic carve-out.

## 3. Q1 — the discriminator (partial vs broken-ship)

`partial` = a _whole smaller thing_, cut at a scope seam, that builds clean and is honestly disclosed. **broken-ship** = the _claimed_ thing with a defect inside the shipped surface, relabelled "draft."

The stop gate is governed by clauses that are **instruction-led and honesty-audited, NOT regex/keyword-matched** (per No-Shitty-NLP P#49 and the ida tiering Nic settled in [[note-36c15a69]] — "instruction-led register, mechanical tiering explicitly NOT wanted"). The honesty floor (ida, always-on) audits the worker's self-certification.

**Clause 1 — scope seam, not defect seam.** The cut is at a component/feature boundary the worker can name, not through the middle of a behaviour. The shipped chunk is a thing a reader can review as complete-in-itself.

**Clause 2 — clean build, no red test in the diff.** The shipped surface builds clean from a clean checkout; no failing test is present in the diff. _(This clause alone is blind to the absent-test hole — see 2b.)_

**Clause 2b — acceptance-criterion coverage partition (NEW — closes the absent-test hole).** Each acceptance criterion of the shipped chunk (from the brief / originating task) MUST resolve to exactly one of three states:

- **tested** — a green test in the diff exercises it; or
- **declared-deferred** — an explicit entry in the PKB task record's `## Deliberately deferred` disclosure (canonical, surface-agnostic — same anchoring as clause 4) names the AC as _not-yet-attempted_, with a live follow-up task; where the deliverable is a PR, the PR's `## Deliberately deferred` section is the GitHub-surface projection of that entry; or
- **illegal-gap** — silently absent from both. **An AC in this state FAILS the stop gate.**

This converts "absent test" from invisible to a checkable three-way partition (`tested | declared-deferred | illegal-gap`). It closes the laundering path Stage-3 found: _worker hits a bug in component A, never writes the catching test, ships A as "finished," decomposes the buggy behaviour as "deferred scope"_ — because the bugged AC is now either tested, or explicitly declared-deferred (visible to the reviewer and Nic), or an illegal gap that fails the stop. The defect can no longer hide in the silence between "tested" and "unstarted scope."

**This is a judgment call the worker self-certifies and the honesty floor audits — it is NOT a new mechanical gate.** Per `exercise-authority` Edge 3 and `judgment-non-delegable`: the AC→state mapping is qualitative. **An implementer MUST NOT build a deterministic coverage-gate / regex / keyword-scan to enforce 2b.** The enforcement is the ida honesty floor (always-on, every register) + reviewer audit, consistent with the settled ida tiering. The spec states this so Stage-5 implementation does not regress into NLP-matching.

**Clause 3 — no orphan.** Every deferred remainder has a live follow-up task (a _continue_ task; a _review_ task if the chunk needs review beyond the deliverable). The PKB task record's `## Deliberately deferred` disclosure links them — canonical on every surface; where the deliverable is a PR, the PR's `## Deliberately deferred` section mirrors that list as the GitHub-surface projection. Anti-sprawl backstop in §6.

**Clause 4 — disclosed.** The canonical, surface-agnostic marker is on the PKB task (R1/R6): the task carries the `partial` terminal status, the disclosure fired in the honesty register, and the evidence + output URL are written to the task. Whenever the deliverable is a PR (the polecat/GitHub surface), the PR MUST be opened as a **draft** PR (`gh pr create --draft`, structurally unmergeable) — but that draft PR is the GitHub-surface **projection** of `partial`, not part of the state's definition. An in-session subagent or agent team reaches `partial` with no PR at all: its output URL and disclosure live on the task. (Terminology: ruling R2's word "DRAFT" maps onto this existing `partial` status — "draft" names only the PR mechanism, never a PKB status.)

A chunk passing all of 1, 2, 2b, 3, 4 is `partial`. A chunk failing any is either fixed before ship or reverted (feature-dev fail-fast still governs the _claimed leaf_).

**Refuse-and-attempt (first-class, R2).** A worker REFUSES to make choices not derivable with reasonable confidence from the axioms + available context — but still ATTEMPTS everything it can, and hands the task back at `partial` with the refused decisions surfaced. This satisfies the discriminator via clauses 2b/3/4 even when the shipped chunk is small: each refused decision resolves its AC to **declared-deferred** (2b), carries a live follow-up (3), and is disclosed on the task (4). It is expected, legal, first-class behavior — not a failure — and dispatch MUST NOT compensate by fattening briefs into step-scripts: briefs leave workers actual thinking work, not mechanical instructions (R2: no micromanaging).

## 4. The `partial` terminal state

`partial` is an existing, canonical terminal status **on the PKB task** (shipped in the status taxonomy and the mem server enum, #414 — see §6 Correction for the client-side remainder) — the surface-agnostic marker (§3 clause 4, R1) — distinct from `merge_ready` and from draft-abandonment:

- **vs `merge_ready`:** the inherited invariant, stated surface-agnostically, is that **a partial deliverable never enters the human-approval one-way-door queue**. On the GitHub surface this is enforced structurally: a `partial` PR is opened with `gh pr create --draft`, and GitHub draft PRs **cannot** be merged and never produce an `APPROVED`-on-SHA auto-merge. That is how the currently-deferred GitHub executor happens to enforce the invariant (R3/R7 — GH is one optional executor; the PKB review task + receipt is the system of record); non-PR partials honour the same invariant by never being marked approval-ready on the task. `finalize.py` currently hard-codes `merge_ready` as the only terminal (recon [[note-0e871b87]] #5); Stage 5 adds `partial` as a sibling terminal.
- **vs abandonment:** clause 3 (no-orphan) + §6 backstop guarantee a live follow-up exists. A `partial` with no live child is itself a gate failure.

`partial` is a legitimate place for an autonomous worker to **stop** (it satisfies the Stop hook's "done-pending-more-work" — the worker shipped a reviewable chunk and queued the remainder); it is **not** a place Nic's approval queue (the human one-way door) ever sees as ready.

## 5. Eligibility — a composable workflow rule (re-cut 2026-07-19; supersedes the NARROW two-tier fork)

This section is superseded by the unified worker contract and the 2026-07-19 rulings; thin-brief/`partial` eligibility and review depth are now composable rules recorded at decomposition. See [[note_ad2ed3d2]] and the updated workflow spec.

## 6. Q3 — net review load + the anti-sprawl backstop

**Net load: RELIEVES, conditional on no-orphan.** A `partial` deliverable never enters the human-approval one-way-door queue (§4; on the GitHub surface, the draft PR's `APPROVED`-on-SHA exclusion enforces this), so it adds zero to the _approval-decision_ load that is the actual [[kb-524d60d7]] ceiling. Fix-or-bounce (reviewers **independent of the worker's session**, at the pauli-specified level — R3 — fix or send up) removes the advisory-notes load source. The falsifier is **draft sprawl**: `partial` tasks that never get continued, accumulating as orphans.

**Backstop verification (FIX 2 — verified against ground truth, result stated):**

The Stage-3 review claimed the no-orphan guarantee rests on an **unbuilt** `/daily` loop-closer ([[note-36c15a69]] L180). **Verification result: the claim is half-stale.** The `/daily` loop-closer **IS built** — `aops/skills/daily/SKILL.md` L278–298 ("Red-CI / stuck-PR loop-closer", shipped under WS2). **BUT it does not cover the `partial` case.** It keys off `$AOPS_SESSIONS/state/pr-state.json` and selects only **stuck-_red_-CI** candidates (`statusCheckRollup conclusion == "FAILURE"`, `updatedAt > 24h`). A `partial` PR is a **green** draft — it never matches the stuck-red selector. So for the orphan-draft falsifier specifically, the mitigation is **genuinely unbuilt**: the right surface exists but is keyed on the wrong signal.

**Specified backstop — the `partial`-orphan loop-closer.** Stage 5 adds a sibling pass to `/daily`, mirroring the _proven, deployed_ red-CI loop-closer pattern but keyed off PKB task status (`list_tasks(status="partial")`).

> **Correction (assumption falsified by implementation).** The original draft of this section asserted `list_tasks(status="partial")` was _deployed infrastructure queryable today_. That was false. The live PKB MCP server (mem, Rust) rejected the `partial` status enum, and `list_tasks` silently matched **all** tasks rather than erroring — so the backstop query would have returned garbage, not orphan-drafts. The real mechanism has three load-bearing parts, each of which had to be built: (1) the **mem server status enum** must accept `partial` (mem PR #414 — `graph.rs` + `mcp_server.rs`, list-filter fixed, round-trip tested); (2) the **academicOps client** `pkb_bridge.py` `VALID_TASK_STATUSES` must include `partial` so the worker can persist it (continue task [[aops-8d3e43a1]], gated on #414 deploy — the server must accept before the client may emit); (3) **only then** does this §6 `list_tasks(status="partial")` backstop return a true orphan set. The gap was invisible to both this spec and the recon; it surfaced only when a worker tried to persist `partial` against the running server. Until #414 + [[aops-8d3e43a1]] are deployed, the backstop query is not yet trustworthy — clause 3 (worker no-orphan discipline) is the only live guard.

The pass:

1. `list_tasks(status="partial")` → candidate orphan-drafts.
2. For each, confirm a **live follow-up (continue) task** exists and is open (clause 3). If one exists and is open → healthy; skip.
3. Where the `partial` task has **no open continue-task** (orphaned) OR — as a **polecat/GitHub-surface supplement** — its draft PR has been idle **> 7 days** with no commits → surface it in the daily note under "What Needs Attention / Stalled partials" with the output URL and the missing-continue-task flag. (The `list_tasks(status="partial")` PKB query is the **primary** backstop; the draft-PR-idle check only applies where the deliverable is a PR — non-PR partials exist under R1 and are covered by the PKB query alone.) Where the continue-task is simply missing, **file one** via `create_task` (tags `partial-continue`; same dedupe + **severity guard** as the red-CI loop-closer — routine, not SEV3/4).
4. Same **artefact-freshness discipline** as the rest of `/daily`: if the PKB query or `pr-state.json` is stale, report `partial loop-closer: skipped — artefact stale` and take no action.

Once the §6 Correction's dependency chain (mem #414 + [[aops-8d3e43a1]]) is deployed, this keys off a real `partial` query + the deployed `/daily` artefact pipeline (not the unbuilt GHA self-heal) and is a standalone pass, mirroring the proven red-CI loop-closer pattern. It does **not** hard-block on the unbuilt self-heal — but, per the Correction, it **does** depend on the server-enum fix, which the original draft wrongly treated as already present.

## 7. Fitness Rubric

The rubric bites hardest on the discriminator (§3) and the load proof (§6). A dogfood pass (Stage-5 QA, epic output #5) is the falsifier instrument:

| Dimension                   | Excellence looks like                                                                                                                                    | Failure signal                                                                      |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Discriminator integrity** | A planted bug whose catching test is never written FAILS the stop (clause 2b illegal-gap), or is visibly declared-deferred — never laundered as "scope." | The dogfood worker ships a green draft with a silent bugged AC and the gate passes. |
| **No-NLP discipline**       | Clause 2b is enforced by worker self-cert + ida honesty floor + reviewer audit.                                                                          | An implementer built a regex/keyword coverage-gate.                                 |
| **No orphans**              | Every `partial` has a live continue-task; the §6 loop-closer files one where missing.                                                                    | A `partial` PR with no continue-task survives a `/daily` cycle un-surfaced.         |
| **Load relief**             | Draft `partial` PRs stay out of the merge queue; sprawl is bounded by the §6 backstop.                                                                   | Draft sprawl accumulates (the falsifier fires) at Stage-5 dogfood.                  |
| **Eligibility integrity**   | A worker cannot self-promote into the thin-brief path via frontmatter; the recorder's log is the auditable signal.                                       | A mis-set `uncertainty` frontmatter routes heavy work onto the thin path.           |
| **Invariant preservation**  | A `partial` deliverable never enters the human-approval one-way-door queue (on GitHub: never trips `APPROVED`-on-SHA); per-repo policy intact.           | Any path, on any surface, by which a `partial` reaches Nic's approval queue.        |

## 8. Residual risk (honest, after the fixes)

1. **Clause 2b is honesty-bound, not mechanically guaranteed.** By deliberate design (No-Shitty-NLP), the AC→state partition rests on worker self-certification + ida + reviewer audit. A worker that lies in _both_ its self-cert _and_ its `## Deliberately deferred` section, past a reviewer who doesn't re-derive the ACs, can still launder a defect. The mitigation is the always-on ida floor + the reviewer's AC re-read (the same `merge-close-ac-check` discipline `/daily` already runs), not a gate. **This is a residual, not a closure** — the dogfood (Stage 5) is the instrument that tests whether the honesty floor actually binds here.
2. **The §6 `partial`-orphan loop-closer is specified, not yet built — and its query depends on a server-enum fix that the spec wrongly assumed was already deployed.** Draft-sprawl is bounded only by worker discipline (clause 3) until _all three_ of mem PR #414 (server accepts `partial`), [[aops-8d3e43a1]] (client `pkb_bridge.py` emits `partial`), and the §6 daily pass land. The original "deployed PKB infra" assumption was empirically falsified during implementation (see §6 Correction); this residual now names the real dependency chain. Net-honest, not net-mitigated, until those land.
3. **§5's eligibility signal depends on the promotion log being honestly written** by the recording agent. The seam is narrower than worker-frontmatter (the recorder is pauli at decomposition, whose output sits under the standing independent-review tasks) but not zero — a careless recorder could mis-record eligibility. Auditability (the log is inspectable) is the mitigation, not prevention.
4. **The 7-day idle threshold (§6 step 3) is a guess**, not tuned against field data. Stage-5 dogfood + first production cycles should calibrate it.

No claimed mitigation in this spec rests on a capability that does not exist; where a mitigation is pending-build it is labelled as such (residuals 2 + 4).
