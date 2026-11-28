---
name: pull
description: Claim a PKB task, do the job it specifies to completion, record verified evidence under ## Report, and hand over via /dump. Use as the task entry point in any session with crew installed; dispatched worker containers have no plugins and never run it.
---

# /pull -- Task Execution

Claim a PKB task, do the job it specifies, record verified evidence under `## Report`, and invoke `/dump` to hand over.

## 1. Claim & Assemble

- Claim the assigned task via `pkb_claim_task` (`assignee` set to your agent or role), looking it up by exact ID or title (`pkb_get_task`); if invoked on an untracked directive without a task ID, ensure a task exists on the graph per the composed workflow before claiming it.
- Verify deliverables as a frozen `## Acceptance` checklist before starting work. If the task lacks `## Instructions` and `## Appendix: Sources` (and is not `invoke /<skill>`), compose its workflow via the active workflow-composition mechanism. Execute the composed workflow's steps and nothing more: the composed workflow decides what gets reviewed, verified, and delivered.
- Keep the PKB task updated after major stages so progress survives container pre-emption.

## 2. Do the Job

- Execute the task end-to-end in-session, coordinating subagents in parallel where helpful and reading each target file in full before editing.
- Commit scrubbed work incrementally (`data-boundaries`: no private PKB, task, or session IDs, `Task:` trailers, personal names, or private hostnames) so work survives pre-emption; push or open a pull request only when the task's `Output` names one.
- Escalate blocking infrastructure or tool failures verbatim without hidden workarounds.
- Run only the checks the task or repository calls for. Queue a dependent follow-up task (under the governing parent with `needs` edges and zero leaf `serves` edges) only when work requires a different repository, a different execution window or external wait, or a separate external agent or session, routing it as the composed workflow directs.

## 3. Consolidate Findings & Durable Facts

- Write the handback under `## Report`, stating the task's original ask and acceptance criteria upfront and quoting deciding primary evidence inline for every load-bearing claim.
- Offer settled durable facts uncovered during work (decisions, architectural constraints, verified system-state facts, or KB corrections -- excluding exploratory thinking aloud) to the knowledge-base curation role with source pointers, or record them under `## Durable Facts` on the task and handover when isolated.

## 4. Verify Criteria & Determine Status

Verify every criterion against primary evidence (`file:line`, quoted output, counts, PR URL, or test run). Tick (`[x]`) only items directly evidenced; leave others unticked (`[ ]`) with limits stated.

- `done`: All in-scope criteria are met with evidence in `## Report` and delivered where `Output` names (the report, the working branch, a shared location, or a PR with `pr_url` and `branch` when `Output` names one -- never ephemeral scratch paths), and any out-of-session follow-up is queued. Exit without waiting for CI, review, merge, or proof of user installation or deployment.
- `partial`: In-session criteria remain unfinished (blocker, missing tool, scope seam, missing evidence, or pre-work approval boundary), or the task checklist contains an unreachable post-exit criterion (complete reachable work, leave that item unticked, and cite it in `reason`).
- `failed`: Check or review task fails; document failure evidence and root cause.
- Never set `review`, and never create speculative follow-up tasks (partial and failed tasks are settled according to the composed workflow).

## 5. Handover (`/dump`)

Always invoke `/dump` on exit regardless of release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`) so `## Report` and the final handover report are recorded.
