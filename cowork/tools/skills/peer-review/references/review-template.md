---
title: Generic Review Template
permalink: review-template
tags: [template, peer-review]
---

# Generic Review Template

Instantiate this with the criteria, weights, and band descriptors fetched from the current round's handbook (Stage 0). Do **not** hardcode prior-year structure — copy the criteria list verbatim from this round.

This template is deliberately lean: one criterion block, comments plus the evidence located. A reservation trimmed in the voice pass is not appended here — it lives in the one living draft's git history.

```markdown
# {SCHEME} {ROUND} Assessment

**Application ID**: {APPLICATION_ID}
**Candidate / Lead Investigator**: {NAME}
**Institution**: {INSTITUTION}
**Project Title**: {TITLE}
**Level / Career Stage**: {LEVEL}
**Role**: Detailed Assessor | General Assessor / CoE | Collegial reviewer
**Round handbook fetched**: {URL or PKB id, date fetched}
**Min char counts (Detailed only)**: {per criterion} / {overall}
**Deadline**: {DATE}

---

## Criterion 1 — {Name} ({Weight}%)

**Comments** (≥{N} chars).

### Evidence located in application

- {sub-element 1}: {what the application says, with line/section ref}
- …

---

## Criterion 2 — {Name} ({Weight}%)

…

---
```
