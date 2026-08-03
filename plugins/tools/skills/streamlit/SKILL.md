---
name: streamlit
description: Streamlit implementation of the analyst presentation layer. Use when building or updating a Streamlit dashboard that displays pre-computed research data. This is the Streamlit-specific HOW for the tech-agnostic principles in the aops-tools analyst skill — display only, never transform.
---

# Streamlit — Presentation Layer (academicOps)

Streamlit is one **swappable** implementation of the presentation layer. The `analyst`
skill owns the principle — display only, never transform — which holds whichever
dashboard tool you use.

## When to use

- The project has a Streamlit app (`streamlit/` directory or `.py` files using `st.`).
- You need to display pre-computed metrics, render charts, or add interactive filtering
  on EXISTING columns.

## Hard boundary

Streamlit may read (`SELECT * FROM mart`), filter on existing columns, format for
display, and render charts. It must NEVER `GROUP BY`/aggregate, `JOIN`, apply `CASE`
business logic, or compute derived metrics inline. If tempted to transform: STOP and
add a model in the transformation layer (see the dbt skill) instead.

This boundary is the whole of what this skill contributes. Fetch current Streamlit API
documentation at the point of use.
