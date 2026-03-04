---
name: evaluate-dashboard
title: Evaluate Overwhelm Dashboard
description: "Phase 1 of the QA handoff chain: dynamic visual QA and structural verification. Produces a report, then STOPS."
triggers: [evaluate dashboard, overwhelm dashboard, visual QA, dashboard evaluation, dashboard QA]
chain: qa-handoff-chain
phase: 1-evaluate
next: decompose-qa-report
---

# Workflow: Evaluate Overwhelm Dashboard

Phase 1 of the QA handoff chain (Evaluate → Decompose → Implement). This workflow produces a QA report and **STOPS**. It does NOT decompose findings into tasks or fix issues.

> **Why the split?** QA evaluation requires user-empathy and design judgment. Decomposition requires task design skills. Implementation requires engineering. Mixing these in one session causes QA agents to make technical rearrangements thinking they are UX fixes. See issues #729, #731, #732.

## 1. Setup & Execution

Ensure visualization dependencies are installed, the `ACA_DATA` environment variable is set, and start the server:

```bash
# 1. Install 'viz' extra
uv sync --extra viz

# 2. Start dashboard in headless mode (default port 8501)
uv run streamlit run lib/overwhelm/dashboard.py --server.headless true
```

## 2. Dynamic Specification Discovery

Before evaluating, read the current "Acceptance Criteria" and "ADHD Design Principles" from the source specs:

- `specs/overwhelm-dashboard.md`
- `specs/task-map.md`

## 3. Visual Validation Routine

Use browser tools to navigate the dashboard and perform the following for each view:

1. **Read Specs:** Identify the "Acceptance Criteria" for the current view mode (Dashboard vs. Task Graph).
2. **Verify UI:** Confirm every mandated feature in the spec is present and functional in the browser.
3. **Stress Test:** Verify the ADHD Design Principles (e.g., "Scannable, not studyable", "No flat displays at scale") are upheld by the current rendering.
4. **Check Data Integrity:** Confirm the UI matches the underlying state in `$ACA_DATA/tasks/index.json` and the relevant graph file: `$ACA_DATA/outputs/graph.json` for the Tasks view, or `$ACA_DATA/outputs/knowledge-graph.json` for the Knowledge Base view.

## 4. Write QA Report

Write the report to `qa/dashboard-qa-results-{YYYY-MM-DD}.md` with this structure:

```markdown
# Dashboard QA Report — {YYYY-MM-DD}

## Verdict: {VERIFIED | ISSUES}

## Summary

{1-3 sentence overview of findings}

## Per-View Findings

### {View Name}

#### Spec Compliance

{What matches spec, what diverges}

#### ADHD Design Principles

{Assessment against each principle — narrative, not checklist}

#### Data Integrity

{Any mismatches between UI and underlying data}

## Deviations from Spec

{Numbered list of gaps, each with:}

1. **{Title}**: {description} — Severity: {critical|major|minor}

## Recommendations

{Specific, actionable, empathetic to both user AND developer}
```

## 5. STOP — Handoff Boundary

**You are done.** Do not:

- Create tasks from the findings
- Decompose issues into subtasks
- Fix any problems you found
- Suggest code changes

Instead, report the file path of your QA results file. The next phase (decompose-qa-report) will review your report and create properly scoped tasks with UX-centered acceptance criteria.

> **Next phase**: `decompose-qa-report` — Review this QA report and create tasks with UX acceptance criteria.
