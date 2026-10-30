---
title: Task base
type: template
description: Foundation for every task executed from a task file via /ida:pull -- compose all other workflows onto it.
tags: [base, task]
---

- **GOAL:** <one sentence stating the observable outcome>
- **STRUCTURAL PLACEMENT:** Tasks requiring review or follow-up must be structured either as a single task with internal subtasks (if executable by the same agent in one session) or as a dedicated epic with child tasks (if multi-session or independent context is required); never as loose siblings under an external parent. Research on design questions includes by default a dependent decision task assigned to the user (`assignee: user`) to select the implementation route.
- **ACCEPTANCE CRITERIA:** <one line each, stating observable end-state conditions rather than mechanism prescriptions or file:line edits; workers read target files in full before editing>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <destination repo or URI (no local paths, polecats run isolated)>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.
