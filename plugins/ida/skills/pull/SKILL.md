---
name: pull
description: Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified results, and hand over via /dump. Use for fast-path worker execution of leaf tasks. Exclude for composite tasks needing workflow composition and multi-agent fan-out (use /supervise).
---

# /pull -- Fast-Path Task Execution

Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified evidence under `## Report`, and invoke `/dump` to hand over. Dispatched leaf workers operate strictly under the state-only invariant.

## 1. Claim Task

- Claim the assigned task via `pkb_claim_task` (`assignee` set to your agent or role). Look up assigned tasks strictly by exact ID or title (`pkb_get_task`) rather than running exploratory semantic searches; if unreachable, halt or query the custodian (`pauli`).
- Mutate only the claimed task's own fields and checklist: never reify workflows, create child tasks, or mint follow-ups.
- Verify deliverables as a frozen `## Acceptance` checklist on the task before starting work.
- Coordinators use `/pull` strictly for lightweight documentation, synthesis, or coordination without test suites or large codebase sweeps; dispatch implementation, sweeps, and test runs to isolated worker containers via `/dispatch`.

## 2. Execute Work

- Deliver stated outcomes directly, sequencing steps in session and escalating failures upstream without hidden workarounds.
- **Whole-file inspection**: Read each target file in full before editing so architecture, conventions, and helpers are understood; narrow line-slice reads without whole-file context are prohibited (line numbers are advisory pointers only).

## 3. Consolidate Findings & Durable Facts

- Write the handback under `## Report` solely in clean Argdown prose per `ida:premise-check`, stating the task's original ask and acceptance criteria upfront and quoting deciding primary evidence inline for every load-bearing claim.
- Offer settled durable facts uncovered during work (decisions, architectural constraints, verified system-state facts, or KB corrections -- excluding exploratory thinking aloud) to the custodian (`pauli`) with source pointers, or record them under `## Durable Facts` on the task and handover when isolated.

## 4. Verify Criteria & Determine Status

Verify every criterion against primary evidence (`file:line`, quoted output, counts, PR URL, or test run). Tick (`[x]`) only items directly evidenced; leave others unticked (`[ ]`) with limits stated.

- `done`: All in-scope criteria are met with evidence in `## Report` and delivered where `Output` names (draft PR opened via `gh pr create --draft` with `pr_url` and `branch`, or durable PKB artifact pointer -- never ephemeral scratch paths). Exit without waiting for CI, review, merge, or proof of user installation/deployment.
- `partial`: Worker's own items remain unfinished (blocker, missing tool, scope seam, missing evidence, or pre-work approval boundary), or the task checklist contains an unreachable post-exit criterion (complete reachable work, leave that item unticked, and cite it in `reason`).
- `failed`: Check or review task fails; document failure evidence and root cause.
- Never set `review`, and never create or name speculative follow-up tasks (`/reconcile` settles partial and failed tasks from the parent).

## 5. Handover (`/dump`)

Always invoke `/dump` on exit regardless of release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`) so `## Report` and the final handover report are recorded.
