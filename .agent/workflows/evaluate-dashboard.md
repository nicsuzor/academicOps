# Workflow: Evaluate Overwhelm Dashboard

Instructions for dynamic visual QA and structural verification against the live specifications.

## 1. Setup & Execution

Ensure visualization dependencies are installed and start the server:

```bash
# 1. Install 'viz' extra
uv sync --extra viz

# 2. Start dashboard in headless mode (default port 8501)
uv run streamlit run lib/overwhelm/dashboard.py --server.headless true
```

## 2. Dynamic Specification Discovery

Before evaluating, read the current "Acceptance Criteria" and "ADHD Design Principles" from the source specs:

- `aops/specs/overwhelm-dashboard.md`
- `aops/specs/task-map.md`

## 3. Visual Validation Routine

Use browser tools to navigate the dashboard and perform the following for each view:

1. **Read Specs:** Identify the "Acceptance Criteria" for the current view mode (Dashboard vs. Task Graph).
2. **Verify UI:** Confirm every mandated feature in the spec is present and functional in the browser.
3. **Stress Test:** Verify the ADHD Design Principles (e.g., "Scannable, not studyable", "No flat displays at scale") are upheld by the current rendering.
4. **Check Data Integrity:** Confirm the UI matches the underlying `ACA_DATA/tasks/index.json` and `ACA_DATA/graph.json` state.

## 4. Documentation of Deviations

Record any gaps where the implementation diverges from the live specifications. Do not rely on previous evaluations; verify the implementation against the spec as it exists _now_.
