---
id: wf-signoff-loop
title: "wf-signoff-loop"
type: template
category: gate
description: The review-until-approval loop the principal runs at a human sign-off gate, over one completed unit, before it may be marked done. Select when human sign-off is the recorded review obligation. Not a step inside a worker's process; no producer runs it over its own output.
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
source: "aops-1e4cbf7e"
---

## What this step does

The review-until-approval loop run **at** a sign-off gate, over one completed unit of work,
before it may be marked done. It is the interior of the heaviest review obligation `brief` can
record on a task.

**Do not select it** as a step composed into a worker's process, and never where the producer
would run it over its own output.

## Slots the invoker fills

No defaults — and a worked example is not a default.

- `<unit>` — the completed unit under sign-off, and the artifact(s) it produced.
- `<record>` — where its working record lives: transcript(s), applicable logs, run output.
- `<class-criteria-source>` — where standards for this _class_ of work are already written down.
- `<task-criteria-source>` — where standards for _this particular_ commission are written down.
- `<verifier>` — the identity that performs step 4. **Constrained, not free:** not the party that
  produced `<unit>`, not anyone whose own work forms part of `<unit>`, and not a continuation of
  the producing session. Where no such identity is available, report that to `<principal>` as a
  blocking gap; never let the producer verify itself.
- `<principal>` — the one person whose approval terminates this loop.

## Core principle

**The loop reaches no verdict of its own.** Steps 1–6 assemble material and judgment; both gates
are crossed by `<principal>` and nobody else. **Silence is not consent.**

Anyone may run steps 1–3 and 5–7, including a reviewer acting for `<principal>`. **Step 4's
assessment is `<verifier>`'s.** No automated check, status, or pipeline result discharges step 4,
and none of them is a verdict.

## The loop — run until approval

### 1. Obtain the primary material

Obtain the actual `<record>` and the **full text** of the artifact(s) `<unit>` produced — not a
summary, not the producer's account. Carry anything unobtainable into the digest as a named gap.

### 2. Obtain and report the acceptance criteria

Retrieve, and reproduce in the digest, both bands: from `<class-criteria-source>`, what any work
of this kind must satisfy; from `<task-criteria-source>`, what this particular commission asked
for. Keep them distinct — they fail differently.

**Criteria are obtained, never invented.** Quote each and name its source. Where a source yields
nothing, that absence is itself a reportable finding for `<principal>`, never a licence to
substitute the reviewer's own standard under the same heading. Settle criteria before examining
evidence.

### 3. Review the record of the node that actually did the work

**3a. Selection.** Walk down from the coordinating node that accepted the commission until you
reach the first node whose record shows it **performing** the work — producing, changing, running
— rather than **delegating** it. That node's record is the review target. Where several siblings
each performed work, **each such highest performer is a target**, and each is reviewed.

**3b. Review it** for limitations, errors, problems, refusals, retries, silent scope reduction,
and anything the performer flagged that did not survive into what was reported upward.

**3c. When the record is missing.** If it is absent, truncated, or unobtainable, say so and name
what becomes unverifiable. Never reconstruct it from the artifact, never accept the coordinator's
summary instead, never skip it silently.

### 4. Assess artifact, record, and logs against the criteria and the excellence bar

Two readings, reported separately: conformance against the criteria obtained at step 2, and
quality against `<principal>`'s excellence bar. Conformant but unimpressive is a finding, not a
pass.

**`<verifier>` performs this assessment, and performs it by exercising `<unit>`.**

- **Independent of the production.** `<verifier>` did not make `<unit>` and holds no stake in its
  standing. The producer's own say-so is material for step 1, never verification.
- **Exercising, not re-reading.** `<verifier>` puts the artifact to the use its criteria describe
  and observes what actually happens — operating it, following its procedure, re-deriving a
  result it claims, reading it as its intended audience would, checking that a source it cites
  says what it is cited for. What the exercise _is_ comes from `<class-criteria-source>` and the
  artifact's own nature.

**Verification completes before the digest is composed** — not alongside it, not "pending final
checks", not deferred to the next round. Where verification genuinely cannot be completed, carry
it to step 5 as a named gap and mark every proposition resting on it unverified.

### 5. Present the evidence digest — **Gate A**

**Bottom line first.** The digest opens with the verdict `<verifier>` reached and the decision
`<principal>` is being asked to make. **The digest's open question is its literal last line,
restated fresh each round** — or is put through a direct question surface. Never buried
mid-digest, and never a back-reference to an earlier unanswered ask.

**Every proposition carries a verbatim excerpt** — inline, quoted, and sufficient for
`<principal>` to reach his **own** verdict on it **without opening `<record>` or following
anything**. Evidence forms include, non-exhaustively: quoted text from the artifact or the
record; `path:line`; a command with its observed output; an exit code; the quoted criterion being
applied.

**The digest names `<verifier>`, states how they were independent of the production, and says
what they exercised.**

**Verification and excerpts are both required, every round; neither substitutes for the other.**
The excerpts are how `<principal>` audits the verification. A digest failing either half is
rejected and redone before it reaches `<principal>`.

**On length.** This digest is the sanctioned exception to the terse default, and it is an
exception **for excerpts only** — never for narration or prose restating what an excerpt already
shows.

**Gate A — the principal assesses the digest himself.**

- **Approved, no defects → the loop terminates here.** That approval is the sign-off; `<unit>`
  may be marked done.
- **Defects confirmed by him → step 6.**
- **No reply → nothing is approved.**

### 6. Propose a remediation plan — **Gate B**

Per confirmed defect: what is wrong, what would fix it, who would do it, and how the fix will be
evidenced next round. Where a defect turns on a choice of method nobody specified, **methodology
belongs to the researcher** — surface the choice _in the plan_ for `<principal>`; neither
reviewer nor worker decides it or picks a default.

**One ask per logical unit.** Every confirmed defect from this round goes into a single Gate B
ask, not a serial trickle of small approvals for pieces of the same work. A defect found after
the plan is composed but before dispatch joins that plan; it does not open a second ask.

**Failure to converge is itself a finding.** Where a defect survives remediation, or rounds
accumulate without the evidence improving, name that pattern **at the top of the next digest** —
what has not converged, over how many rounds, and what `<verifier>` takes to be causing it — and
put it to `<principal>` as its own proposition with its own excerpts. This adds no cap and no
exit: the loop still ends only at Gate A approval.

**Gate B — the principal approves the plan before anything is dispatched.** Gate A settles what
is _true_ about the work; Gate B authorises what will be _done_ about it. Approval of one is
never approval of the other.

- **Approved → step 7.**
- **Rejected or amended → revise and re-present at Gate B.** Nothing dispatches meanwhile.

### 7. Dispatch workers on the approved remediation plan

Only the approved items, only after Gate B. **Research data is immutable** — remediation workers
never modify, reformat, convert, or "fix" the underlying research material; where a remediation
appears to require it, the worker halts and reports.

**Then re-enter at step 1**, evidence obtained afresh: new record, full artifact text again,
`<verifier>` exercising the changed artifact again before anything is composed, new digest. **The
prior digest is stale the moment a worker touches `<unit>`** and may not be re-presented,
patched, or amended in place.

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

Door-type belongs to the act dispatched at step 7, judged there. This loop's termination is the
ship gate: nothing is marked done, circulated, sent, or published ahead of Gate A approval.
Prefer over-verification.
