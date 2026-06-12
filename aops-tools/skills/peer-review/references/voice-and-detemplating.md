---
title: Voice & De-templating
permalink: voice-and-detemplating
tags: [reference, peer-review, voice, detemplating]
---

# Voice & De-templating

Stage 3 turns a _verified_ draft into clean, signable prose in the academic's own voice,
and — when there is more than one review in a round — strips the recurring formulas that
read as a template (and invite suspicion of AI drafting, which most schemes prohibit in
assessor text). Two distinct jobs: **match the voice** (per review) and **de-template the
set** (whole round).

## Two registers

A review carries information at two registers, and they must not be confused:

- **Prep register** — maximally specific: line refs, quotes, numbers, the raw judgement
  block. This is the working layer (the reading notes); it never goes to the platform as-is.
- **Final register** — **generally-assertable from one careful reading without re-checking
  any single number.** This is what makes the prose _signable_: the academic can stand
  behind every sentence from one read.

The test for a final-register sentence: _could the academic assert this confidently from one
careful reading, without checking a figure?_ If it depends on a number the reader would have
to re-verify, it belongs in prep, not the final text.

Everything cut in moving from prep to final is preserved in **git history** of the one
living draft — not a carried-forward appendix, not `-v2`/`-v3` files. The git record is also
what lets verification distinguish _consciously parked_ from _accidentally lost_.

## Render boldly — the one voice rule that subsumes the rest

The agent's systematic failure mode is **under-assertion** — softening the academic's
position, dropping hedged hunches, cushioning ethical points. The single rule:

> **Render the academic's stated position faithfully and boldly. Raise register worries in
> conversation, never by silent substitution.**

If a phrasing seems too strong, _say so in chat_ and let the academic decide — do not quietly
downgrade "alt-right" to "extremist" or "largely poor" in place of a blunter judgement. The
academic owns the calibration; the agent's job is to render it, not to pre-soften it.

## Voice onboarding — the reflection-on-diff loop

A static style guide alone is **not enough** to reproduce a voice. The voice emerges from a
short feedback loop over the first several reviews:

1. The agent drafts the final-register prose.
2. The academic edits it (offline).
3. The agent **diffs** the human-final against its own draft.
4. The agent **codifies the delta** — the consistent edits — into the academic's voice file,
   `${ACA_DATA}/STYLE.md` (the general style guide) and/or a review-specific
   `{academic}-style.md`.

A few cycles of this sharpens the voice far faster than any one-shot prompt. Point the loop
at `${ACA_DATA}/STYLE.md` as the authoritative general style guide where one exists, and
extend it per academic. **Never hardcode one academic's voice as the default** — ship the
loop and a _generic_ starter, and let each academic train their own.

## De-templating — a whole-set operation

A signature phrase used **once** is voice; the **same** phrase used across six reviews in
one panel is a **fingerprint**. Fingerprints only exist _across_ documents, so this pass runs
over the **entire round's set** at once, after verification, before the academic's own
rewrite. (A lone-review user gets the within-review intensifier diet but not the
cross-document fingerprint guard — that's expected, not a gap.)

### Procedure

1. **Census.** Grep the full set and count, per review, every recurring pivot formula. Build
   the census from _your own_ drafts — the tics are whatever _you_ (or the agent in your
   voice) over-use; do not import another academic's list. Common **generic** offenders to
   seed the census:
   - Stock review pivots: "I have some reservations about…", "I am not (yet) persuaded
     that…", "the application would be stronger if…", "this raises the question of…",
     "it would benefit from…".
   - Asserted-not-X scaffolds: "asserted rather than demonstrated / designed / established".
   - LLM tells: "delve", "crucial", "landscape", "moreover", "furthermore", "it is worth
     noting that", "robust", "nuanced", "multifaceted".
   - Recycled section openers (every Feasibility section opening the same way).
   - Intensifiers: "genuinely", "significant", "severe", "exceptional", "standout".

2. **Budget.** A signature phrase appears **at most once across the whole set**. Generic
   connectives ("However", "That said") are exempt — but vary section openers across reviews.

3. **Two-tier rewrite — mechanism over synonym.** De-templating is _not_ "never thesaurus-swap":
   - **Re-mechanise** the load-bearing critique sentences: delete the scaffold and lead with
     the specific mechanism. "I have some reservations about the team's capacity" →
     "{N} of the {M} investigators hold concurrent grants ending mid-project (refs)". The
     strongest sentences quote the application, then judge it in few words.
   - **Light synonym / connective de-dup** is acceptable in **low-stakes praise** positions.
     Name both tiers so the rule isn't read as a blanket ban on rewording.

4. **Preserve exactly:**
   - All pin cites, line references, and quoted application text — never altered, never dropped.
   - **Calibration** — rewording must not strengthen or soften any judgement.
   - Concede-then-qualify structure, including engagement with the application's self-defence.
   - Constructive counter-offers (what would make the application stronger).

5. **One weighting sentence per review** — the panel should know which concern you weight
   most — **worded differently in each review of the set**. Bound it: synthesise the
   weighting sentence **only by promoting the concern the review's own notes already name
   largest**; never manufacture a new ranking the notes don't support.

6. **Re-scan for new fingerprints.** The fix introduces its own uniformity (e.g. every review
   now opens Feasibility with a quote). Re-run the census; break any fresh pattern.

7. **Machine-check parity.** Verify pin-cite / quote counts are **unchanged** by the pass
   (count before and after — they must match). This is a mechanical gate, not a judgement.

8. **Calibration-notes report.** List every place the pass was tempted to over-firm or
   over-soft and rolled back. This makes the academic's QA take minutes instead of a full
   re-read.
