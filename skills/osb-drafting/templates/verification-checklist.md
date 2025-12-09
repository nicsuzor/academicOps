# Citation Verification Checklist

**Case**: [CASE_TITLE]
**Draft Date**: [DATE]
**Verification Date**: [DATE]

---

## Instructions

Complete this checklist after Phase 5 (Recommendations) and before finalizing any draft.

1. Extract all case citations from draft (format: `XX-XXXXXXX` or `XXX-XXXXXXXX`)
2. For each citation, retrieve case data using OSB MCP tools
3. Verify each item against the criteria below
4. Document findings in the appropriate section
5. Quality gate: Draft not complete until 0 items in NEEDS CORRECTION

---

## Citations Extracted

| # | Case ID | Case Name (as cited) | Cited For |
|---|---------|---------------------|-----------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

---

## Verification Criteria

| Check | Criteria | Method |
|-------|----------|--------|
| Case ID exists | Must return valid result | `mcp__osb__get_case_summary(record_id)` |
| Case name matches | Exact or close match to official name | Compare to `case_name` field |
| Quoted text accurate | Exact phrase or valid paraphrase | Search summary, then full document |
| Principle attributed | IRAC/Ratio section supports claim | Check Legal Reasoning section |
| Recommendation accurate | Matches recommendations text and status | Verify recommendation wording |

---

## VERIFIED

| Case ID | Cited Claim | Verification |
|---------|-------------|--------------|
| | | CONFIRMED in [section] |
| | | CONFIRMED in [section] |
| | | CONFIRMED in [section] |

---

## NEEDS CORRECTION

| Case ID | Issue | Draft Says | Actual | Required Fix |
|---------|-------|------------|--------|--------------|
| | | | | |
| | | | | |

---

## UNVERIFIABLE

| Case ID | Quote/Claim | Reason | Action |
|---------|-------------|--------|--------|
| | | Full document needed | Document justification |
| | | | |

---

## Common Error Types

- **Case mislabeling**: Wrong case name for ID (e.g., "COVID lockdowns Brazil" instead of "Claimed COVID Cure")
- **Quote fabrication**: Phrase not found in case text
- **Principle misattribution**: Case doesn't establish the cited holding
- **Recommendation misstatement**: Wrong implementation status or wording

---

## Quality Gate

- [ ] All case IDs verified as existing
- [ ] All case names match official records
- [ ] All direct quotes found in source
- [ ] All attributed principles confirmed in case reasoning
- [ ] All recommendation citations accurate
- [ ] 0 items in NEEDS CORRECTION section
- [ ] All UNVERIFIABLE items documented with justification

**Verification Status**: [ ] PASS / [ ] FAIL

**Verified By**: [NAME/AGENT]
**Date**: [DATE]

---

## Example (Israel-Iran Draft)

### VERIFIED
- **FB-GW8BY1Y3**: Policy "too narrow" / limited to "saying words" - CONFIRMED in summary
- **FB-GW8BY1Y3**: Recommendation 3 (label instead of remove) - CONFIRMED
- **BUN-6AQH31T6**: "core criteria that trigger immediate activation" - CONFIRMED
- **BUN-6AQH31T6**: "even posts from non-influential users" - EXACT MATCH
- **FB-XWJQBU9A**: "imminent harm requires specific contextual analysis" - CONFIRMED

### NEEDS CORRECTION
- **FB-XWJQBU9A**: Case mislabeling
  - Draft says: "COVID lockdowns Brazil"
  - Actual: "Claimed COVID Cure" (France, hydroxychloroquine)
  - Fix: Update case name throughout draft

### UNVERIFIABLE
- **PAO-SABU4P2S**: "overwhelming majority...never reviewed by fact-checkers" - Full document needed
- **FB-E1154YLY**: "appearance of inconsistency" / "differential treatment" - Full document needed
- **BUN-6AQH31T6**: "barriers to creating...AI tools" / "almost a full week" - Full document needed
