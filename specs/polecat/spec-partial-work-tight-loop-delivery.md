---
id: spec-partial-work-contract
title: "Spec contract: Partial-work / decentralised tight-loop delivery doctrine"
type: spec
status: draft
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

---

## 1. Thesis

It is legitimate — sometimes encouraged — for a worker on any surface (polecat container, in-session subagent, agent team; R1) to leave work unfinished: ship the **finished component** as a discrete reviewable chunk, decompose the rest into follow-up tasks, hand off. Less central pre-planning; more decentralised tight loops grounded in running code. Trust smart workers + version control; stop paying twice (plan-in-detail, then re-implement). The same doctrine covers decision limits, not just scope seams: **refuse-and-attempt** (R2, first-class in §3) makes handing back a partially-completed task after refusing non-derivable choices an expected, legal terminal outcome — not a failure.

This is **not** a licence to ship broken work behind a "draft" label. The whole contract is the discriminator (§3) between _a smaller whole thing, honestly disclosed_ and _the claimed thing with a defect laundered into "scope."_

## 2. Reconciliation (what this EXTENDS / NARROWS — no invariant altered)

- **EXTENDS the supervision architecture.** Adds a fourth terminal shape, `partial`, to the autonomous trust gate. **Inherits every locked invariant unchanged.** Stated surface-agnostically (R3/R7), the invariant is: **a partial deliverable never enters the human-approval one-way-door queue.** The single `APPROVED`-on-SHA merge trigger, per-repo merge policy (the policy table), clean-build "green", and per-SHA reviewer attestation are how the currently-deferred GitHub executor happens to enforce that invariant — GH is one optional executor; the PKB review task + receipt is the system of record. `partial` never satisfies any of these — it is _by construction_ not approval-ready (§4).
- **NARROWS "Partial completion is not success"** (`lib/axioms/do-one-thing.md`). That rule scopes to **a single claimed leaf**: _the claimed unit_ works completely or doesn't ship. It does **not** forbid cutting a large brief into a smaller whole leaf and shipping that. The rule is narrowed where it lives, not contradicted at a distance. **Refuse-and-attempt (§3, R2) goes beyond this NARROWed scoping:** a worker that refuses non-derivable decisions hands back at `partial` even though the claimed unit is not complete — legal because the refused decisions are surfaced through clauses 2b/3/4, not laundered as scope.
- **The pre-dispatch sizing gate** (the `brief` skill, `plugins/aops-core/skills/brief/SKILL.md`) runs **live, default, mandatory**: every released unit passes through it before dispatch. Its collision with "thin briefs, worker plans" was resolved to **NARROW** (a DECISION:Nic fork, decided reversibly): eligibility is a composable rule pauli records when assembling the task's workflow at brief time, not a two-tier epic carve-out. What the gate cuts on is an unresolved fork or a responsibility boundary — never size — so the default outcome is one whole unit, which is what leaves the worker room to plan.

## 3. Q1 — the discriminator (partial vs broken-ship)

`partial` = a _whole smaller thing_, cut at a scope seam, that builds clean and is honestly disclosed. **broken-ship** = the _claimed_ thing with a defect inside the shipped surface, relabelled "draft."

The stop gate is governed by clauses that are **instruction-led and honesty-audited, NOT regex/keyword-matched** (per `judgment-non-delegable` — instruction-led register, mechanical tiering explicitly not wanted). The honesty floor (ida, always-on) audits the worker's self-certification.

**Clause 1 — scope seam, not defect seam.** The cut is at a component/feature boundary the worker can name, not through the middle of a behaviour. The shipped chunk is a thing a reader can review as complete-in-itself.

**Clause 2 — clean build, no red test in the diff.** The shipped surface builds clean from a clean checkout; no failing test is present in the diff. _(This clause alone is blind to the absent-test hole — see 2b.)_

**Clause 2b — acceptance-criterion coverage partition (NEW — closes the absent-test hole).** Each acceptance criterion of the shipped chunk (from the brief / originating task) MUST resolve to exactly one of three states:

- **tested** — a green test in the diff exercises it; or
- **declared-deferred** — an explicit entry in the PKB task record's `## Deliberately deferred` disclosure (canonical, surface-agnostic — same anchoring as clause 4) names the AC as _not-yet-attempted_, with a live follow-up task; where the deliverable is a PR, the PR's `## Deliberately deferred` section is the GitHub-surface projection of that entry; or
- **illegal-gap** — silently absent from both. **An AC in this state FAILS the stop gate.**

