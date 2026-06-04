---
title: Reading Notes Format
permalink: reading-notes-format
tags: [reference, peer-review]
---

# Reading Notes Format

The reading notes are the document the user reads alongside the source PDF/text during the in-depth pass. They are not the assessment. Their job is to make the read efficient: pointers to the right place, factual extracts, flags for re-read.

## Location

`~/brain/reviews/{scheme}/{appid}/YYYYMMDD-reading-notes.md` (or `${ACA_DATA}/reviews/...` if `ACA_DATA` set).

## Structure

```markdown
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

For each criterion, a **factual** account of what the application claims, with line refs. No "good", "weak", "strong", "concerning". Just what's there. Judgment goes in step 5 of the workflow, not here.

### Criterion N — {Name}

**Where to look**: {line range}.

**What the application states**

- {sub-element}: {extracted claim, paraphrased or quoted, with line ref}
- ...

**Open questions / `[?]` flags for re-read**

- L{nnn}: {what to verify or check}
- ...

(Repeat for each criterion.)

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
```

## Tone rules for reading notes

- **Factual, not evaluative.** "The application proposes 20 participants over 2 weeks" — not "the sample is small". Save evaluation for the assessment file.
- **Cite line numbers.** Every factual claim should be checkable in 5 seconds.
- **Tag uncertainty as `[?]`.** Future-you will thank present-you.
- **Use paraphrase over long quotes.** Quotes pull the user's eye out of the source; paraphrase + line ref keeps them in it.
- **No restatement-in-disguise.** If a paragraph of notes just retells the application, cut it.
