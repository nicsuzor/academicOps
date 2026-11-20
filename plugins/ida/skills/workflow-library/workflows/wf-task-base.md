---
title: Task base
type: template
description: Foundation for every task executed via /supervise (repo-scoped epic tasks) or /pull (plain leaf tasks) -- defines the canonical task schema, structural placement, groundwork rule, and container boundary.
tags: [base, task]
---

- **GOAL:** <one sentence stating the observable end-state>
- **ACCEPTANCE CRITERIA:** <one line each, stating observable outcomes rather than mechanism or file:line prescriptions>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <destination repo or URI; no local container paths, as isolated workers run independently>
- **REPORT:** Update the task via `/dump` in place (current state only; delete stale prose). Tick `[x]` an acceptance item only with inline primary evidence and citation for that item itself; leave unmet items `[ ]` with their limit stated.

## Placement and Execution

- **Single combined task by default**: Structure repo-scoped work requiring design, build, PR, or verification as one combined task under `/supervise`. Split into child or follow-up tasks ONLY when a step requires a different repository, different execution window, or separate external agent/session; never place loose siblings under an external parent.
- **State-only leaf workers**: Plain leaf workers under `/pull` mutate only their claimed task's own record and never inspect cross-task edges or mint follow-up tasks.
- **Groundwork first**: Read target files in full before editing (no keyhole reads) and settle unknowns from the PKB before escalating. Release as `partial` with a reasoned recommendation and options only when a genuine user decision blocks progress (never `review`).
- **Container boundary**: A refusal at or beyond the container boundary is a halt, never a workaround; in-container sandbox refusals are not walls.
