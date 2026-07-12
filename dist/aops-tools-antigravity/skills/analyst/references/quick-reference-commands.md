---
category: ref
---

# Quick Reference Commands

Engine-neutral commands for working with a modelled analytical warehouse. For
transformation-engine commands (e.g. `dbt run`/`dbt test`) and presentation-engine
commands (e.g. `streamlit run`), see the aops-extras `dbt` and `streamlit` skills.

## Querying the Modelled Layer (DuckDB example)

```bash
# Read from a tested mart in the warehouse (never query raw upstream sources)
duckdb data/warehouse.db -c "SELECT * FROM fct_cases LIMIT 10"
```

## Inspecting the Pipeline

```bash
# List existing transformation-layer models (path/extension is engine-specific)
ls -1 dbt/models/**/*.sql 2>/dev/null

# List presentation-layer apps (path is engine-specific)
ls -1 streamlit/*.py 2>/dev/null
```
