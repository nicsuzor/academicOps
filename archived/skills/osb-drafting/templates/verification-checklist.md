---
title: Citation Verification Checklist
type: spec
category: template
permalink: skills/osb-drafting/templates/verification-checklist
description: Checklist for verifying case citations and ensuring factual accuracy in OSB decision drafts
tags: [template, osb-drafting, verification, qa, checklist]
---

# Citation Verification Checklist

**Case**: [CASE_TITLE]
**Draft Date**: [DATE]
**Verification Date**: [DATE]

## Instructions

Complete this checklist after Phase 5 (Recommendations) and before finalizing any draft.

1. Extract all case citations from draft (format: `XX-XXXXXXX` or `XXX-XXXXXXXX`)
2. For each citation, **retrieve full document text** using `mcp__osb__get_document(record_id, include_full_text=true)`
3. Verify each quoted phrase exists **verbatim in full text**
4. Document findings in the appropriate section
5. Quality gate: Draft not complete until all citations verified and 0 items in NEEDS CORRECTION

**Why full text is required**: Summaries are AI-generated abstractions. Only the full decision text can verify exact quotes, context, and nuanced reasoning.

## Citations Extracted

| # | Case ID | Case Name (as cited) | Cited For |
| - | ------- | -------------------- | --------- |
| 1 |         |                      |           |
| 2 |         |                      |           |
| 3 |         |                      |           |
| 4 |         |                      |           |
| 5 |         |                      |           |

## Verification Criteria

| Check                     | Criteria                                 | Method                                                      |
| ------------------------- | ---------------------------------------- | ----------------------------------------------------------- |
| Case ID exists            | Must return valid result                 | `mcp__osb__get_document(record_id, include_full_text=true)` |
| Case name matches         | Exact or close match to official name    | Compare to document title                                   |
| Quoted text accurate      | **Exact phrase in full document**        | Search full text for quoted string                          |
| Principle attributed      | Legal reasoning section supports claim   | Read ratio/reasoning in full text                           |
| Recommendation accurate   | Verbatim match to recommendations        | Check recommendations section                               |
| **Quote originates here** | Quote is FROM this case, not cited BY it | Check for "Board found in [other case]" pattern             |

**CRITICAL**: For each quoted phrase, run `mcp__osb__search(query="[exact phrase]")` to find where it actually originates. Catches citation chain errors where Case A cites Case B but draft attributes quote to Case A.

## VERIFIED

| Case ID | Cited Claim | Verification                         |
| ------- | ----------- | ------------------------------------ |
|         |             | CONFIRMED at [location in full text] |
|         |             | CONFIRMED at [location in full text] |
|         |             | CONFIRMED at [location in full text] |

## NEEDS CORRECTION

| Case ID | Issue | Draft Says | Actual Text | Required Fix |
| ------- | ----- | ---------- | ----------- | ------------ |
|         |       |            |             |              |
|         |       |            |             |              |

## Common Error Types

- **Case mislabeling**: Wrong case name for ID (e.g., "COVID lockdowns Brazil" instead of "Claimed COVID Cure")
- **Quote fabrication**: Phrase not found in full case text
- **Principle misattribution**: Case doesn't establish the cited holding
- **Recommendation misstatement**: Wrong implementation status or wording
- **Citation chain error**: Quote is FROM Case B but draft attributes to Case A (which merely cites Case B). Look for patterns like "The Board found in [other case]..." - the principle originates from the cited case.

## Quality Gate

- [ ] All case IDs verified via full document retrieval
- [ ] All case names match official records
- [ ] All direct quotes found **verbatim** in full document text
- [ ] All attributed principles confirmed in case reasoning
- [ ] All recommendation citations accurate
- [ ] 0 items in NEEDS CORRECTION section

**Verification Status**: [ ] PASS / [ ] FAIL

**Verified By**: [NAME/AGENT]
**Date**: [DATE]

## Example (Israel-Iran Draft)

### VERIFIED

- **FB-GW8BY1Y3**: Policy "too narrow" / limited to "saying words" - CONFIRMED in full decision text
- **FB-GW8BY1Y3**: Recommendation 3 (label instead of remove) - CONFIRMED verbatim
- **BUN-6AQH31T6**: "core criteria that trigger immediate activation" - EXACT MATCH in recommendations
- **BUN-6AQH31T6**: "even posts from non-influential users" - EXACT MATCH in reasoning
- **FB-XWJQBU9A**: "imminent harm requires specific contextual analysis" - CONFIRMED in ratio

### NEEDS CORRECTION

- **FB-XWJQBU9A**: Case mislabeling
  - Draft says: "COVID lockdowns Brazil"
  - Actual text: "Claimed COVID cure" (France, hydroxychloroquine)
  - Fix: Update case name throughout draft
