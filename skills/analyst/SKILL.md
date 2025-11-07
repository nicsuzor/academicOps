---
name: analyst
description: Support academic research data analysis using dbt and Streamlit. Use
  this skill when working with computational research projects (identified by dbt/
  directory, Streamlit apps, or empirical data pipelines). The skill enforces academicOps
  best practices for reproducible, transparent, self-documenting research with collaborative
  single-step workflow.
permalink: aops/skills/analyst/skill
---

# Analyst

## Overview

Support academic research data analysis by working collaboratively with dbt (data build tool) and Streamlit dashboards. This skill enforces academicOps methodology: reproducible data pipelines, automated testing, self-documenting code, and fail-fast validation.

**Core principle:** Take ONE action at a time (generate a chart, update database, create a test), then yield to the user for feedback before proceeding.

## Documentation Index

This skill includes both inline guidance and detailed reference documentation:

### Core Workflow Documentation (Inline)

- Context Discovery - How to discover project context
- Data Access Workflow - Critical rules for accessing data through dbt
- Testing Workflow - Adding tests to validate data quality
- Data Investigation - Reusable investigation scripts
- Exploratory Analysis - Collaborative data exploration
- Quick Reference Commands

### Research Documentation Standards (_CHUNKS/)

- `_CHUNKS/research-documentation.md` - **REQUIRED documentation structure and maintenance rules**
- `_CHUNKS/methodology-files.md` - What goes in METHODOLOGY.md files
- `_CHUNKS/methods-vs-methodology.md` - Distinguishing METHODS from METHODOLOGY
- `_CHUNKS/experiment-logging.md` - Experiment directory structure and lifecycle

### Detailed Technical Workflows (_CHUNKS/)

- `_CHUNKS/dbt-workflow.md` - dbt model creation and data access patterns
- `_CHUNKS/streamlit-workflow.md` - Streamlit visualization workflow

### Additional Resources (references/)

- `references/dbt-workflow.md` - Comprehensive dbt patterns and testing strategies
- `references/streamlit-patterns.md` - Visualization best practices and layout patterns
- `references/context-discovery.md` - Guide to finding and reading project context

### Statistical Analysis (references/)

- `references/statistical-analysis.md` - **Complete guide to hypothesis testing and statistical analysis**
- `references/test_selection_guide.md` - Choosing the right statistical test
- `references/assumptions_and_diagnostics.md` - Checking and validating statistical assumptions
- `references/effect_sizes_and_power.md` - Effect sizes, confidence intervals, and power analysis
- `references/bayesian_statistics.md` - Bayesian alternatives and Bayes factors
- `references/reporting_standards.md` - APA-style statistical reporting

### Data Science References (references/)

- `references/MATPLOTLIB.md` → Visualization with matplotlib
- `references/SEABORN.md` → Statistical visualization with seaborn
- `references/STATSMODELS.md` → Statistical modeling and econometrics
- `references/PYTHON-DEV.md` → Python best practices and development standards

**Note**: Chunk files are loaded on-demand when detailed technical specifications are needed. Use `@reference _CHUNKS/filename.md` or `@references/filename.md` to load specific documentation.

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

conn = duckdb.connect("data/warehouse.db")
df = conn.execute("SELECT * FROM fct_case_decisions").df()


# Or reference in Streamlit
@st.cache_data
def load_data():
    conn = duckdb.connect("data/warehouse.db")
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

**For detailed dbt workflow including model layers, single-step workflow, and examples, see `@reference _CHUNKS/dbt-workflow.md`**

### Quick Reference: Model Layers

1. **Staging (`stg_*`)** - Clean and standardize raw data (no business logic)
2. **Intermediate (`int_*`)** - Business logic transformations (can be ephemeral)
3. **Marts (`fct_*`, `dim_*`)** - Analysis-ready datasets (materialized)

### Quick Reference: Workflow Pattern

1. Create model file → STOP, show user
2. Add documentation → STOP, show user
3. Add tests → STOP, show user
4. Run model and tests → STOP, report results

**ALWAYS check for duplicate models before creating new ones.**

**See:** `_CHUNKS/dbt-workflow.md` for complete workflow details and `references/dbt-workflow.md` for comprehensive patterns

## Follow Visualization Workflow

Create Streamlit visualizations following single-step collaborative pattern.

**For detailed Streamlit workflow including structure, single-step patterns, and examples, see `@reference _CHUNKS/streamlit-workflow.md`**

### Quick Reference: Workflow Pattern

1. Load data from dbt model → STOP, confirm data
2. Create single chart → STOP, get feedback
3. Add interactivity → STOP, confirm works
4. Continue one change at a time

**Key principle:** Always load data through dbt models using DuckDB, cache with `@st.cache_data`

