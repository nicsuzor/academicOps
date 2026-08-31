---
id: wf-signoff-loop
title: "wf-signoff-loop"
type: template
created: 2026-08-18T02:55:48.170276131+00:00
modified: 2026-08-18T02:55:48.170276131+00:00
last_modified: 2026-08-18T02:55:48.170278295+00:00
alias:
  - "wf-signoff-loop-wf-signoff-loop"
  - "wf-signoff-loop"
permalink: wf-signoff-loop
tags:
  - wf-template
  - workflow
  - sign-off
  - review
  - restored-from-git
source: "aops-1e4cbf7e"
---

> **Restored 2026-08-18 from git `df9969164:notes/wf-signoff-loop.md` (2026-08-06 13:36 UTC), the last good revision.**
> This node was overwritten on 2026-08-11 (`3dc23d2e3`, 241 lines deleted, 6 inserted) with a session status dump, and deleted on that basis 2026-08-18. The deletion was wrong: the original is authored governance doctrine and was fully recoverable. Provenance and the correction record: [[note_signoff_loop_forensic]].

## What this step does

The review-until-approval loop the principal runs **at** a sign-off gate, over one completed unit
of work, before it may be marked done. Human sign-off is the heaviest review obligation `brief`
can record on a task, and this template is the _interior_ of that obligation. It is **not** a step
composed into a worker's process, and no producer runs it over its own output.

## Slots the invoker fills

No defaults — and a worked example is not a default.

- `<unit>` — the completed unit under sign-off, and the artifact(s) it produced.
- `<record>` — where its working record lives: transcript(s), applicable logs, run output.
- `<class-criteria-source>` — where standards for this _class_ of work are already written down.
- `<task-criteria-source>` — where standards for _this particular_ commission are written down.
- `<verifier>` — the identity that performs step 4. **Constrained, not free:** not the party that
  produced `<unit>`, not anyone whose own work forms part of `<unit>`, and not a continuation of
  the producing session. Where no such identity is available, that is reported to `<principal>` as
  a blocking gap — never worked around by letting the producer verify itself.
- `<principal>` — the one person whose approval terminates this loop.

## Core principle

**The loop reaches no verdict of its own.** Steps 1–6 assemble material and judgment; both gates are
crossed by `<principal>` and nobody else. Operating the loop never confers power to end it.
**Silence is not consent.**

**Operating it is nonetheless not open to everyone.** Anyone may run steps 1–3 and 5–7, including a
reviewer acting for `<principal>` — but **step 4's assessment is `<verifier>`'s**, and `<verifier>`
is independent of the production of `<unit>` by construction. A party close to the work may fetch
material for this loop; it may not judge it. That independence is a property of _who_ judges and
_what they do_, never of a mechanism: no automated check, status, or pipeline result discharges
step 4, and none of them is a verdict.

## The loop — run until approval

### 1. Obtain the primary material

Obtain the actual `<record>` and the **full text** of the artifact(s) `<unit>` produced — not a
summary, not the producer's account of them. Anything unobtainable is carried into the digest as a
named gap. This loop reads the working record by design; lenses that deliberately exclude it —
[[wf-boundary-review]] checks contract and handback, **never the transcript** — are separate passes
this one does not replace.

### 2. Obtain and report the acceptance criteria

Retrieve, and reproduce in the digest, both bands: from `<class-criteria-source>`, what any work of
this kind must satisfy; from `<task-criteria-source>`, what this particular commission asked for.
Keep them distinct — they fail differently.

**Criteria are obtained, never invented.** Quote each and name its source. Where a source yields
nothing, **the absence is itself a reportable finding** for `<principal>` — not a licence to
substitute the reviewer's own standard under the same heading. Criteria are settled before the
evidence is examined.

### 3. Review the record of the node that actually did the work

**3a. Selection — which record to pull.** Walk down from the coordinating node that accepted the
commission until you reach the first node whose record shows it **performing** the work —
producing, changing, running — rather than **delegating** it. That node's record is the review
target. Where several siblings each performed work, **each such highest performer is a target**,
and each is reviewed. Not the coordinator above it (its record evidences delegation), and not every
leaf below it (those evidence fragments, not the unit).

