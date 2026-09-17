---
title: Reading Notes Format
permalink: reading-notes-format
tags: [reference, peer-review]
---

# Reading Notes Format

Reading notes organize application facts and reviewer hunches for efficient evaluation. They maintain two quarantined layers:

1. **Factual line-mapped layer**: Verifiable claims and locations.
2. **Raw judgment block**: Candid reviewer impressions and hunches (private, never submitted).

## Location

`${ACA_DATA:-~/brain}/reviews/{scheme}/{appid}/YYYYMMDD-reading-notes.md`

## Template

```markdown
---
title: {APPID} -- Reading Notes
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

# {APPID} -- Reading Notes

## Source Map

Text: `{path}` ({N} lines via `pdftotext -layout`).

| Section | Lines | Notes |
| ------- | ----- | ----- |

## Criteria

| # | Criterion | Weight | Sub-elements |
| - | --------- | ------ | ------------ |

## Factual Read-Along (Per Criterion)

### Criterion N -- {Name}

**Location**: {line range}
**Application Claims**:

- {sub-element}: {claim, paraphrased or quoted, with line ref}
  **Flags for Verification `[?]`**:
- L{nnn}: {what to verify}

## Raw Judgment Block (Private -- Never Submitted)

**Top-line read**: {informal, candid initial assessment}
**Primary vulnerability**: {key theory-of-change, construct, or feasibility issue}
**Criterion hunches**:

- {Criterion}: {unvarnished critique}
  **Provisional net call**: {reviewer-owned trajectory}

## Cross-Cutting & Anti-Bias Checks

- Cross-section consistency (budget vs method, timelines, support letters).
- Application-specific bias risks: {e.g. institutional affinity, prestige halo}.
```

## Drafting Rules

- **Layer separation**: Keep factual summaries evidentiary; place subjective critique exclusively in the raw judgment block.
- **Line citations**: Support every factual claim with line numbers.
- **Mark paraphrases**: Never format paraphrased claims as direct quotes.
- **Uncertainty flags**: Use `[?]` to mark items requiring verification, not as speculative assertions.
