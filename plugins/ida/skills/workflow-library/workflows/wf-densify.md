---
alias:
  - wf-densify
  - wf-link-densify
description: Universal graph link densify routine for evaluating, drafting, and writing edge proposals ordered by reach under the flow rule.
id: wf-densify
tags:
  - wf-template
  - valuation
  - densify
  - ranking
title: Universal Graph Link Densify Template
type: template
---

## What this template does

Drafts, evaluates, and writes link proposals for unvalued or uncalibrated graph edges ordered by reach (R3 in `specs/workflows/graph-valuation.md`). Agents draft edge values with supporting evidence, write them as `agent-proposed`, and rely on corrections made directly on the graph.

## Procedure

1. **Candidate pool**: Draw candidate rows in priority order:
   - Edges at `set_by: migrated` awaiting calibration.
   - Edges at `set_by: agent-proposed`.
   - Edges with no quantum, drafting proposals per FR §5.1.
2. **Granularity before value**: Wire at the highest node where the answer is identical for all descendants. A batch row covering fungible siblings is one row for their container, not one row each.
3. **Measure from source of record**: Ground proposed quantum and probability in primary artifacts (code, specs, publications), not hearsay.
4. **Order by reach**: Compute reach as `|worth of priced targets edge leads to| × proposed strength` from the engine `stake` map. Sort descending by reach, then proposal age.
5. **Draft and write edge proposals (ADR-0002)**:
   - For each edge in the batch (up to 50 rows), evaluate label (`serves`, `needs`, `supports`), quantum, probability, effect, and one-sentence justification under the Three-Purpose Taxonomy.
   - Densify handles only real weight flow edges (`serves`, and valid `supports` that directly alter an upstream node's execution difficulty or likelihood); never convert markdown body citations into frontmatter edges. Tracking tasks link only to user understanding targets.
   - Write edges directly with `set_by: agent-proposed`. Writes returning without error need no readback.
6. **Agent corrections**: Correct mechanical errors unasked on in-node evidence (word outside scale, edge to wrong class, mismatched justification); write as `agent-proposed`.
7. **Rely on graph corrections**: Do not pause, poll, or block for human sign-off; record the link proposals on the graph where corrections are made directly as needed.

## Output contract

- An evaluated edge report of ≤ 50 rows ordered by reach.
- A report of edges updated with `set_by: agent-proposed`.