**3b. Review it** for limitations, errors, problems, refusals, retries, silent scope reduction, and
anything the performer flagged that did not survive into what was reported upward.

**3c. When the record is missing.** If it is absent, truncated, or unobtainable, say so and name
what becomes unverifiable. Never reconstruct it from the artifact, never accept the coordinator's
summary instead, never skip it silently — an unreviewable performance is itself a finding.

### 4. Assess artifact, record, and logs against the criteria and the excellence bar

Two readings, reported separately: conformance against the criteria obtained at step 2, and quality
against `<principal>`'s excellence bar. Conformant but unimpressive is a finding, not a pass.

**`<verifier>` performs this assessment, and performs it by exercising `<unit>`.** Independence has
two halves and both are checkable:

- **Independent of the production.** `<verifier>` did not make `<unit>` and holds no stake in its
  standing. The producer's own say-so — however confident, however detailed — is material for step
  1. It is never verification.
- **Exercising, not re-reading.** `<verifier>` puts the artifact to the use its criteria describe
  and observes what actually happens — operating it, following its procedure, re-deriving a result
  it claims, reading it as its intended audience would, checking that a source it cites says what
  it is cited for. Re-reading the producer's account of having checked it is not exercising it.
  What the exercise _is_ comes from `<class-criteria-source>` and the artifact's own nature; this
  template names no form of exercise as the form, because none is general.

**Verification completes before the digest is composed.** Not alongside it, not "pending final
checks", not deferred to the next round. `<principal>`'s crossing at Gate A is a final assessment
of something already exercised, not the first real check anyone has run on it. Where verification
genuinely cannot be completed, that is carried to step 5 as a named gap and every proposition
resting on it is marked unverified — it is never quietly presented as though it had been.

### 5. Present the evidence digest — **Gate A**

**Bottom line first.** The digest opens with the verdict `<verifier>` reached and the decision
`<principal>` is being asked to make. Everything after that is the evidence for it. **The digest's
open question is its literal last line, restated fresh each round** — or is put through a direct
question surface. It is never buried mid-digest, and it never refers back to an earlier unanswered
ask: re-asking is this loop's job, not `<principal>`'s to recall.

**Every proposition carries a verbatim excerpt** — inline, quoted, and sufficient for `<principal>`
to reach his **own** verdict on it **without opening `<record>` or following anything**. Evidence
forms include, non-exhaustively: quoted text from the artifact or the record; `path:line`; a
command with its observed output; an exit code; the quoted criterion being applied. Pick the form
that makes the proposition checkable.

**The digest names `<verifier>`, states how they were independent of the production, and says what
they exercised** — not merely that a check occurred.

**Verification and excerpts are both required; neither substitutes for the other.** The obvious
misreading is that work verified in advance no longer needs its evidence shown. It is backwards:
**the excerpts are how `<principal>` audits the verification.** Drop them and the verification
becomes one more say-so, differing from the producer's only in whose it is. And the excerpts are
equally not a way to hand `<principal>` unverified work with the checking attached for him to do.
Pre-verification without excerpts, and excerpts without pre-verification, are the same defect from
opposite sides. Both, every round. A digest failing either half is rejected and redone before it
reaches `<principal>` — it is a defect in this loop's execution, not a style preference.

**On length.** Terse and bottom-line-first is the standing default; this digest is the sanctioned
high-stakes exception to it, and it is an exception **for excerpts only**. Its length is spent on
evidence `<principal>` assesses for himself — never on narration, or prose restating what an
excerpt already shows. The provenance the output contract requires — which record, which verifier,
what they exercised — is not narration; it is what makes an excerpt checkable.
`specs/enforcement/sign-off.md:24-29` sets the shape: a "one-page prose brief in which every
delivered/checked claim carries a resolvable pointer ... or a stated failure reason", and approving
"on the strength of the brief's rhetorical shape rather than checking its claims" is not sign-off.
Here the pointer is stronger — the excerpt, inline.

**Gate A — the principal assesses the digest himself.**

- **Approved, no defects → the loop terminates here.** That approval is the sign-off; `<unit>` may
  be marked done.
- **Defects confirmed by him → step 6.**
- **No reply → nothing is approved.** No reviewer's or worker's own assessment that the work is
  good enough substitutes for this crossing — `<verifier>`'s independent verification is what makes
  the digest worth his attention, never a stand-in for his crossing of it.

