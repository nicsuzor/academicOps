---
name: analyst
description: Support academic research data analysis using dbt and Streamlit. Use this skill when working with computational research projects (identified by dbt/ directory, Streamlit apps, or empirical data pipelines). The skill enforces academicOps best practices for reproducible, transparent, self-documenting research with collaborative single-step workflow.
---

# Analyst

## Overview

Support academic research data analysis by working collaboratively with dbt (data build tool) and Streamlit dashboards. This skill enforces academicOps methodology: reproducible data pipelines, automated testing, self-documenting code, and fail-fast validation.

**Core principle:** Take ONE action at a time (generate a chart, update database, create a test), then yield to the user for feedback before proceeding.

## When to Use This Skill

Invoke this skill when:

1. **Working in computational research projects** - Directory contains `dbt/`, Streamlit apps, or empirical data pipelines
2. **User requests data analysis** - "Analyze X", "Create a chart showing Y", "Explore the relationship between Z"
3. **Building or updating dashboards** - Streamlit visualization work
4. **Creating or modifying dbt models** - Data transformation pipelines
5. **Validating data quality** - Adding tests, checking consistency

**Key indicators in project structure:**
- `dbt/models/` directory (staging, intermediate, marts)
- `streamlit/` or `.py` files with Streamlit code
- `data/warehouse.db` or similar analytical database
- Academic research focus (papers, empirical analysis)

## Workflow Decision Tree

```
START
│
├─ Is this a new analysis task?
│  ├─ YES → Go to: Context Discovery
│  └─ NO → Is context already loaded?
│     ├─ YES → Go to: Task Execution
│     └─ NO → Go to: Context Discovery
│
Context Discovery (REQUIRED FIRST STEP)
│
├─ Read project context files:
│  ├─ README.md (current directory + all parents to project root)
│  ├─ data/README.md (if exists)
│  └─ data/projects/[project-name].md (if exists)
│
├─ Identify project conventions:
│  ├─ Research questions
│  ├─ Data sources and access patterns
│  ├─ Existing dbt models (list them)
│  ├─ Testing strategy
│  └─ Project-specific rules
│
└─ Proceed to: Task Execution
│
Task Execution
│
├─ What type of task?
│  ├─ Data access → Go to: Data Access Workflow
│  ├─ Visualization → Go to: Visualization Workflow
│  ├─ dbt model → Go to: DBT Model Workflow
│  ├─ Testing → Go to: Testing Workflow
│  └─ Exploration → Go to: Exploratory Analysis
│
└─ After completing ONE step:
   ├─ Report results to user
   ├─ Explain what was done
   └─ STOP and wait for user feedback
```

## Context Discovery

**CRITICAL FIRST STEP:** Before any analysis work, automatically discover and read project context.

### Required Context Files

1. **Project README files**
   - Current working directory `README.md`
   - All parent directories up to project root (e.g., `papers/automod/`, `projects/buttermilk/`)
   - Purpose: Understand research questions, conventions, project structure

2. **Data README**
   - `data/README.md` in the project
   - Purpose: Understand data sources, schema, access patterns

3. **Project overview**
   - `data/projects/[project-name].md` corresponding to current project
   - Purpose: Strategic context, goals, status

### Context Extraction

From these files, identify:

- **Research questions** - What is this project investigating?
- **Data sources** - Where does data come from? (BigQuery, APIs, files?)
- **Existing dbt models** - What models already exist? (Run `ls -1 dbt/models/**/*.sql`)
- **Conventions** - Naming patterns, coding standards, project-specific rules
- **Testing strategy** - What tests exist? What quality expectations?
- **Tools and technologies** - DuckDB? PostgreSQL? Specific Python packages?

**Example context discovery:**

```bash
# List existing dbt models
ls -1 dbt/models/staging/*.sql dbt/models/marts/*.sql

# Check for Streamlit apps
ls -1 streamlit/*.py

# Understand project structure
cat README.md
cat data/README.md
```

After context discovery, summarize findings to user:

"I've reviewed the project context. This is a [research topic] project investigating [questions]. The dbt pipeline has [N] staging models and [M] mart models. I see existing work on [areas]. What would you like me to help with?"