**See:** `_CHUNKS/streamlit-workflow.md` for complete workflow and `references/streamlit-patterns.md` for best practices

## Follow Testing Workflow

Add tests to validate data quality at every pipeline stage.

### Testing Strategy

Use appropriate test type for the validation:

| Test Type             | Use For             | Example                                        |
| --------------------- | ------------------- | ---------------------------------------------- |
| **Schema tests**      | Column-level checks | not_null, unique, accepted_values              |
| **Singular tests**    | Multi-column logic  | Date range validation, cross-table consistency |
| **Package tests**     | Common patterns     | Recency checks, multi-column uniqueness        |
| **Diagnostic models** | Quality monitoring  | Aggregated metrics for manual review           |

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
              values: ["pending", "reviewed", "published"]
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
      severity: warn # Don't fail build, just warn
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
    conn = duckdb.connect("data/warehouse.db")

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
    investigate_missing_values("judge_scores", "expected_violating")
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

conn = duckdb.connect("data/warehouse.db")
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

fig = px.scatter(
    df,
    x="submission_date",
    y="processing_days",
    color="status",
    title="Processing Time Over Time",
)
fig.show()
```

**STOP. Discuss findings. Ask: "What pattern should we investigate next?"**

**Step 3: Follow user guidance for next exploration**

Continue one step at a time, yielding to user after each finding.

### Exploratory Analysis Anti-Patterns

❌ **Don't** create comprehensive analysis notebook without user input ❌ **Don't** generate 10 charts at once ❌ **Don't** make assumptions about what's interesting ❌ **Don't** query upstream data sources directly

✅ **Do** take one analytical step at a time ✅ **Do** explain each finding and ask for direction ✅ **Do** use dbt models for all data access ✅ **Do** document interesting findings in code comments

## Documentation Philosophy

**Self-documenting work**: Do NOT create separate analysis reports or random documentation files.

**🚨 CRITICAL: Research projects must follow STRICT documentation structure. See `@reference _CHUNKS/research-documentation.md` for complete requirements.**

### Required Documentation Structure

Research projects MUST maintain:

- **README.md** - Project overview and quick start
- **METHODOLOGY.md** - Research design and approach (see `@reference _CHUNKS/methodology-files.md`)
- **methods/*.md** - Technical implementation details (see `@reference _CHUNKS/methods-vs-methodology.md`)
- **data/README.md** - Data sources and schema
- **dbt/schema.yml** - Model and column documentation
- **experiments/YYYYMMDD-description/** - Experimental work (see `@reference _CHUNKS/experiment-logging.md`)

### Where Analysis Documentation Lives

1. **Streamlit dashboards** - Interactive exploration and validation
2. **Jupyter notebooks** - Detailed analysis with inline markdown (in experiments/ if exploratory)
3. **GitHub issues** - Track analysis tasks and decisions
4. **Code comments** - Explain analytical decisions in dbt models
5. **Commit messages** - Document why changes were made
6. **dbt schema.yml** - Document model purposes and column meanings
7. **methods/*.md** - Technical method specifications

### Prohibited

❌ Create `analysis_report.md` or any random markdown files ❌ Create `findings_summary.docx` ❌ Proliferate documentation files without defined structure ❌ Leave documentation stale when code changes

✅ Follow strict structure defined in `_CHUNKS/research-documentation.md` ✅ Update documentation in SAME commit as code changes ✅ One source of truth for each piece of information

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

This skill includes comprehensive documentation organized in three tiers:

### Research Documentation Standards (_CHUNKS/)

**Load these to understand required project documentation:**

- `_CHUNKS/research-documentation.md` - Required documentation structure and maintenance rules
- `_CHUNKS/methodology-files.md` - What goes in METHODOLOGY.md files
- `_CHUNKS/methods-vs-methodology.md` - Distinguishing METHODS from METHODOLOGY
- `_CHUNKS/experiment-logging.md` - Experiment directory structure and lifecycle

### Technical Workflow Details (_CHUNKS/)

**Load these for detailed technical workflows:**

- `_CHUNKS/dbt-workflow.md` - dbt model creation, data access patterns, and workflow
- `_CHUNKS/streamlit-workflow.md` - Streamlit visualization workflow and structure

### Comprehensive Reference Documentation (references/)

**Load these for in-depth best practices:**

- `references/dbt-workflow.md` - Complete dbt patterns (testing, documentation, common patterns)
- `references/streamlit-patterns.md` - Complete Streamlit best practices (layout, components, libraries)
- `references/context-discovery.md` - Project context discovery guide

**Usage**: Reference chunk files using `@reference _CHUNKS/filename.md` to load detailed documentation on-demand.
