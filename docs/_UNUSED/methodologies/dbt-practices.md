# DBT Best Practices

This document outlines best practices for using dbt (data build tool) in computational research projects.

## 🚨 CRITICAL: Data Access Policy

**ALL data access MUST go through dbt models. Direct queries to upstream sources (BigQuery, databases, APIs) are PROHIBITED.**

**Why this is mandatory:**

- **Reproducibility**: Queries are version-controlled in dbt
- **Data governance**: dbt models are the single source of truth
- **Quality**: Data passes through validated transformation pipeline
- **Consistency**: All analysts use same transformations

**Workflow when data is missing:**

1. ❌ **NEVER** query upstream source directly (e.g., `SELECT * FROM bigquery.raw.table`)
2. ✅ **CREATE** appropriate dbt model (staging/intermediate/mart)
3. ✅ **REFERENCE** the model via `{{ ref('model_name') }}`

**If you need data not in existing marts:**

- Ask user: "Should I create a dbt model for this data?"
- Create model in appropriate layer (staging for raw cleanup, marts for analysis)
- Run `dbt run --select model_name` to materialize
- Query the materialized model, not the upstream source

## Overview

dbt is used to define, document, and validate data transformations. In academicOps projects, dbt serves as the foundation for reproducible empirical analysis by:

- Defining data models as SQL transformations
- Documenting data lineage and relationships
- Validating data quality through tests
- Creating a reproducible pipeline from raw data to analysis-ready datasets

## Testing Strategy

### 1. Schema Tests (in schema.yml)

Built-in tests for common column-level checks. Define these in your `schema.yml` files alongside model documentation.

**Available schema tests:**

- `not_null`: Column has no nulls
- `unique`: Column values are unique
- `relationships`: Foreign key constraints (references another model/column)
- `accepted_values`: Column has only specific values from a defined list

**Example:**

```yaml
models:
  - name: stg_cases
    columns:
      - name: case_id
        tests:
          - unique
          - not_null
      - name: status
        tests:
          - accepted_values:
              values: ["pending", "reviewed", "published"]
```

### 2. Singular Tests (in tests/)

Custom SQL queries for complex validation logic. Create `.sql` files in the `tests/` directory.

**How they work:**

- Return 0 rows = PASS ✓
- Return >0 rows = FAIL ✗ (shows you the problematic data)
- Great for multi-column logic, data quality checks, business rules

**Example:**

```sql
-- tests/assert_decision_dates_logical.sql
-- Fail if any case has decision_date before submission_date
select
    case_id,
    submission_date,
    decision_date
from {{ ref('stg_cases') }}
where decision_date < submission_date
```

### 3. Test Severity

Control whether tests fail the build or just warn:

```yaml
columns:
  - name: optional_field
    tests:
      - not_null:
          severity: warn # Show warning but don't fail build
```

**Severity levels:**

- `error` (default): Fails the build, stops execution
- `warn`: Shows warning but continues build

**When to use warn:**

- Known data quality issues you're tracking
- Aspirational standards not yet achieved
- Optional fields with expected nulls in some contexts

### 4. Package Tests (dbt-utils)

The `dbt-utils` package provides reusable tests for common patterns:

```yaml
# Install: packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1

# Use in schema.yml
tests:
  - dbt_utils.expression_is_true:
      expression: "revenue >= 0"
  - dbt_utils.recency:
      datepart: day
      field: created_at
      interval: 1
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns: ["user_id", "date"]
```

**When to use:** Common patterns like recency checks, multi-column uniqueness, value ranges.

### 5. Diagnostic Models

Create ephemeral views for data quality monitoring:

```sql
-- models/diagnostics/data_quality_summary.sql
{{ config(materialized='view', tags=['diagnostic']) }}

select
    'content_populated' as check_name,
    count(*) as total_rows,
    count(case when content is not null then 1 end) as passing_rows
from {{ ref('stg_documents') }}
```

Run with `dbt show --select data_quality_summary` to inspect quality issues interactively.

### 6. When to Use Each Test Type

| Test Type             | Use For                        | Example                                                 |
| --------------------- | ------------------------------ | ------------------------------------------------------- |
| **Schema tests**      | Quick column-level checks      | Nulls, uniqueness, allowed values                       |
| **Singular tests**    | Complex multi-column logic     | Date ranges, cross-table consistency                    |
| **Package tests**     | Common reusable patterns       | Recency, multi-column uniqueness, value ranges          |
| **Diagnostic models** | Interactive quality inspection | Aggregated quality metrics, `dbt show` for quick checks |
| **Dashboards**        | Human review, visual analysis  | Exploratory data analysis, trend identification         |

**General principle:** Start with schema tests (fast, declarative), add package tests for common patterns, write singular tests for project-specific logic, create diagnostic models for quality monitoring, use dashboards for human judgment.

## Model Organization

### Staging Models (stg_)

First layer of transformation from raw sources. Focus on:

- Type casting
- Renaming to consistent conventions
- Basic filtering (remove test data, invalid records)
- No business logic yet

**Example:**

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

### Intermediate Models (int_)

Business logic and transformations. Can be ephemeral (not materialized).

**Example:**

```sql
-- models/intermediate/int_case_metrics.sql
select
    case_id,
    submission_date,
    decision_date,
    datediff('day', submission_date, decision_date) as processing_days
from {{ ref('stg_cases') }}
```

### Mart Models (fct_, dim_)

Final analysis-ready models:

- `fct_*`: Fact tables (events, transactions, measurements)
- `dim_*`: Dimension tables (entities, classifications)

## Documentation

Document all models in `schema.yml`:

```yaml
models:
  - name: fct_case_decisions
    description: One row per case decision with analysis metrics
    columns:
      - name: case_id
        description: Unique identifier for the case
        tests:
          - unique
          - not_null
      - name: processing_days
        description: Number of days from submission to decision
```

**Why document:**

- Agents can understand your data model
- Future you remembers what fields mean
- Collaborators can navigate the project
- Auto-generated documentation website with `dbt docs generate`

## Running Tests

```bash
# Run all tests
dbt test

# Run tests for specific model
dbt test --select stg_cases

# Run tests for model and downstream
dbt test --select stg_cases+

# Run only schema tests
dbt test --select test_type:schema

# Run only singular tests
dbt test --select test_type:singular
```

## Common Patterns

### Incremental Models

For large datasets, use incremental models to only process new data:

```sql
{{
    config(
        materialized='incremental',
        unique_key='case_id'
    )
}}

select * from {{ source('raw', 'cases') }}

{% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### Source Freshness

Validate that source data is recent:

```yaml
sources:
  - name: raw
    database: mydb
    freshness:
      warn_after: { count: 24, period: hour }
      error_after: { count: 48, period: hour }
    tables:
      - name: cases
```

## Integration with Analysis

dbt creates analysis-ready datasets. Connect to them via:

**Streamlit:**

```python
import duckdb

conn = duckdb.connect("data/warehouse.db")
df = conn.execute("SELECT * FROM fct_case_decisions").df()
```

**Jupyter:**

```python
# Use dbt's ref() pattern via sqlalchemy
from sqlalchemy import create_engine

engine = create_engine("duckdb:///data/warehouse.db")
df = pd.read_sql("SELECT * FROM fct_case_decisions", engine)
```

## References

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Testing Guide](https://docs.getdbt.com/docs/build/tests)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
