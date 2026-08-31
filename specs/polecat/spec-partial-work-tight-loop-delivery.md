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

## Thesis

A worker on any surface — polecat container, in-session subagent, agent team — may
legitimately leave work unfinished: ship the **finished component** as a discrete
reviewable chunk, decompose the rest into follow-up tasks, hand off. Less central
pre-planning; more decentralised tight loops grounded in running code. Trust smart
workers and version control, and stop paying twice for plan-in-detail then
re-implement.

The same doctrine covers decision limits as well as scope seams. **Refuse-and-attempt**
is first-class: a worker refuses choices it cannot derive with reasonable confidence
from the axioms and available context, still attempts everything it can, and hands
the task back with the refused decisions surfaced. That is an expected, legal
terminal outcome, not a failure — and dispatch must not compensate by fattening
briefs into step-scripts. Briefs leave workers actual thinking work.

None of this licenses shipping broken work behind a "draft" label. The whole value
of this contract is the discriminator below, between _a smaller whole thing,
honestly disclosed_ and _the claimed thing with a defect laundered into "scope."_

## What this changes, and what it does not

**It adds a fourth terminal shape, `partial`, and inherits every locked invariant
unchanged.** Stated surface-agnostically, the governing invariant is: **a partial
deliverable never enters the human-approval one-way-door queue.** GitHub is one
optional executor of that invariant — the single `APPROVED`-on-SHA merge trigger,
per-repo merge policy, clean-build green, per-SHA reviewer attestation — but the
PKB review task and its receipt are the system of record. `partial` satisfies none
of those triggers, by construction.

**It narrows "Partial completion is not success"**
([`lib/axioms/do-one-thing.md`](../../lib/axioms/do-one-thing.md)), it does not
contradict it. That rule scopes to **a single claimed leaf**: the claimed unit works
completely or it does not ship. It does not forbid cutting a large brief into a
smaller whole leaf and shipping that. Refuse-and-attempt goes one step beyond that
scoping — a worker hands back at `partial` even though the claimed unit is not
complete — and is legal only because the refused decisions are surfaced through
clauses 3, 4 and 5 rather than laundered as scope.

**It does not create a size carve-out.** The pre-dispatch sizing gate (the
[`brief`](../../plugins/aops/skills/brief/SKILL.md) skill) runs live, default and
mandatory on every released unit. What it cuts on is an unresolved fork or a
responsibility boundary — never size — so its default outcome is one whole unit,
which is exactly what leaves the worker room to plan. Thin-brief and `partial`
eligibility, and review depth, are composable rules pauli records when assembling
the task's workflow at decomposition.

## The discriminator: `partial` vs broken-ship

`partial` = a _whole smaller thing_, cut at a scope seam, that builds clean and is
honestly disclosed. **broken-ship** = the _claimed_ thing with a defect inside the
shipped surface, relabelled "draft."

A chunk is `partial` only if all five clauses hold. Failing any, it is fixed before
ship or reverted — fail-fast still governs the claimed leaf.

**1 — scope seam, not defect seam.** The cut is at a component or feature boundary
the worker can name, not through the middle of a behaviour. The shipped chunk is
reviewable as complete-in-itself.

**2 — clean build, no red test in the diff.** The shipped surface builds clean from
a clean checkout. On its own this clause is blind to the absent-test hole, which is
what clause 3 closes.

**3 — acceptance-criterion coverage partition.** Each acceptance criterion of the
shipped chunk resolves to exactly one of three states:

- **tested** — a green test in the diff exercises it;
- **declared-deferred** — an explicit entry in the task record's
  `## Deliberately deferred` disclosure names the AC as not-yet-attempted, with a
  live follow-up task;
- **illegal-gap** — silently absent from both. **This state fails the stop gate.**

This converts "absent test" from invisible into a checkable three-way partition. It
closes the laundering path where a worker hits a bug in component A, never writes
the catching test, ships A as "finished", and decomposes the buggy behaviour as
"deferred scope": the bugged AC is now either tested, or visibly declared-deferred,
or an illegal gap that fails the stop. The defect can no longer hide in the silence
between "tested" and "unstarted scope."

**Enforcement is judgment, not a rig.** The AC→state mapping is qualitative, so per
[`judgment-non-delegable`](../../lib/axioms/judgment-non-delegable.md) an
implementer must **not** build a deterministic coverage gate, regex, or keyword
scan for it. Enforcement is worker self-certification, the always-on ida honesty
floor auditing that self-certification, and reviewer audit. This is stated here so
implementation does not regress into keyword matching.

**4 — no orphan.** Every deferred remainder has a live follow-up _continue_ task.
Review is performed against the deliverable itself, not via a separately
pre-emitted review node. The `## Deliberately deferred` disclosure links them.

**5 — disclosed.** The canonical marker is on the PKB task: it carries the
`partial` terminal status, the disclosure fired in the honesty register, and the
evidence plus output URL are written to the task.

## The `partial` terminal state

