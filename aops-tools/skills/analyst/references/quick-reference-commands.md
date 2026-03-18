---
category: ref
---

# Quick Reference Commands

## dbt Commands

```bash
# List existing dbt models
ls -1 dbt/models/staging/*.sql dbt/models/intermediate/*.sql dbt/models/marts/*.sql

# Run specific dbt model
dbt run --select model_name

# Run tests for model
dbt test --select model_name

# Check dbt lineage
dbt docs generate
dbt docs serve
```

## Streamlit

```bash
# Run Streamlit app
streamlit run streamlit/dashboard.py
```

## DuckDB Warehouse

```bash
# Query warehouse
duckdb data/warehouse.db -c "SELECT * FROM fct_cases LIMIT 10"
```
