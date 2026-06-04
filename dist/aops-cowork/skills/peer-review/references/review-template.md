---
title: Generic Review Template
permalink: review-template
tags: [template, peer-review]
---

# Generic Review Template

Instantiate this with the criteria, weights, and band descriptors fetched from the current round's handbook (workflow step 2). Do **not** hardcode prior-year structure — copy the criteria list verbatim from this round.

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

## Criteria summary (this round)

| # | Criterion | Weight | Sub-elements            |
| - | --------- | ------ | ----------------------- |
| 1 | {Name}    | {%}    | {bulleted sub-elements} |
| 2 | …         | …      | …                       |
| … | …         | …      | …                       |

Add-on criteria triggered (if any): {e.g. ARC Indigenous research; medical research statement}

Scoring scale: {e.g. A–E; band descriptors as fetched}

---

## Criterion 1 — {Name} ({Weight}%)

### Evidence located in application

- {sub-element 1}: {what the application says, with line/section ref}
- …

### Strengths

-

### Weaknesses / gaps / concerns

-

**Score**: [ ] A | [ ] B | [ ] C | [ ] D | [ ] E (or numeric per scheme)

**Comments** (≥{N} chars):

---

## Criterion 2 — {Name} ({Weight}%)

…

---

## Overall

**Overall score**: [ ]

**Overall comments** (≥{N} chars):

---

## Pre-submit checklist

- [ ] Each criterion comment cites specific application content
- [ ] Scores aligned with comment text
- [ ] Char minimums met
- [ ] No comparisons with other applications
- [ ] No restatement of application
- [ ] No outside information (no web search beyond preprints/LoS hyperlinks)
- [ ] No integrity / eligibility allegations in text
- [ ] No AI-generated text
- [ ] Anti-bias check completed (halo/horns/confirmation/conformity/affinity/anchor)
- [ ] CoI re-confirmed against all named participants and key collaborators
- [ ] Confirmation of submission saved to task file
```

## Notes on adaptation

- For **General Assessor / CoE** work, the deliverable in step 5 is panel-oriented (rank within pool, defended at SAC) rather than 500-char-per-criterion applicant-facing text. Adapt the template by removing per-criterion char minimums and adding a `## Rank within allocation` and `## Recommendation rationale` section. Keep the criterion grid because you still need to triangulate against Detailed Assessor signals.
- For **collegial draft review**, this template is overkill — use the reading notes format directly and produce feedback in the user's voice.