`partial` is a canonical terminal status in the closed status taxonomy, and the
surface-agnostic marker for clause 5. It is distinct from `merge_ready` and from
abandonment:

- **vs `merge_ready`** — a partial deliverable never enters the human-approval
  one-way-door queue. Where the deliverable is a PR, that is enforced structurally:
  the PR is opened with `gh pr create --draft`, and a GitHub draft PR cannot be
  merged and never produces an `APPROVED`-on-SHA auto-merge. That draft PR is the
  GitHub-surface **projection** of `partial`, not part of the state's definition —
  an in-session subagent or agent team reaches `partial` with no PR at all, its
  output URL and disclosure living on the task. ("Draft" names only the PR
  mechanism; it is never a PKB status.) Non-PR partials honour the same invariant
  by never being marked approval-ready on the task.
- **vs abandonment** — clause 4 and the backstop below guarantee a live follow-up
  exists. A `partial` with no live child is itself a gate failure.

`partial` is therefore a legitimate place for an autonomous worker to **stop** — it
satisfies the Stop hook's "done-pending-more-work", the worker having shipped a
reviewable chunk and queued the remainder — and never a state the human approval
queue sees as ready.

## Review load, and the sprawl falsifier

**Net effect: relieves, conditional on no-orphan.** A `partial` deliverable never
enters the approval queue, so it adds zero to the approval-decision load that is
the real ceiling. Fix-or-bounce — reviewers independent of the worker's session, at
the pauli-specified level, who fix or send up — removes the advisory-notes load
source.

The falsifier is **draft sprawl**: `partial` tasks that never get continued,
accumulating as orphans. Nothing catches this today. No shipped skill runs a
periodic stuck-work sweep of any kind, and even a stuck-red-CI loop-closer would
not catch an orphaned `partial`, because a `partial` PR is a **green** draft and
never matches a stuck-red selector. Worker discipline under clause 4 is the only
live guard.

### The `partial`-orphan loop-closer — specified, not built

A periodic pass keyed off PKB task status rather than CI outcome:

1. `list_tasks(status="partial")` → candidate orphan-drafts.
2. For each, confirm a **live, open continue task** exists (clause 4). If so →
   healthy, skip.
3. Where there is no open continue task — or, as a PR-surface supplement only, the
   draft PR has been idle **> 7 days** with no commits — surface it in the daily
   note under "What Needs Attention / Stalled partials", with the output URL and
   the missing-continue-task flag. Where the continue task is simply missing,
   **file one** via `create_task` (tag `partial-continue`), with the same dedupe
   and severity guard as any routine loop-closer — routine, not SEV3/4.
4. Same artefact-freshness discipline as the rest of the daily pass: if the PKB
   query is stale, report `partial loop-closer: skipped — artefact stale` and take
   no action.

The `list_tasks(status="partial")` query is the primary backstop; the draft-PR-idle
check applies only where the deliverable is a PR. The query is trustworthy only
once the PKB server's status enum accepts `partial` as a `list_tasks` filter value
— a server that silently matches all tasks instead of erroring on an unrecognised
status returns garbage, not an orphan set — and once client-side task-status
validation permits emitting `partial`, since the server cannot accept a status the
client never sends.

## Fitness rubric

| Dimension               | Excellence looks like                                                                                        | Failure signal                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| Discriminator integrity | A planted bug whose catching test is never written fails the stop as an illegal gap, or is visibly deferred. | A green draft ships with a silent bugged AC and the gate passes.          |
| No-rig discipline       | Clause 3 is enforced by self-cert + honesty floor + reviewer audit.                                          | An implementer built a regex or keyword coverage gate.                    |
| No orphans              | Every `partial` has a live continue task; the loop-closer files one where missing.                           | A `partial` survives a `/daily` cycle with no continue task, un-surfaced. |
| Load relief             | Draft partials stay out of the merge queue; sprawl stays bounded.                                            | Draft sprawl accumulates.                                                 |
| Invariant preservation  | No path, on any surface, by which a `partial` reaches the human approval queue.                              | Any such path exists.                                                     |

## Residual risk

1. **Clause 3 is honesty-bound, not mechanically guaranteed.** By deliberate design,
   the AC→state partition rests on worker self-certification plus the honesty floor
   plus reviewer audit. A worker that lies in _both_ its self-cert and its
   `## Deliberately deferred` section, past a reviewer who does not re-derive the
   ACs, can still launder a defect. The mitigation is the always-on floor and the
   reviewer's own AC re-read — not a gate. This is a residual, not a closure.
2. **The orphan loop-closer is specified, not built.** Draft sprawl is bounded only
   by clause 4 discipline until the server status-enum acceptance, the client-side
   status validation, and the pass itself all land.
3. **Eligibility depends on the promotion log being honestly written** by the
   recording agent. The seam is narrower than worker-declared frontmatter — the
   recorder is pauli at decomposition, under standing independent review — but not
   zero. Auditability is the mitigation, not prevention.
4. **The 7-day idle threshold is a guess**, untuned against field data. First
   production cycles should calibrate it.
