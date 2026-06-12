---
title: Verification — adversarial, independent claim-checking
permalink: review-verification
tags: [reference, peer-review, verification]
---

# Verification

This is the highest-value stage and the one a naive draft-then-submit flow lacks. Its power
comes from **independence + re-derivation**: a cold reader who distrusts the draft and
re-checks every claim against the source catches what a self-review never will. Every
high-value catch in the evidence corpus came from here — and specifically from an
independent cold re-read, not from ticking off the draft's own claim list.

**Stance.** _The draft's authors are not to be trusted. Distrust any prior PASS — re-grep
from scratch. Demand proof for every claim._ Run VERIFY as a separate contextless sub-agent
where you can; in serial mode, switch hats forcefully and re-read the source cold, not the
draft.

**Never degrade VERIFY to a citation-checker.** It is a full independent cold re-read with
gap analysis. A citation-checker confirms the draft's own claims line up; a verifier asks
what the draft _missed_ and whether any quoted string is real.

## The six core techniques

1. **Verbatim-quote-existence sweep** — _the single highest-value check._ For every quoted
   string in the draft, grep the source for that exact string. A null grep on a quoted
   phrase is a **presumptive BLOCKER**: a fabricated or blended quote is the one error the
   applicant can disprove by reading their own document. Check the _inverse_ of citation —
   not "is this claim supported?" but "does this quoted string actually exist in source?"
   That inverse test is what a citation-checker skips and what lets a fabricated quote pass
   an earlier "0 WRONG" verdict.

2. **Tool-backed arithmetic** — recompute every total from its components with a calculator
   (`python3 -c "print(...)"`), never mental math. Reconcile sub-totals against the grand
   total (e.g. D1 vs D2 vs D3 vs total). Quote no figure you have not re-derived. Summing to
   the cent catches the typo'd line item and the internal sum error.

3. **Absence-claims via synonym grep** — "the application never addresses X" is only safe if
   you grepped X _and its synonyms_ and documented the terms. State the terms you searched.
   An undocumented absence-claim is an assertion, not a finding.

4. **Read the actual PDF pages** for GANTT charts, budgets, and timelines — `pdftotext`
   mangles tables, so layout-dependent content must be read from the page. This is how a
   GANTT that describes a _different_ project, or a timeline inconsistent with the funding
   window, gets caught.

5. **Internal-contradiction sweep** — cross-check fields against each other: FTE vs
   "retired"/career-stage claims; project dates vs the funding window; reference list vs
   in-text citations; budget narrative vs budget table. Contradictions across fields are
   high-signal and invisible to a single-field read.

6. **Self-verification of your own corrections** — before asserting a correction, verify it.
   The canonical failure is "the correction was itself wrong" (the draft flags the
   application as mistaken, but the application was right and the correction is the
   fabrication). When your re-derivation and the application disagree, re-derive again before
   concluding the application is wrong; prefer deletion over substituting a new unverified
   figure.

## Claim-by-claim classification

Extract every claim the draft makes and classify it:

- **CONFIRMED** — supported; record the line number **and** a verbatim proof-quote.
- **UNSUPPORTED** — not found; say **where you looked** (sections, line ranges, grep terms).
- **WRONG** — contradicted; record the contradicting quote **and** line number.

Then run **independent gap analysis**: read the application cold and list strengths and
weaknesses the draft missed, and check balance across criteria (don't let one criterion get
three paragraphs and another two lines).

## Severity ladder (guard F6)

Classify every finding. The BLOCKER↔FIX boundary is where reviewers disagree, so it is
defined explicitly:

- **BLOCKER** —
  - a **fabricated or wrong verbatim quote** the applicant can check against their own
    document; or
  - a **false content-attribution** in the assessor's paraphrase that a source-checking
    reader would find absent (FIX only if a charitable reading rescues it).
- **FIX** —
  - an overstatement, mischaracterisation, or typo;
  - defensible assessor world-knowledge that is imprecise; or
  - **an overstatement that _favours_ the applicant** — still a FIX, because it mis-evidences
    the score.
- **NIT** — optional polish; no evidential consequence.

End the verification with a one-line **verdict** (e.g. "1 BLOCKER, 3 FIX, 2 NIT — not ready;
re-verify after fixes").

## Where verification runs (guard F7)

Push the techniques **upstream into a pre-"ready" gate** — verbatim-quote grep + AU-spell +
dash-normalise + budget-recompute must pass before a draft is _called_ ready. Keep a
contextless final-check as **confirmation**, not as the first place anyone greps a quote. A
final check that is the _only_ place a quote gets grepped means verification is compensating
for a missing upstream gate.

## After verification: applying the findings (guard F4)

Whoever integrates the findings (the FIX hat) must do the triage itself, not receive a
pre-digested list:

- **Read the full verification report** and confirm the action list is complete — the
  decision of _which_ findings change the draft is the most error-prone step and needs its
  own check.
- **Re-derive every number or quote it lands** — a bad figure in a work order ships
  unchecked otherwise.
- Use the **narrowest possible edit target** (a broad find-replace can destroy a section).
- **Re-read the edited artifact** and confirm each finding is actually present before
  reporting success. Report from the re-read, never from intention.
- Append a short `## Verification round N — applied` changelog; defer (don't silently drop)
  lower-priority items.

## The boundary gate (guard F1)

_"Verified" attaches to a committed artifact, not an idea._ Any regeneration after VERIFY —
voice rewrite, polish, hand-edit — **re-enters verification**. The seams between stages are
where errors enter: a fabricated quote is born when a voice pass promotes a paraphrase into
quote-marks; a correct addition is lost when a later polish drops it. Stamp the verified
commit and re-run the checks on any later diff. On-disk drafts are mutable (guard F8) — the
committed/verified artifact is the record, never a live draft.
