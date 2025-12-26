---
title: DBT Workflow Reference
type: reference
permalink: analyst-ref-dbt-workflow
description: Detailed dbt patterns for data access, model organization (staging/intermediate/mart layers), testing strategies, documentation, and integration with analysis tools.
---

# DBT Workflow Reference

Detailed dbt patterns for academicOps computational research projects.

## Data Access Policy

**🚨 CRITICAL: ALL data access MUST go through dbt models.**

### Why This Is Mandatory

Direct queries to upstream sources (BigQuery, databases, APIs) are PROHIBITED because:

1. **Reproducibility**: Queries in dbt are version-controlled, documented, and testable
2. **Data governance**: dbt models are the single source of truth
3. **Quality**: Data passes through validated transformation pipeline with tests
4. **Consistency**: All analysts use identical transformations
5. **Auditability**: Changes to data logic are tracked in git history

### Workflow When Data Is Missing

```
Need data not in existing marts?
│
├─ Step 1: Ask user for permission
│  "Should I create a dbt model for [data source]?"
│
├─ Step 2: Create appropriate dbt model
│  ├─ Raw data cleanup → staging model (stg_*)
│  └─ Analysis-ready data → mart model (fct_*, dim_*)
│
├─ Step 3: Run dbt to materialize
│  dbt run --select model_name
│
└─ Step 4: Query the materialized model
   SELECT * FROM {{ ref('model_name') }}
```

**NEVER query upstream sources directly.** If data doesn't exist in dbt, create a model first.

## Model Organization

### Layered Architecture

```
Raw Data Sources
    ↓
Staging Models (stg_*)
    ↓
Intermediate Models (int_*)
    ↓
Mart Models (fct_*, dim_*)
    ↓
Analysis (Streamlit, Jupyter)
```

### Layer 1: Staging Models (stg_*)

**Purpose:** Clean and standardize raw data

**Responsibilities:**

- Type casting (strings to dates, numbers, etc.)
- Renaming to consistent conventions (snake_case, clear names)
- Basic filtering (remove test data, invalid records, nulls in key fields)
- Light transformation (lowercasing, trimming)

**NOT allowed:**

- Business logic
- Aggregations
- Joins (except simple lookups)
- Complex calculations

**Example:**

```sql
-- models/staging/stg_cases.sql
select
    id as case_id,
    cast(submitted_at as date) as submission_date,
    cast(decision_at as date) as decision_date,
    lower(trim(status)) as status,
    decision_text,
    metadata
from {{ source('raw', 'cases') }}
where id is not null  -- Basic filtering only
```

**Materialization:** Usually `view` (fast, always fresh)

### Layer 2: Intermediate Models (int_*)

**Purpose:** Business logic and transformations

**Responsibilities:**

- Business calculations (processing days, categorizations)
- Joins between staging models
- Window functions
- Complex transformations
- Reusable logic components

**Example:**

```sql
-- models/intermediate/int_case_metrics.sql
select
    case_id,
    submission_date,
    decision_date,
    status,
    datediff('day', submission_date, decision_date) as processing_days,
    case
        when processing_days <= 30 then 'fast'
        when processing_days <= 90 then 'normal'
        else 'slow'
    end as processing_category
from {{ ref('stg_cases') }}
```

**Materialization:** Usually `ephemeral` (not materialized, used as CTE) or `view`

### Layer 3: Mart Models (fct__, dim__)

**Purpose:** Analysis-ready datasets

**Fact Tables (`fct_*`):**

- Events, transactions, measurements
- One row per occurrence
- Includes metrics and foreign keys to dimensions
- Optimized for analysis queries

**Dimension Tables (`dim_*`):**

- Entities, classifications, lookup tables
- One row per entity
- Descriptive attributes
- Referenced by fact tables

**Example Fact:**

```sql
-- models/marts/fct_case_decisions.sql
select
    c.case_id,
    c.submission_date,
    c.decision_date,
    c.status,
    m.processing_days,
    m.processing_category,
    t.decision_sentiment,
    t.decision_topics
from {{ ref('int_case_metrics') }} m
join {{ ref('stg_cases') }} c using (case_id)
left join {{ ref('int_text_analysis') }} t using (case_id)
```

**Example Dimension:**

```sql
-- models/marts/dim_jurisdictions.sql
select
    jurisdiction_id,
    jurisdiction_name,
    jurisdiction_type,
    region,
    population
from {{ ref('stg_jurisdictions') }}
```

**Materialization:** Usually `table` (fast queries) or `incremental` (large datasets)

## Testing Strategy

### Test Type Selection Matrix

