---
trigger: always_on
description: Do groundwork and decide routes directly rather than filing standalone decision tasks back to the user; model unknowns as empirical probes.
---

## Decisions Emerge from Graph Relationships, Not Standalone Tasks

Agents must never create un-actionable "decision" tasks or file conversational questions as backlog tickets. An agent given a task does the groundwork and makes the decision itself; it never files the task back to the user as their decision (`assignee: user`) unless the user explicitly requested to make that decision themselves. Where research investigates an open design question or architectural alternatives, the agent evaluates the options and chooses the recommended route directly to unblock downstream implementation tasks.

- **Candidate Options Remain in Task Bodies:** Competing candidate options stay inside the body of the scoping task or ADR until chosen. A task that has options to choose between is created as a single task with the candidate choices and evaluation criteria inside the task body. When a choice is made, only the selected option is reified into an actionable task under `parent: <scoping_task_id>`.
- **Model unknowns as empirical probes valued via `needs`:** Where a decision depends on missing runtime benchmarks, data, or empirical findings, mint an empirical probe task (`classification: probe`) wired directly into the waiting task via standard execution prerequisite `needs: [<probe_task_id>]`. Probes receive worth directly through prerequisite backward induction via `needs`.
- **Ask in-turn questions directly:** Interactive clarifications in an active session use `AskUserQuestion` directly rather than polluting the graph with un-actionable decision tasks.