This converts "absent test" from invisible to a checkable three-way partition (`tested | declared-deferred | illegal-gap`). It closes the laundering path Stage-3 found: _worker hits a bug in component A, never writes the catching test, ships A as "finished," decomposes the buggy behaviour as "deferred scope"_ — because the bugged AC is now either tested, or explicitly declared-deferred (visible to the reviewer and Nic), or an illegal gap that fails the stop. The defect can no longer hide in the silence between "tested" and "unstarted scope."

**This is a judgment call the worker self-certifies and the honesty floor audits — it is NOT a new mechanical gate.** Per `exercise-authority` Edge 3 and `judgment-non-delegable`: the AC→state mapping is qualitative. **An implementer MUST NOT build a deterministic coverage-gate / regex / keyword-scan to enforce 2b.** The enforcement is the ida honesty floor (always-on, every register) + reviewer audit, consistent with the settled ida tiering. The spec states this so Stage-5 implementation does not regress into NLP-matching.

**Clause 3 — no orphan.** Every deferred remainder has a live follow-up task (a _continue_ task; any review is performed against the deliverable/PR, not via a separate pre-emitted review node). The PKB task record's `## Deliberately deferred` disclosure links them — canonical on every surface; where the deliverable is a PR, the PR's `## Deliberately deferred` section mirrors that list as the GitHub-surface projection. Anti-sprawl backstop in §6.

**Clause 4 — disclosed.** The canonical, surface-agnostic marker is on the PKB task (R1/R6): the task carries the `partial` terminal status, the disclosure fired in the honesty register, and the evidence + output URL are written to the task. Whenever the deliverable is a PR (the polecat/GitHub surface), the PR MUST be opened as a **draft** PR (`gh pr create --draft`, structurally unmergeable) — but that draft PR is the GitHub-surface **projection** of `partial`, not part of the state's definition. An in-session subagent or agent team reaches `partial` with no PR at all: its output URL and disclosure live on the task. (Terminology: ruling R2's word "DRAFT" maps onto this existing `partial` status — "draft" names only the PR mechanism, never a PKB status.)

A chunk passing all of 1, 2, 2b, 3, 4 is `partial`. A chunk failing any is either fixed before ship or reverted (feature-dev fail-fast still governs the _claimed leaf_).

**Refuse-and-attempt (first-class, R2).** A worker REFUSES to make choices not derivable with reasonable confidence from the axioms + available context — but still ATTEMPTS everything it can, and hands the task back at `partial` with the refused decisions surfaced. This satisfies the discriminator via clauses 2b/3/4 even when the shipped chunk is small: each refused decision resolves its AC to **declared-deferred** (2b), carries a live follow-up (3), and is disclosed on the task (4). It is expected, legal, first-class behavior — not a failure — and dispatch MUST NOT compensate by fattening briefs into step-scripts: briefs leave workers actual thinking work, not mechanical instructions (R2: no micromanaging).

## 4. The `partial` terminal state

`partial` is an existing, canonical terminal status **on the PKB task** (shipped in the status taxonomy; §6 covers the server/client status-enum dependency the orphan-backstop query needs) — the surface-agnostic marker (§3 clause 4, R1) — distinct from `merge_ready` and from draft-abandonment:

- **vs `merge_ready`:** the inherited invariant, stated surface-agnostically, is that **a partial deliverable never enters the human-approval one-way-door queue**. On the GitHub surface this is enforced structurally: a `partial` PR is opened with `gh pr create --draft`, and GitHub draft PRs **cannot** be merged and never produce an `APPROVED`-on-SHA auto-merge. That is how the currently-deferred GitHub executor happens to enforce the invariant (R3/R7 — GH is one optional executor; the PKB review task + receipt is the system of record); non-PR partials honour the same invariant by never being marked approval-ready on the task.
- **vs abandonment:** clause 3 (no-orphan) + §6 backstop guarantee a live follow-up exists. A `partial` with no live child is itself a gate failure.