## Follow Data Access Workflow

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
import duckdb
conn = duckdb.connect('data/warehouse.db')
df = conn.execute("SELECT * FROM fct_case_decisions").df()

# Or reference in Streamlit
@st.cache_data
def load_data():
    conn = duckdb.connect('data/warehouse.db')
    return conn.execute("SELECT * FROM fct_case_decisions").df()
```

### Why This Matters

- **Reproducibility**: Queries are version-controlled in dbt
- **Data governance**: dbt models are single source of truth
- **Quality**: Data passes through validated transformation pipeline
- **Consistency**: All analysts use same transformations

**See:** `references/dbt-workflow.md` for detailed dbt patterns

## Follow DBT Model Workflow

Create or modify dbt models following academicOps layered architecture.

### Before Creating New Model: Check for Duplicates

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

### Model Layers

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

### Follow Single-Step Workflow

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

**See:** `references/dbt-workflow.md` for model patterns and testing strategies

## Follow Visualization Workflow

Create Streamlit visualizations following single-step collaborative pattern.

### Streamlit Structure

Standard Streamlit app structure for academicOps projects:

```python
import streamlit as st
import duckdb
import plotly.express as px

# Page config
st.set_page_config(page_title="Project Analysis", layout="wide")

# Data loading (cached)
@st.cache_data
def load_data():
    conn = duckdb.connect('data/warehouse.db')
    return conn.execute("SELECT * FROM fct_cases").df()

# Main app
def main():
    st.title("Case Analysis Dashboard")

    df = load_data()

    # Filters in sidebar
    with st.sidebar:
        st.header("Filters")
        status_filter = st.multiselect("Status", df['status'].unique())

    # Apply filters
    if status_filter:
        df = df[df['status'].isin(status_filter)]

    # Visualizations
    st.header("Overview Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cases", len(df))
    col2.metric("Avg Processing Days", df['processing_days'].mean().round(1))
    col3.metric("Completion Rate", f"{(df['status']=='published').mean():.1%}")

    # Chart
    fig = px.histogram(df, x='processing_days', title='Processing Time Distribution')
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
```

### Follow Single-Step Visualization Workflow

**Step 1: Load data from dbt model**

```python
import streamlit as st
import duckdb

@st.cache_data
def load_data():
    conn = duckdb.connect('data/warehouse.db')
    return conn.execute("SELECT * FROM fct_cases").df()

df = load_data()
st.dataframe(df.head())
```

**STOP. Show to user. Confirm data is correct.**

**Step 2: Create single chart** (only after user confirms data)

```python
import plotly.express as px

fig = px.histogram(df, x='processing_days', title='Processing Time Distribution')
st.plotly_chart(fig, use_container_width=True)
```

**STOP. Show to user. Get feedback on chart.**

**Step 3: Add interactivity** (only after user approves chart)

```python
with st.sidebar:
    status_filter = st.multiselect("Status", df['status'].unique())

if status_filter:
    df = df[df['status'].isin(status_filter)]
```

**STOP. Show to user. Confirm filter works as expected.**

**Continue this pattern:** One change at a time, user feedback, then proceed.

**See:** `references/streamlit-patterns.md` for visualization best practices

## Follow Testing Workflow

Add tests to validate data quality at every pipeline stage.

### Testing Strategy

Use appropriate test type for the validation:

| Test Type | Use For | Example |
|-----------|---------|---------|
| **Schema tests** | Column-level checks | not_null, unique, accepted_values |
| **Singular tests** | Multi-column logic | Date range validation, cross-table consistency |
| **Package tests** | Common patterns | Recency checks, multi-column uniqueness |
| **Diagnostic models** | Quality monitoring | Aggregated metrics for manual review |

### Follow Single-Step Testing Workflow

**Step 1: Identify what to test**

Review the model and ask:
- Which columns should never be null?
- Which columns should be unique?
- Are there accepted value lists?
- Any date range logic to validate?

**STOP. Discuss with user which tests to add.**

**Step 2: Add schema tests** (after user agrees on test plan)

```yaml
# dbt/schema.yml
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
              values: ['pending', 'reviewed', 'published']
```

**STOP. Show to user.**

**Step 3: Run tests** (after user approves test definitions)

```bash
dbt test --select stg_cases
```

**STOP. Report results. If failures, discuss with user before fixing.**

**Step 4: Add singular test if needed** (complex validation)

```sql
-- tests/assert_decision_dates_logical.sql
select
    case_id,
    submission_date,
    decision_date
