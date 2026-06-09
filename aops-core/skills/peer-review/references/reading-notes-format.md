---
title: Reading Notes Format
permalink: reading-notes-format
tags: [reference, peer-review]
---

# Reading Notes Format

The reading notes are the document the user reads alongside the source PDF/text during the in-depth pass. They are not the assessment. Their job is to make the read efficient: pointers to the right place, factual extracts, flags for re-read — **and** to capture the reviewer's raw, forming judgement before it is tidied.

The notes carry **two layers, deliberately separated** (see [[voice-and-detemplating]] on the two registers):

1. a **factual, line-mapped** layer (where to look + what the application states, line-cited); and
2. a **raw judgement block** — the reviewer's actual hunches and reservations, kept verbatim and never sanitised, quarantined from any submission text.

The raw judgement block is **first-class**, not a contaminant. In practice it is where the real assessment forms: a blunt note like "this claim ignores the obvious counter-literature" becomes the spine of a criterion critique. Keep it candid; do not pre-soften it into blandness. It never goes to the platform — it feeds the verified draft, which is then voice-matched.

## Location

`${ACA_DATA:-~/brain}/reviews/{scheme}/{appid}/YYYYMMDD-reading-notes.md`.

## Structure

````markdown
---
title: {APPID} — Reading Notes
scheme: {SCHEME}
application_id: {APPID}
candidate: {NAME}
admin_org: {ORG}
project_title: "{TITLE}"
total_budget: {AMOUNT}
role: detailed-assessor | general-assessor | college-of-experts | collegial
created: {DATE}
status: initial-read | re-read | drafting | submitted
---

# {APPID} — Reading Notes

> One-line context: role, deadline, anything unusual about this assignment.

## Source map

Working text: `{path}` ({N} lines, line-numbered via `pdftotext -layout`).

| Section | Lines | Notes |
| ------- | ----- | ----- |
| ...     | ...   | ...   |

## Criteria for this round

(Pulled from {handbook id / URL}, fetched {date}. Verify against current.)

| #   | Criterion | Weight | Sub-elements |
| --- | --------- | ------ | ------------ |
| ... | ...       | ...    | ...          |

## Read-along: facts per criterion

For each criterion, a **factual** account of what the application claims, with line refs. Keep this layer evidentiary — what the application states, where — so it stays checkable in seconds. Evaluation lives in the raw judgement block (below) and the drafted comments, not interleaved here; keeping the factual map clean is what lets verification re-check it fast. **Mark paraphrase as paraphrase** — never write a phrase here that a downstream reader could mistake for a quotable string from the application.

### Criterion N — {Name}

**Where to look**: {line range}.

**What the application states**

- {sub-element}: {extracted claim, paraphrased or quoted, with line ref}
- ...

**Open questions / `[?]` flags for re-read**

- L{nnn}: {what to verify or check}
- ...

(Repeat for each criterion.)

## Raw judgement block

The reviewer's actual, forming assessment — verbatim, candid, **never tidied**. This is a first-class element, quarantined from submission text. Capture per criterion or as a single top-line read; candour is the point.

```markdown
## Raw judgement (private — never submitted)

**Top-line read**: {blunt first impression — informal, candid}.

**Largest analytical vulnerability**: {the single biggest theory-of-change / construct / feasibility problem — see [[review-probes]]}.

**Per criterion (hunches)**:

- {Criterion}: {the real reservation, in your own words, even if unpolished}.

**Net call (provisional, reviewer-owned)**: {where this is heading and why}.
```
````

These notes feed the **verified draft** (which strips anything not source-anchored), then the voice-match pass. They are not the assessment and never go to the platform.

## Cross-cutting flags

Things that don't fit one criterion but matter:

- Cross-references between sections (e.g. budget claim vs. method claim)
- Internal inconsistencies
- Missing letters of support, missing add-on declarations
- Dates / placeholder text / typos that signal proofing
- ROPE / opportunity-relative considerations the assessor should weigh

## Anti-bias check (named for this application)

Two or three concrete bias risks for _this_ application:

- {e.g. "candidate at my prior institution — check affinity"}
- {e.g. "strong LoS; check anchoring"}

## Next step

What the workflow says to do next, instantiated for this case.

## Tone rules for reading notes

- **Keep the two layers separate.** The factual layer stays evidentiary ("the application proposes 20 participants over 2 weeks"); the evaluative read ("the sample looks small for the claim") goes in the raw judgement block — *not* mixed into the factual map. This is a separation of layers, **not** a ban on judgement: the old "factual-only, no evaluative" rule was wrong, because the raw block is where the assessment actually forms.
- **Cite line numbers.** Every factual claim should be checkable in 5 seconds.
- **Tag uncertainty as `[?]`** — and never use `[?]` to dress a guess as a fact. A flag is "verify this", not licence to assert.
- **Use paraphrase over long quotes in the factual layer, and mark it as paraphrase.** Quotes pull the eye out of the source; paraphrase + line ref keeps it in. Never write a paraphrase a downstream reader could mistake for a verbatim string.
- **No restatement-in-disguise.** If a paragraph of notes just retells the application, cut it.
