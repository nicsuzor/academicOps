---
title: Task base
type: template
description: Foundation for every task executed from a task file via /ida:supervise (repo-scoped epic tasks) or /ida:pull (plain leaf tasks) -- compose all other workflows onto it with single-session combined-task default.
tags: [base, task]
---

- **GOAL:** <one sentence stating the observable outcome>
- **STRUCTURAL PLACEMENT:** Tasks requiring review or follow-up must be structured as a single combined repo-scoped task by default under `/ida:supervise` (handling design review, test-first build, PR creation, and independent verification in one container session), splitting into separate child/follow-up tasks ONLY when explicitly requiring a different repository, different time, or separate external agent/session; never as loose siblings under an external parent. Plain leaf workers under `/ida:pull` operate strictly state-only. An agent given a task does the groundwork and makes the decision itself; never file the task back to the user as their decision (`assignee: user`) unless the user explicitly directed to decide it themselves (tg 1013).
- **BOUNDARY:** A refusal at or beyond the container boundary is a halt, never a method. In-container sandbox refusals are not walls.
- **ACCEPTANCE CRITERIA:** <one line each, stating observable end-state conditions rather than mechanism prescriptions or file:line edits; workers read target files in full before editing>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <destination repo or URI (no local paths, polecats run isolated)>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.