from {{ ref('stg_cases') }}
where decision_date < submission_date
```

**STOP. Show test SQL to user.**

**Step 5: Run singular test**

```bash
dbt test --select test_name:assert_decision_dates_logical
```

**STOP. Report results.**

### Test Severity

Use `severity: warn` for known issues or aspirational standards:

```yaml
tests:
  - not_null:
      severity: warn  # Don't fail build, just warn
```

**See:** `references/dbt-workflow.md` for complete testing patterns

## Follow Data Investigation Workflow

**🚨 CRITICAL: Axiom #15 - WRITE FOR THE LONG TERM**

When investigating data issues (missing values, unexpected patterns, data quality problems), create REUSABLE investigation scripts in the `analyses/` directory. NEVER use throwaway `python -c` one-liners for data investigation.

### When to Create Investigation Scripts

Create reusable scripts for:
- ✅ **Root cause analysis** - Tracing why data is missing or incorrect
- ✅ **Coverage analysis** - Checking how much data satisfies conditions
- ✅ **Data quality checks** - Investigating completeness, accuracy
- ✅ **Schema exploration** - Understanding structure of complex JSON/struct fields
- ✅ **Join validation** - Checking coverage of joins between tables

Use throwaway queries ONLY for:
- ❌ Quick calculations (simple arithmetic, counts)
- ❌ Checking if single command worked
- ❌ One-time data fixes

### Investigation Script Structure

Save scripts in `analyses/` directory within the dbt project:

```
dbt_project/
├── analyses/
│   ├── investigate_missing_record_ids.py
│   ├── check_ground_truth_coverage.py
│   └── validate_scorer_completeness.py
├── models/
└── tests/
```

**Script template:**

```python
"""
Investigation: [Brief description of what this investigates]

Context: [Why this investigation is needed]
Date: [YYYY-MM-DD]
Issue: [Link to GitHub issue if applicable]
"""
import duckdb
from google.cloud import bigquery
import pandas as pd

def investigate_missing_values(table_name: str, column_name: str):
    """Check what proportion of records have missing values."""
    conn = duckdb.connect('data/warehouse.db')

    query = f"""
    SELECT
        COUNT(*) as total_rows,
        COUNTIF({column_name} IS NOT NULL) as with_value,
        COUNTIF({column_name} IS NULL) as missing_value,
        ROUND(100.0 * COUNTIF({column_name} IS NOT NULL) / COUNT(*), 2) as pct_complete
    FROM {table_name}
    """

    result = conn.execute(query).df()
    print(f"=== {column_name} completeness in {table_name} ===")
    print(result)
    return result

if __name__ == "__main__":
    # Example investigation
    investigate_missing_values('judge_scores', 'expected_violating')
```

### Follow Investigation Workflow

**Step 1: Create investigation script**

```bash
touch dbt_project/analyses/investigate_issue.py
```

Add docstring explaining WHAT you're investigating and WHY.

**STOP. Show script to user.**

**Step 2: Run investigation**

```bash
cd dbt_project
uv run python analyses/investigate_issue.py
```

**STOP. Share findings with user.**

**Step 3: Commit investigation script**

After investigation is complete and fix is implemented, commit the script:

```bash
git add analyses/investigate_issue.py
git commit -m "chore: Add investigation script for [issue]

Documents investigation into [problem]. Found [key finding].
Used to diagnose issue #[number].
"
```

**Why This Matters:**
- **Reproducibility** - Can rerun after data changes
- **Documentation** - Shows how issue was diagnosed
- **Testing** - Can validate fix by running investigation again
- **Learning** - Future analysts understand the problem
- **Verification** - Can compare before/after metrics

### When NOT to Create Scripts

For simple one-time checks, throwaway queries are fine:

```bash
# Quick count - OK as one-liner
uv run python -c "import duckdb; print(duckdb.connect('data/warehouse.db').execute('SELECT COUNT(*) FROM fct_cases').fetchone())"

