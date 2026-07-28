---
name: streamlit
description: Streamlit implementation of the analyst presentation layer. Use when building or updating a Streamlit dashboard that displays pre-computed research data. This is the Streamlit-specific HOW for the tech-agnostic principles in the aops-tools analyst skill — display only, never transform.
---

# Streamlit — Presentation Layer (academicOps)

This skill is the **Streamlit-specific implementation** of the presentation layer
described in the tech-agnostic `analyst` skill (aops-tools). The analyst skill owns the
_principle_ (display-only, never transform); this skill owns the _Streamlit how-to_ —
see **Hard boundary** below for what that means in practice.

Streamlit is one **swappable** choice of presentation layer. The display-only rule holds
regardless of which dashboard tool you use; only the patterns below are Streamlit-specific.

## Contents

- [[streamlit-workflow]] — single-step collaborative workflow for building Streamlit
  dashboards (load → STOP → chart → STOP → interactivity → STOP).
- [[streamlit-patterns]] — design patterns and best practices for research dashboards.
- [[streamlit]] — standard app structure and additional Streamlit patterns.

## When to use

- The project has a Streamlit app (`streamlit/` directory or `.py` files using `st.`).
- You need to display pre-computed metrics, render charts, or add interactive filtering
  on EXISTING columns.

## Hard boundary

Streamlit may read (`SELECT * FROM mart`), filter on existing columns, format for
display, and render charts. It must NEVER `GROUP BY`/aggregate, `JOIN`, apply `CASE`
business logic, or compute derived metrics inline. If tempted to transform: STOP and
add a model in the transformation layer (see the dbt skill) instead.
