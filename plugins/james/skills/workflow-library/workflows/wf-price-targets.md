---
alias:
  - wf-price-targets
  - wf-target-pricing
description: Universal target pricing routine for estimating and writing approximate target worth directly to the graph on the open-ended continuous log scale.
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

Estimates and writes approximate worth for target nodes on the open-ended continuous log scale ($W_t \in \mathbb{R}$, no cap) directly to the graph with supporting evidence (R4 in `specs/workflows/graph-valuation.md`). Agents work out the best approximate worth, write it to the graph, leave `intent` untouched, and rely on corrections made directly on the graph.

## Procedure

1. **Scale**: Price targets on the open-ended continuous log scale ($W_t \in \mathbb{R}$, no cap; S26):
   - Positive aspirations: Positive values on the open log scale, using price ratios to express relative value across fat-tailed outcomes (e.g., a 10% moonshot priced ~9x a 90% sure thing; a 2% moonshot priced ~45x; 100x+ outcomes are uncapped).
   - Negative anti-targets: Negative values on the open log scale, proportional to the loss or catastrophe averted.
   - Hub targets: Configure capital stocks (reputation, funding reserve, infrastructure) as hubs (S27).
2. **Inspect node links**: Go through the node's links before setting its price. Inspect incoming and outgoing edges (`serves`, `depends_on`, `part_of`, `supports`), checking edge quantum, effect, and whether linked work is decomposed and active, so valuation reflects the real work and dependencies connected to the node.
3. **Estimate approximate worth**: Work out the best approximate worth for each unpriced target using the inspected links, open work behind it, and existing severity as an anchor prompt.
4. **Write to graph**: Write the estimated `worth` directly to the target node using `pkb.update_task(id=..., worth=...)`.
5. **Leave intent untouched**: Never write, modify, or clear `intent` when pricing targets; `intent` remains reserved and untouched.
6. **Evidence and justification**: Attach the evidence justification to the target record explaining the estimated worth calculation.
7. **Consistency pass**: Verify ordering is transitive and relative ratios hold across targets in the same domain.
8. **Rely on graph corrections**: Do not pause, poll, or block for human sign-off; record the estimates directly on the graph where corrections are made as needed.
9. **New targets**: Agents never create target nodes; work fitting no existing target is recorded as a finding.

## Output contract

- A report of target nodes updated with estimated `worth` and supporting evidence.
- Zero modifications to `intent`.
