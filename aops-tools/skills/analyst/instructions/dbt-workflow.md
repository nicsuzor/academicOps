---
title: dbt Workflow
type: reference
category: instruction
permalink: skills-analyst-dbt-workflow
description: Workflow and best practices for creating and modifying dbt data models in layered architecture
tags: [dbt, data-engineering, workflow, models, reference]
---

# dbt Model Workflow

Create or modify dbt models following academicOps layered architecture.

## Critical Rule: All Data Access Through dbt

**🚨 CRITICAL RULE: ALL data access MUST go through dbt models. NEVER query upstream sources directly.**

### Decision Tree

```
Need data for analysis?
│
├─ Does required data exist in dbt marts?
│  ├─ YES → Use `SELECT * FROM {{ ref('mart_name') }}`
│  │         └─ Done! Use this data in analysis.
│  │
│  └─ NO → Does it exist in staging models?
│     ├─ YES → Should this become a new mart?
│     │  ├─ YES → Go to: DBT Model Workflow (create mart)
│     │  └─ NO → Use staging model for exploratory work
│     │
│     └─ NO → Data doesn't exist in dbt yet
│        └─ Ask user: "Should I create a dbt model for [data source]?"
│           ├─ YES → Go to: DBT Model Workflow (create staging model)
│           └─ NO → Stop. Cannot proceed without dbt model.
```

### Prohibited Actions

❌ **NEVER** do this:

```python
# Direct BigQuery query - PROHIBITED
df = client.query("SELECT * FROM bigquery.raw.cases").to_dataframe()

# Direct database query - PROHIBITED
df = pd.read_sql("SELECT * FROM raw_schema.table", engine)

# Direct API call for analysis data - PROHIBITED
response = requests.get("https://api.example.com/data")
```

✅ **ALWAYS** do this:

```python
# Query through dbt mart - CORRECT
from db_resolver import get_canonical_db_path
import duckdb

conn = duckdb.connect(str(get_canonical_db_path()))
df = conn.execute("SELECT * FROM fct_case_decisions").df()


# Or reference in Streamlit
@st.cache_data
def load_data():
    conn = duckdb.connect(str(get_canonical_db_path()))
    return conn.execute("SELECT * FROM fct_case_decisions").df()
```

### Why This Matters

- **Reproducibility**: Queries are version-controlled in dbt
- **Data governance**: dbt models are single source of truth
- **Quality**: Data passes through validated transformation pipeline
- **Consistency**: All analysts use same transformations

## Before Creating New Model: Check for Duplicates

**REQUIRED:** Always check existing models first to avoid duplication.

```bash
# List all existing models
ls -1 dbt/models/staging/*.sql dbt/models/intermediate/*.sql dbt/models/marts/*.sql

# Search for related models
grep -r "keyword" dbt/models/
```

Ask yourself:

- Can I extend an existing model instead of creating new one?
- Does this transformation already exist?
- Can I reuse intermediate models?

## Model Layers

1. **Staging (`stg_*`)** - Clean and standardize raw data
   - Type casting
   - Rename to conventions
   - Basic filtering (remove test data, invalid records)
   - NO business logic

2. **Intermediate (`int_*`)** - Business logic transformations
   - Can be ephemeral (not materialized)
   - Focused transformations
   - Reusable logic

3. **Marts (`fct_*`, `dim_*`)** - Analysis-ready datasets
   - `fct_*`: Fact tables (events, transactions, measurements)
   - `dim_*`: Dimension tables (entities, classifications)
   - Materialized for performance

## Follow Single-Step Workflow

When creating a dbt model, take ONE step, then stop:

**Step 1: Create the model file**

```bash
# Create staging model
touch dbt/models/staging/stg_source_name.sql
```

Write SQL:

```sql
-- models/staging/stg_cases.sql
select
    id as case_id,
    cast(submitted_at as date) as submission_date,
    lower(status) as status,
    decision_text
from {{ source('raw', 'cases') }}
where id is not null
```

**STOP. Show to user. Wait for feedback.**

**Step 2: Add documentation** (only after user approves model)

```yaml
# dbt/schema.yml
models:
  - name: stg_cases
    description: Cleaned case data from raw source
    columns:
      - name: case_id
        description: Unique identifier for case
      - name: status
        description: Case status (pending, reviewed, published)
```

**STOP. Show to user. Wait for feedback.**

**Step 3: Add tests** (only after user approves documentation)

```yaml
columns:
  - name: case_id
    tests:
      - unique
      - not_null
```

**STOP. Show to user. Wait for feedback.**

**Step 4: Run the model** (only after user approves tests)

```bash
dbt run --select stg_cases
dbt test --select stg_cases
```

**STOP. Report results. Wait for next instruction.**

## Additional Resources

See [[dbt-patterns]] for comprehensive dbt patterns, including:

- Testing strategies (schema, singular, package tests)
- Documentation practices
- Common patterns (incremental models, source freshness)
- Performance optimization