### 6. Propose a remediation plan — **Gate B**

Per confirmed defect: what is wrong, what would fix it, who would do it, and how the fix will be
evidenced next round. Where a defect turns on a choice of method nobody specified, **"Methodology
belongs to the researcher"** — surface the choice _in the plan_ for `<principal>`; neither reviewer
nor worker decides it or picks a default.

**One ask per logical unit — the round's defects consolidate into a single plan.** Every confirmed
defect from this round goes into one Gate B ask, not a serial trickle of small approvals for pieces
of the same work. `<principal>`'s attention is the scarce input this loop spends, and spending it
three times on what could have been asked once is a defect in the loop's operation, not diligence.
A defect found after the plan is composed but before dispatch joins that plan; it does not open a
second ask.

**Failure to converge is itself a finding, not another quiet round.** Where a defect survives
remediation, or rounds accumulate without the evidence improving, that pattern is named **at the
top of the next digest** — what has not converged, over how many rounds, and what `<verifier>`
takes to be causing it — and it is put to `<principal>` as its own proposition, with its own
excerpts, like any other. It is never absorbed by dispatching one more silent round. **This adds no
cap and no exit:** the loop still ends only at Gate A approval, and a non-convergence finding is
information for `<principal>` to act on, never a termination.

**Gate B — the principal approves the plan before anything is dispatched.** A distinct crossing
from Gate A: Gate A settles what is _true_ about the work, Gate B authorises what will be _done_
about it. Approval of one is never approval of the other.

- **Approved → step 7.**
- **Rejected or amended → revise and re-present at Gate B.** Nothing dispatches meanwhile.

### 7. Dispatch workers on the approved remediation plan

Only the approved items, only after Gate B. **"Research data is immutable"** — remediation workers
never modify, reformat, convert, or "fix" the underlying research material; where a remediation
appears to require it, the worker halts and reports.

**Then re-enter at step 1**, evidence obtained afresh: new record, full artifact text again,
`<verifier>` exercising the changed artifact again before anything is composed, new digest. **The
prior digest is stale the moment a worker touches `<unit>`** and may not be re-presented, patched,
or amended in place.

## Output contract

Each round produces **one** digest, in this order:

1. the bottom line — `<verifier>`'s verdict and the decision `<principal>` is being asked for;
2. any failure to converge across rounds, named as its own proposition;
3. criteria obtained and their sources, or the named absence;
4. the record selected at 3a and why;
5. `<verifier>`, how they were independent of the production, and what they exercised;
6. every proposition with its inline verbatim excerpt;
7. what could not be obtained, and anything left unverified, named;
8. either **one consolidated remediation plan** for Gate B, or nothing further, pending Gate A;
9. last line: the open question, restated fresh.

## Declared stakes

**Invoked, not asserted.** This is `<principal>`'s review of work made for him, at a gate he (or his
standing instruction) places — placing a gate is never crossing it — not an agent seeking authority
for a reversible act, the `exercise-authority` failure named in `lib/axioms/one-way-door.md`.
Door-type belongs to the act dispatched at step 7, judged there.

Doctrine at `plugins/ida/agents/ida.md:27,32,33` binds every round and bites hardest
at steps 6–7: research data is immutable; methodology belongs to the researcher; and "**Nothing
externally visible ships without explicit sign-off**" — **this loop's termination _is_ that ship
gate.** Nothing is marked done, circulated, sent, or published ahead of Gate A approval. Prefer
over-verification.

## Anti-patterns

- A digest of conclusions, findings, or verdicts with no verbatim excerpt under them.
- Step 4 performed by the party that produced `<unit>`, or by a continuation of the producing
  session — including where it is dressed as a fresh pass over one's own output.
- Verifying by re-reading the producer's account of the work instead of exercising the artifact.
- Sending the digest with verification still in flight, or letting `<principal>` be the first
  identity to actually check the work.
- Dropping excerpts because the work was verified in advance — the excerpts are how he audits the
  verification.
- Burying the open question mid-digest, or referring back to an earlier unanswered ask instead of
  restating it fresh.
- Spending the digest's length on narration rather than on excerpts.
