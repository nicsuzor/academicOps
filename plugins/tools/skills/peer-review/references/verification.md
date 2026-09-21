---
title: Verification -- Adversarial Claim Checking
permalink: review-verification
tags: [reference, peer-review, verification]
---

# Verification

Adversarial verification validates draft claims against the source document. Execute as a contextless sub-agent or an explicit serial cold re-read.

## Six Core Techniques

1. **Verbatim-quote sweep**: Grep source text for every quoted string. A null grep is a presumptive **BLOCKER**; applicants easily disprove fabricated or misattributed quotes.
2. **Tool-backed arithmetic**: Recompute totals and sub-totals via calculation tools (`python3 -c "..."`). Never cite an unverified figure.
3. **Documented absence search**: Support claims that a topic is absent by searching terms and documented synonyms across the document.
4. **Inspect original PDF pages**: Read GANTT charts, budget tables, and complex figures directly from PDF pages, as text extractors mangle layouts.
5. **Cross-field consistency**: Cross-check project dates against funding rules, investigator FTE against career stage declarations, and budget text against budget tables.
6. **Self-verify corrections**: Confirm proposed corrections against source data before modifying the draft. If re-derivation is uncertain, remove the critique.

## Claim Classification & Gap Analysis

Classify extracted draft claims:

- **CONFIRMED**: Backed by source text; cite line number and verbatim proof.
- **UNSUPPORTED**: Not found in source; document searched terms and sections.
- **WRONG**: Contradicted by source; cite line number and contradictory quote.

Run independent gap analysis on the source to surface omitted strengths or weaknesses and ensure balanced criterion coverage.

## Severity Ladder

- **BLOCKER**:
  - Fabricated, blended, or missing verbatim quote.
  - Material misattribution of content the applicant did not state.
- **FIX**:
  - Imprecise claims, overstatements (including those favoring the applicant), or typos.
- **NIT**:
  - Minor stylistic polish with no evidential consequence.

Conclude with a summary verdict (e.g., "0 BLOCKER, 2 FIX, 1 NIT -- ready after fixes").

## Applying Findings & Boundary Gate

- **Triage**: Address all verification findings; do not discard items silently.
- **Minimal edits**: Apply surgical edits to preserve surrounding verified context.
- **Boundary rule**: Verification attaches strictly to committed artifacts. Any subsequent text regeneration (voice pass, polishing) requires re-verification of the diff.