| Validation Need         | Test Type        | Where Defined       | Example                                          |
| ----------------------- | ---------------- | ------------------- | ------------------------------------------------ |
| Column never null       | Schema test      | schema.yml          | `- not_null`                                     |
| Column unique           | Schema test      | schema.yml          | `- unique`                                       |
| Specific allowed values | Schema test      | schema.yml          | `- accepted_values: {values: [...]}`             |
| Foreign key valid       | Schema test      | schema.yml          | `- relationships: {to: ref('other'), field: id}` |
| Multi-column logic      | Singular test    | tests/*.sql         | Date ranges, consistency checks                  |
| Common pattern          | Package test     | schema.yml          | Recency, multi-column unique                     |
| Quality monitoring      | Diagnostic model | models/diagnostics/ | Aggregated quality metrics                       |

### Schema Tests

Built-in tests defined in `schema.yml` alongside model documentation.

**Available tests:**

- `not_null`: Column has no null values
- `unique`: Column values are unique
- `relationships`: Foreign key constraint (references another model/column)
- `accepted_values`: Column only contains specific values from defined list

**Example:**

```yaml
models:
  - name: stg_cases
    description: Cleaned case data from raw source
    columns:
      - name: case_id
        description: Unique identifier for case
        tests:
          - unique
          - not_null

      - name: status
        description: Case processing status
        tests:
          - accepted_values:
              values: ["pending", "reviewed", "published", "rejected"]

      - name: jurisdiction_id
        description: Foreign key to jurisdictions
        tests:
          - relationships:
              to: ref('dim_jurisdictions')
              field: jurisdiction_id
```

### Singular Tests

Custom SQL queries for complex validation. Create `.sql` files in `tests/` directory.

**How they work:**

- Query returns 0 rows = PASS ✓
- Query returns >0 rows = FAIL ✗ (shows problematic data)
- Use for multi-column logic, business rules, data quality checks

**Example:**

```sql
-- tests/assert_decision_dates_logical.sql
-- Fail if any case has decision_date before submission_date
select
    case_id,
    submission_date,
    decision_date,
    datediff('day', submission_date, decision_date) as days_diff
from {{ ref('stg_cases') }}
where decision_date < submission_date
```

**Example: Cross-table consistency**

```sql
-- tests/assert_all_cases_have_metrics.sql
-- Fail if any case in fct_case_decisions missing from int_case_metrics
select
    f.case_id
from {{ ref('fct_case_decisions') }} f
left join {{ ref('int_case_metrics') }} m using (case_id)
where m.case_id is null
```

### Package Tests (dbt-utils)

Reusable tests from dbt-utils package for common patterns.

**Installation:**

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
```

**Common package tests:**

```yaml
# Recency check - data should be recent
tests:
  - dbt_utils.recency:
      datepart: day
      field: created_at
      interval: 1 # Warn if no data in last 24 hours

# Multi-column uniqueness
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns: ["user_id", "date"]

# Expression validation
tests:
  - dbt_utils.expression_is_true:
      expression: "revenue >= 0"

# Value ranges
tests:
  - dbt_utils.expression_is_true:
      expression: "processing_days between 0 and 365"
```

### Diagnostic Models

Create ephemeral views for data quality monitoring.

**Use for:** Quality metrics you want to inspect manually, not fail builds on.

**Example:**

```sql
-- models/diagnostics/data_quality_summary.sql
{{ config(materialized='view', tags=['diagnostic']) }}

select
    'cases_with_content' as check_name,
    count(*) as total_rows,
    count(case when decision_text is not null then 1 end) as passing_rows,
    count(case when decision_text is null then 1 end) as failing_rows,
    round(100.0 * count(case when decision_text is not null then 1 end) / count(*), 2) as pass_rate
from {{ ref('stg_cases') }}

union all

select
    'valid_date_ranges' as check_name,
    count(*) as total_rows,
    count(case when decision_date >= submission_date then 1 end) as passing_rows,
    count(case when decision_date < submission_date then 1 end) as failing_rows,
    round(100.0 * count(case when decision_date >= submission_date then 1 end) / count(*), 2) as pass_rate
from {{ ref('stg_cases') }}
```

**Usage:**

```bash
# Show diagnostic results interactively
dbt show --select data_quality_summary

# Include in Streamlit dashboard for monitoring
```

### Test Severity

Control whether tests fail builds or just warn:

```yaml
columns:
  - name: optional_field
    description: Field that may be null in some contexts
    tests:
      - not_null:
          severity: warn # Don't fail build, just show warning
```

**Severity levels:**

- `error` (default): Fails the build, stops execution
- `warn`: Shows warning in output but continues build

**When to use `warn`:**

- Known data quality issues you're tracking but can't fix yet
- Aspirational standards not yet fully achieved
- Optional fields with expected nulls in certain contexts
- Monitoring checks that shouldn't block analysis

### Testing Best Practices

1. **Test at every layer:**
   - Staging: Not null on keys, uniqueness, basic quality
   - Intermediate: Business logic correctness
   - Marts: Referential integrity, completeness

2. **Start with schema tests** (fast, declarative)
3. **Add package tests** for common patterns
4. **Write singular tests** for project-specific complex logic
5. **Create diagnostic models** for quality monitoring
6. **Use dashboards** for human review and exploratory validation

## Documentation

Document all models in `schema.yml` files.

**Minimum documentation:**

```yaml
models:
  - name: fct_case_decisions
    description: One row per case decision with analysis metrics. Combines case details, processing metrics, and text analysis.
    columns:
      - name: case_id
        description: Unique identifier for the case (primary key)
      - name: processing_days
        description: Number of calendar days from submission to decision
      - name: decision_sentiment
        description: Sentiment score of decision text (-1 to 1, negative to positive)
```

**Why document:**

- Future you remembers what fields mean
- Agents can understand your data model
- Collaborators can navigate the project
- `dbt docs generate` creates browsable documentation website
- Documentation appears in IDE tooltips and autocomplete

## Common Patterns

### Incremental Models

For large datasets, process only new/changed data:

```sql
{{
    config(
        materialized='incremental',
        unique_key='case_id'
    )
}}

select
    id as case_id,
    submitted_at,
    decision_at,
    updated_at
from {{ source('raw', 'cases') }}

{% if is_incremental() %}
    -- Only process new or updated records
    where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

**When to use:**

- Tables with millions of rows
- Data that only grows (events, transactions)
- Long-running transformations

### Source Freshness

Validate that source data is recent:

```yaml
# models/sources.yml
sources:
  - name: raw
    database: mydb
    freshness:
      warn_after: { count: 24, period: hour }
      error_after: { count: 48, period: hour }
    tables:
      - name: cases
        description: Raw case data from upstream system
```

**Check freshness:**

```bash
dbt source freshness
```

### Snapshots (Slowly Changing Dimensions)

Track historical changes to dimension tables:

```sql
-- snapshots/jurisdiction_snapshot.sql
{% snapshot jurisdiction_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='jurisdiction_id',
      strategy='timestamp',
      updated_at='updated_at',
    )
}}

select * from {{ source('raw', 'jurisdictions') }}

{% endsnapshot %}
```

**Run snapshots:**

```bash
dbt snapshot
```

## Running dbt

### Common Commands

```bash
# Run all models
dbt run

# Run specific model
dbt run --select stg_cases

# Run model and all downstream dependencies
dbt run --select stg_cases+

# Run model and all upstream dependencies
dbt run --select +fct_case_decisions

# Run all models in a directory
dbt run --select staging.*

# Run tests
dbt test

# Run tests for specific model
dbt test --select stg_cases

# Run only schema tests
dbt test --select test_type:schema

# Run only singular tests
dbt test --select test_type:singular

# Generate documentation
dbt docs generate
dbt docs serve  # Opens browser with documentation

# Check source freshness
dbt source freshness

# Run snapshots
dbt snapshot

# Full refresh (rebuild incremental models from scratch)
dbt run --full-refresh

# Dry run (compile SQL without executing)
dbt compile
```

### Selection Syntax

```bash
# By model name
--select model_name

# By directory
--select staging.*
--select marts.fct_*

# Downstream dependencies
--select model_name+

# Upstream dependencies
--select +model_name

# Full lineage (up and downstream)
--select +model_name+

# By tag
--select tag:daily

# Exclude models
--select staging.* --exclude stg_deprecated
```

## Integration with Analysis

### DuckDB (typical academicOps setup)

```python
import duckdb

# Connect to warehouse
conn = duckdb.connect("data/warehouse.db")

# Query materialized dbt models
df = conn.execute("SELECT * FROM fct_case_decisions").df()

# Use in analysis
print(df.describe())
```

### Streamlit

```python
import streamlit as st
import duckdb


@st.cache_data
def load_data():
    """Load data from dbt warehouse"""
    conn = duckdb.connect("data/warehouse.db")
    return conn.execute("SELECT * FROM fct_case_decisions").df()


df = load_data()
st.dataframe(df)
```

### Jupyter

```python
import duckdb
import pandas as pd
import plotly.express as px

# Load from dbt warehouse
conn = duckdb.connect("data/warehouse.db")
df = conn.execute("SELECT * FROM fct_case_decisions").df()

# Analyze
fig = px.histogram(df, x="processing_days")
fig.show()
```

