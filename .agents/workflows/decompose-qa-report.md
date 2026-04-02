---
name: decompose-qa-report
title: Decompose QA Report into UX Tasks
description: "Phase 2 of the QA handoff chain: review QA report and create tasks with UX-centered acceptance criteria."
triggers: [decompose QA, review QA report, QA decompose, create tasks from QA]
chain: qa-handoff-chain
phase: 2-decompose
prev: evaluate-dashboard
next: implement (standard task execution)
---

# Workflow: Decompose QA Report into UX Tasks

Phase 2 of the QA handoff chain (Evaluate → Decompose → Implement). This workflow reads a QA report, designs UX-centered acceptance criteria for each finding, and creates tasks. It does NOT implement fixes.

> **Why a separate phase?** Decomposition requires designing what "good" looks like from the user's perspective. This is UX design work, not engineering. The QA evaluator's job was to identify deviations; your job is to define what success looks like for the user. See issues #729, #731, #732.

## 1. Read the QA Report

Read the most recent QA results file from `qa/dashboard-qa-results-{YYYY-MM-DD}.md`.

If the verdict is `VERIFIED`, report that no decomposition is needed and stop.

## 2. Read Relevant Specs

Before designing acceptance criteria, re-read the source specs to understand the user intent:

- `specs/overwhelm-dashboard.md`
- `specs/task-map.md`
- Any user stories or personas referenced in the specs

## 3. Design UX-Centered Acceptance Criteria

For each deviation in the QA report, design acceptance criteria that describe the **user experience**, not the technical implementation.

### Anti-patterns (do NOT do this)

| Bad (technical)                                 | Good (UX-centered)                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------------------- |
| "Move the filter widget above the chart"        | "User can narrow the view before scanning — filter is discoverable without hunting" |
| "Add a string parameter to the filter function" | "Filtering feels instant and doesn't require the user to remember syntax"           |
| "Change the CSS to increase font size"          | "Key numbers are readable at a glance without leaning in"                           |
| "Reorder the sections in the Streamlit layout"  | "The information hierarchy matches the user's priority hierarchy"                   |

### For each finding, write

1. **User story**: As a [persona], I need [capability] so that [outcome].
2. **Quality spectrum**: What does excellent look like? What does poor look like? (Narrative, not checklist.)
3. **Acceptance criteria**: 2-4 criteria written from the user's perspective, evaluable by a QA agent without reading source code.
4. **Severity**: Critical (blocks primary use case), major (degrades experience), minor (polish).

## 4. Create Tasks

For each finding that warrants a task:

1. Find the parent epic for the relevant feature area.
2. Create a task with:
   - Title: User-facing description of what needs to improve
   - Body: User story + quality spectrum + acceptance criteria from Step 3
   - Parent: The relevant epic
   - Priority: Based on severity

Group related findings into a single task when they share root cause or can be addressed together without scope bloat.

## 5. Write Decomposition Summary

Append a decomposition summary to the QA report file or write to `qa/dashboard-qa-decomposition-{YYYY-MM-DD}.md`:

```markdown
# QA Decomposition Summary — {YYYY-MM-DD}

## Source Report

qa/dashboard-qa-results-{YYYY-MM-DD}.md

## Tasks Created

| # | Task ID | Title   | Severity   | Parent Epic |
| - | ------- | ------- | ---------- | ----------- |
| 1 | {id}    | {title} | {severity} | {epic}      |

## Findings Not Tasked

{Any findings from the report that were not converted to tasks, with reasoning}
```

## 6. STOP — Handoff Boundary

**You are done.** Do not:

- Implement any of the tasks you created
- Make code changes
- Start working on fixes
- Modify the dashboard or any source code

The tasks you created will be picked up through the normal task queue by implementation agents.

> **Next phase**: Standard task execution — implementation agents pick up the tasks you created and implement them, guided by the UX acceptance criteria you wrote.
