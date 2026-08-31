---
title: Fact and Source Verification
type: template
category: gate
description: Verify factual assertions, empirical numbers, and literature citations against authoritative primary sources. Select when validating research drafts, reports, or claims. Not for unit testing code (use `tdd`).
tags: [fact-check, citations, empirical, verification, gate]
---

# Gate: Fact and Source Verification

Systematic verification of claims, quotes, numbers, and bibliographic citations against primary sources.

## 1. Claim Identification

- Extract load-bearing factual assertions, statistical figures, and literature citations from `<draft-document>`.
- Create a claim roster mapping each assertion to its location in the text.

## 2. Primary Source Retrieval

- Retrieve the original source texts, datasets, or documentation corresponding to each cited claim.
- Locate the verbatim passage or data point in the primary source.

## 3. Evidence Audit

- Classify each claim:
  - `VERIFIED`: Exact match with primary source; citation accurate.
  - `MISATTRIBUTED`: Claim true but source cited incorrectly.
  - `CONTRADICTED`: Claim conflicts with primary source data.
  - `UNSUPPORTED`: Source does not contain sufficient evidence for claim.

## 4. Remediation

- Correct inaccurate claims, update citations, or remove unsupported statements in `<draft-document>`.

## Exit Condition

100% of load-bearing claims verified against primary sources.
