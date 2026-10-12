---
alias:
  - wf-densify
  - wf-link-densify
description: Universal densify routine for drafting and approving link proposals in batches of fifty ordered by reach under the flow rule.
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

Drafts link proposals for unvalued edges ordered by reach and presents them to Nic for batch approval (R3 in `specs/workflows/graph-valuation.md`). Only Nic's explicit approval writes `set_by: nic`.

## Procedure

1. **Candidate pool**: Draw candidate rows in priority order:
   - Edges at `set_by: migrated` awaiting confirmation.
   - Edges at `set_by: agent-proposed`.
   - Edges with no quantum, drafting proposals per FR §5.1.
2. **Granularity before value**: Wire at the highest node where the answer is identical for all descendants. A batch row covering fungible siblings is one row for their container, not one row each.
3. **Measure from source of record**: Ground proposed quantum and probability in primary artifacts (code, specs, publications), not hearsay.
4. **Order by reach**: Compute reach as `|worth of priced targets edge leads to| × proposed strength` from the engine `stake` map. Sort descending by reach, then proposal age.
5. **Batch table**: Format up to 50 rows in a single batch message:
   `| # | Work | → Target (worth) | Label | Proposed quantum | Probability | Effect | Why (one sentence) |`
6. **Nic's approval step**: Await reply under the grammar:
   `reply := item (";" item)*`
   `item := "all" | "all except" nums | num ":" ( qword ["," pword] | "drop" | "harms" )`
7. **Write approved values**:
   - Write `set_by: nic` only for rows explicitly approved or amended.
   - Rows excluded or omitted remain `agent-proposed` and re-enter later batches.
   - `drop` sets quantum to `none` with `set_by: nic` (does not delete edge).
   - Read back each updated edge via `pkb.get_task` and report readback without parse warnings.
8. **Batch expiry**: An unanswered batch expires after 14 days; withdraw it and rebuild with fresh reach ordering.
9. **Agent corrections without Nic**: Correct mechanical errors unasked only on in-node evidence (word outside scale, edge to wrong class, mismatched justification); write as `agent-proposed`, never `nic`.

## Output contract

- A batch table of ≤ 50 rows ordered by reach, or
- A verified readback report of edges updated to `set_by: nic`.
