---
alias:
  - wf-price-targets
  - wf-target-pricing
description: Universal target pricing routine for drafting and approving open-ended continuous log scale target worth in sittings of at most ten targets.
id: wf-price-targets
tags:
  - wf-template
  - valuation
  - pricing
  - targets
  - ranking
title: Universal Target Pricing Template
type: template
---

## What this template does

Drafts recommendations for pricing targets on the open-ended continuous logarithmic scale ($W_t \in \mathbb{R}$, S26) and presents them to Nic in sittings of at most ten targets (R4 in `specs/workflows/graph-valuation.md`). Only Nic's assent prices a target.

## Procedure

1. **Scale**: Price targets on the open-ended continuous log scale ($W_t \in \mathbb{R}$):
   - Positive aspirations: Baseline core commitment +1.00 (accreditation, livelihood), up to +10.00 to +100.00+ for transformative moonshots.
   - Negative anti-targets: Mirrored from -0.05/-1.00 down to -10.00/-100.00 for ruinous catastrophe.
   - Hub targets: Configure capital stocks (reputation, funding reserve, infrastructure) as hubs (S27).
2. **Draft recommendations**: Pauli drafts one recommended price anchor per target with one line of evidence citing what serves the target and open work behind it.
3. **Sitting constraints**:
   - At most 10 targets per sitting.
   - Outer bounds first: Set one Critical and one Minor anchor first to establish bounds.
   - Gain and loss targets priced together to maintain consistent ratios (S16).
4. **Consistency pass**: Verify ordering is transitive and relative ratios hold across targets.
5. **Approval**: Ida presents recommendations. Nic's explicit assent prices the target. An unanswered draft prices nothing (target stays 0).
6. **Re-confirmation**: Targets priced >180 days ago enter a routine pricing sitting row. Stored worth never decays automatically.
7. **New targets**: Agents never create target nodes; work fitting no existing target is recorded in the ask queue.

## Output contract

- A pricing sitting table of ≤ 10 targets with recommended anchor and one-line evidence, or
- A verified readback report of targets updated with Nic-confirmed worth.