`partial` is a legitimate place for an autonomous worker to **stop** (it satisfies the Stop hook's "done-pending-more-work" — the worker shipped a reviewable chunk and queued the remainder); it is **not** a place Nic's approval queue (the human one-way door) ever sees as ready.

## 5. Eligibility — a composable workflow rule

Thin-brief/`partial` eligibility and review depth are composable rules pauli records when assembling the task's workflow at decomposition.

## 6. Q3 — net review load + the anti-sprawl backstop

**Net load: RELIEVES, conditional on no-orphan.** A `partial` deliverable never enters the human-approval one-way-door queue (§4; on the GitHub surface, the draft PR's `APPROVED`-on-SHA exclusion enforces this), so it adds zero to the _approval-decision_ load that is the actual approval-decision-load ceiling. Fix-or-bounce (reviewers **independent of the worker's session**, at the pauli-specified level — R3 — fix or send up) removes the advisory-notes load source. The falsifier is **draft sprawl**: `partial` tasks that never get continued, accumulating as orphans.

**No loop-closer currently covers the `partial` orphan case.** No shipped skill runs a periodic stuck-work sweep of any kind today (a red-CI/stuck-PR loop-closer is not part of the current skill set). Even if one existed, a stuck-red-CI selector would not catch an orphaned `partial`: a `partial` PR is a **green** draft, so it never matches a stuck-_red_-CI check. The orphan-draft falsifier therefore has no mitigation yet beyond worker discipline.

**Specified backstop — the `partial`-orphan loop-closer.** A periodic pass, keyed off PKB task status (`list_tasks(status="partial")`), that mirrors a stuck-work loop-closer's shape but selects on `partial` status rather than CI outcome.

This backstop query has a dependency chain that must be in place before it can run: (1) the **PKB server's status enum** must accept `partial` as a valid `list_tasks` filter value — a server that silently matches all tasks instead of erroring on an unrecognised status would return garbage, not an orphan set; (2) the **client-side task-status validation** (wherever a worker persists task status) must allow emitting `partial`, since the server cannot accept a status the client never sends; (3) only once both hold does `list_tasks(status="partial")` return a trustworthy orphan set. Until then, clause 3 (worker no-orphan discipline) is the only live guard.

The pass:

1. `list_tasks(status="partial")` → candidate orphan-drafts.
2. For each, confirm a **live follow-up (continue) task** exists and is open (clause 3). If one exists and is open → healthy; skip.
3. Where the `partial` task has **no open continue-task** (orphaned) OR — as a **polecat/GitHub-surface supplement** — its draft PR has been idle **> 7 days** with no commits → surface it in the daily note under "What Needs Attention / Stalled partials" with the output URL and the missing-continue-task flag. (The `list_tasks(status="partial")` PKB query is the **primary** backstop; the draft-PR-idle check only applies where the deliverable is a PR — non-PR partials exist under R1 and are covered by the PKB query alone.) Where the continue-task is simply missing, **file one** via `create_task` (tags `partial-continue`; same dedupe + **severity guard** as the red-CI loop-closer — routine, not SEV3/4).
4. Same **artefact-freshness discipline** as the rest of the daily pass: if the PKB query is stale, report `partial loop-closer: skipped — artefact stale` and take no action.

Once the server/client status-enum dependency chain above is in place, this keys off a real `partial` query and is a standalone pass. It does not depend on any CI-self-heal mechanism — but it does depend on the server-enum fix, without which the query is not trustworthy.

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

1. **Clause 2b is honesty-bound, not mechanically guaranteed.** By deliberate design (No-Shitty-NLP), the AC→state partition rests on worker self-certification + ida + reviewer audit. A worker that lies in _both_ its self-cert _and_ its `## Deliberately deferred` section, past a reviewer who doesn't re-derive the ACs, can still launder a defect. The mitigation is the always-on ida floor + the reviewer's own AC re-read, not a gate. **This is a residual, not a closure** — a dogfood pass is the instrument that tests whether the honesty floor actually binds here.
2. **The §6 `partial`-orphan loop-closer is specified, not yet built.** Draft-sprawl is bounded only by worker discipline (clause 3) until _all three_ of the server status-enum fix, the client-side status-validation fix, and the §6 pass itself land. Net-honest, not net-mitigated, until those land.
3. **§5's eligibility signal depends on the promotion log being honestly written** by the recording agent. The seam is narrower than worker-frontmatter (the recorder is pauli at decomposition, whose output sits under the standing independent-review tasks) but not zero — a careless recorder could mis-record eligibility. Auditability (the log is inspectable) is the mitigation, not prevention.
4. **The 7-day idle threshold (§6 step 3) is a guess**, not tuned against field data. Stage-5 dogfood + first production cycles should calibrate it.

No claimed mitigation in this spec rests on a capability that does not exist; where a mitigation is pending-build it is labelled as such (residuals 2 + 4).
