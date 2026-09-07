---
name: streamlit
description: Streamlit presentation layer for analyst dashboards. Use to display pre-computed research metrics and charts. Strictly display-only; no inline data transformations or joins.
---

# Streamlit -- Presentation Layer

Streamlit provides presentation dashboards for pre-computed research data.

## Boundaries

- **Display only**: Read mart models (`SELECT * FROM mart`), filter on existing columns, format values, and render visualizations.
- **No inline transformation**: Never execute aggregations (`GROUP BY`), table joins, or `CASE` business logic within dashboard scripts. Route all transformation logic to dbt models.

Fetch current Streamlit API documentation dynamically at point of use.
