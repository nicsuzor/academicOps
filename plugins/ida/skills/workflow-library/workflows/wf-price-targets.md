---
alias:
  - wf-price-targets
  - wf-target-pricing
description: Universal target pricing routine for estimating and writing approximate target worth directly to the graph within the bounded [-1.0, 1.0] engine range.
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

Estimates and writes approximate worth for target nodes on the bounded continuous scale ($W_t \in [-1.0, 1.0]$) directly to the graph with supporting evidence (R4 in `specs/workflows/graph-valuation.md`). Agents work out the best approximate worth, write it to the graph, leave `intent` untouched, and rely on corrections made directly on the graph.

## Procedure

1. **Scale**: Price targets on the bounded continuous scale within server-enforced engine bounds ($W_t \in [-1.0, 1.0]$):
   - Positive aspirations: From +0.05 up to +1.00, with core commitments (accreditation, livelihood) around +0.70 to +0.80, up to +1.00 for top-tier moonshots.
   - Negative anti-targets: Mirrored from -0.05 down to -1.00 for ruinous catastrophe.
   - Hub targets: Configure capital stocks (reputation, funding reserve, infrastructure) as hubs (S27).
2. **Estimate approximate worth**: Work out the best approximate worth for each unpriced target using what serves the target, open work behind it, and existing severity as an anchor prompt.
3. **Write to graph**: Write the estimated `worth` directly to the target node using `pkb.update_task(id=..., worth=...)`.
4. **Leave intent untouched**: Never write, modify, or clear `intent` when pricing targets; `intent` remains reserved and untouched.
5. **Evidence and justification**: Attach the evidence justification to the target record explaining the estimated worth calculation.
6. **Consistency pass**: Verify ordering is transitive and relative ratios hold across targets in the same domain.
7. **Rely on graph corrections**: Do not pause, poll, or block for human sign-off; record the estimates directly on the graph where corrections are made as needed.
8. **New targets**: Agents never create target nodes; work fitting no existing target is recorded as a finding.

## Output contract

- A verified readback report of target nodes updated with estimated `worth` and supporting evidence.
- Zero modifications to `intent`.
