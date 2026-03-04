---
name: evaluate-dashboard
title: Evaluate Overwhelm Dashboard
description: Dynamic visual QA and structural verification of the Overwhelm Dashboard against live acceptance criteria and ADHD design principles.
triggers: [evaluate dashboard, overwhelm dashboard, visual QA, dashboard evaluation, dashboard QA]
---

# Workflow: Evaluate Overwhelm Dashboard

Instructions for dynamic visual QA and structural verification against the live specifications.

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

## 4. Documentation of Deviations

Record any gaps where the implementation diverges from the live specifications. Do not rely on previous evaluations; verify the implementation against the spec as it exists _now_.

Write QA results to `qa/dashboard-qa-results-{date}.md` with:

- Per-task check results (pass/fail/untested with evidence)
- End-to-end scenario results
- Emotional assessment
- Verdict: VERIFIED or ISSUES

## 5. Decomposition & Task Creation

After finalising the QA report, create actionable follow-up work:

1. **Create or update an epic** for the dashboard improvement work if one doesn't exist.
2. **Decompose each critical/major finding** into individual tasks with clear acceptance criteria derived from the QA check that failed.
3. **Set task priorities** based on QA severity: critical findings → P1, major → P2, minor → P3.
4. **Link tasks** to the QA report and the relevant spec section.

This ensures QA findings are not just documented but enter the task queue for resolution.