# Checking if column exists - OK as one-liner
uv run python -c "import duckdb; conn = duckdb.connect('data/warehouse.db'); print(conn.execute('PRAGMA table_info(fct_cases)').df())"
```

But if you run MORE THAN ONE query to investigate something, that's a signal to create a script.

## Exploratory Analysis

When exploring data to understand patterns, follow collaborative discovery process.

**NOTE:** If you find yourself running multiple queries to investigate a DATA ISSUE (missing values, unexpected nulls, join problems), switch to the Data Investigation Workflow above and create a reusable script.

Exploratory analysis is for understanding PATTERNS and RELATIONSHIPS in clean data. Data investigation is for diagnosing DATA QUALITY problems.

### Exploration Pattern

**Step 1: Load data and show basic statistics**

```python
import duckdb
conn = duckdb.connect('data/warehouse.db')
df = conn.execute("SELECT * FROM fct_cases").df()

print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print("\nSummary statistics:")
print(df.describe())
```

**STOP. Share findings with user. Ask: "What would you like to explore?"**

**Step 2: Create single visualization based on user direction**

```python
import plotly.express as px
fig = px.scatter(df, x='submission_date', y='processing_days',
                 color='status', title='Processing Time Over Time')
fig.show()
```

**STOP. Discuss findings. Ask: "What pattern should we investigate next?"**

**Step 3: Follow user guidance for next exploration**

Continue one step at a time, yielding to user after each finding.

### Exploratory Analysis Anti-Patterns

❌ **Don't** create comprehensive analysis notebook without user input
❌ **Don't** generate 10 charts at once
❌ **Don't** make assumptions about what's interesting
❌ **Don't** query upstream data sources directly

✅ **Do** take one analytical step at a time
✅ **Do** explain each finding and ask for direction
✅ **Do** use dbt models for all data access
✅ **Do** document interesting findings in code comments

## Documentation Philosophy

**Self-documenting work**: Do NOT create separate analysis reports or documentation files.

### Where to Document

1. **Streamlit dashboards** - Interactive exploration and validation
2. **Jupyter notebooks** - Detailed analysis with inline markdown
3. **GitHub issues** - Track analysis tasks and decisions
4. **Code comments** - Explain analytical decisions in dbt models
5. **Commit messages** - Document why changes were made
6. **dbt schema.yml** - Document model purposes and column meanings

### What NOT to Do

❌ Create `analysis_report.md`
❌ Create `findings_summary.docx`
❌ Create separate documentation for what code already shows

✅ Put explanations in Jupyter markdown cells
✅ Put findings in Streamlit dashboard text
✅ Put decisions in GitHub issue comments

## Collaborative Workflow Principles

**One step at a time:**

1. Perform ONE action (create chart, write model, run test)
2. Show results to user
3. Explain what was done and what it means
4. STOP and wait for user feedback
5. Proceed based on user direction

**Never:**
- Create multiple artifacts without checkpoints
- Make assumptions about next steps
- Implement complex workflows end-to-end without user input

**Always:**
- Explain options and ask for user preference
- Show intermediate results
- Yield control back to user frequently

## Quick Reference Commands

```bash
# List existing dbt models
ls -1 dbt/models/staging/*.sql dbt/models/intermediate/*.sql dbt/models/marts/*.sql

# Run specific dbt model
dbt run --select model_name

# Run tests for model
dbt test --select model_name

# Run Streamlit app
streamlit run streamlit/dashboard.py

# Check dbt lineage
dbt docs generate
dbt docs serve

# Query warehouse (DuckDB)
duckdb data/warehouse.db -c "SELECT * FROM fct_cases LIMIT 10"
```

## Resources

This skill includes detailed reference documentation:

### references/dbt-workflow.md
Comprehensive dbt patterns including:
- Data access policy (why no direct upstream queries)
- Model layering (staging, intermediate, marts)
- Testing strategies (schema, singular, package tests)
- Documentation practices
- Common patterns (incremental models, source freshness)

### references/streamlit-patterns.md
Streamlit dashboard best practices including:
- Standard app structure
- Data loading and caching
- Interactive components (filters, selections)
- Visualization libraries (Plotly, Altair)
- Layout patterns (columns, tabs, expanders)

### references/context-discovery.md
Guide to finding and reading project context:
- Required context files (README, data docs, project overview)
- How to identify project conventions
- What information to extract
- Context summarization template
