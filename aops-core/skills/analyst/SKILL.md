---
name: analyst
description: Support academic research data analysis using dbt and Streamlit. Use this skill when working with computational research projects (identified by dbt/ directory, Streamlit apps, or empirical data pipelines). The skill enforces academicOps best practices for reproducible, transparent, self-documenting research with collaborative single-step workflow.
category: instruction
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Skill
version: 2.0.0
permalink: skills-analyst-skill
triggers:
  - "data analysis"
  - "dbt project"
  - "streamlit app"
  - "research pipeline"
---

# Analyst

## Overview

Support academic research data analysis by working collaboratively with dbt (data build tool) and Streamlit dashboards. This skill enforces academicOps methodology: reproducible data pipelines, automated testing, self-documenting code, and fail-fast validation.

**Core principle:** Take ONE action at a time (generate a chart, update database, create a test), then yield to the user for feedback before proceeding.

## 🚨 CRITICAL: Research Data is Immutable

Source datasets, ground truth labels, experimental records, and research configurations are SACRED. NEVER modify, reformat, or "fix" them. If infrastructure doesn't support a format: HALT and report. Violations are scholarly misconduct.

## 🚨 CRITICAL: Transformation Boundary Rule

**ALL data transformation happens in dbt. Period.**

This is non-negotiable for academic integrity, reproducibility, and auditability.

| Layer         | Allowed                                                                 | Prohibited                                                        |
| ------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **dbt**       | ALL SQL transformations, joins, aggregations, filtering, business logic | -                                                                 |
| **Streamlit** | Display, formatting, interactive filtering of PRE-COMPUTED data         | SQL that transforms, joins, aggregates, or applies business logic |

### Why This Matters (Academic Integrity)

1. **Reproducibility**: Anyone can re-run `dbt build` and get identical results
2. **Auditability**: Transformation logic is version-controlled and testable
3. **Transparency**: Reviewers see exactly how data was processed
4. **Testing**: dbt tests PROVE transformations work correctly

### The Rule in Practice

**Need a new metric?** → Create a dbt mart with tests
**Need to filter data?** → Pre-compute filtered views in dbt OR use Streamlit widgets on EXISTING columns (no new calculations)
**Need to join tables?** → Create a dbt model that joins them
**Need aggregations?** → Create a dbt mart with the aggregations

### Streamlit: Display Layer ONLY

Streamlit scripts may:

- ✅ `SELECT * FROM mart_name` (read pre-computed data)
- ✅ `WHERE column = :user_selection` (filter on existing columns)
- ✅ Format numbers, dates for display
- ✅ Create interactive widgets that filter existing data
- ✅ Render charts from pre-computed metrics

Streamlit scripts must NEVER:

- ❌ `SELECT SUM(...) GROUP BY ...` (aggregation = transformation)
- ❌ `SELECT a.*, b.* FROM a JOIN b` (joins = transformation)
- ❌ `SELECT CASE WHEN ... END` (business logic = transformation)
- ❌ Calculate derived metrics inline
- ❌ Apply any formula that changes the meaning of data

### If You're Tempted to Transform in Streamlit

**STOP.** Create a dbt mart instead:

1. Create `marts/mart_name.sql` with the transformation
2. Add tests in `schema.yml` proving it works
3. Run `dbt build --select mart_name`
4. THEN query the mart from Streamlit

This takes more time. That's the point. Transformations deserve scrutiny.

## Documentation Index

### Instructions (_CHUNKS/)

- **Investigation**: [[instructions/data-investigation.md]], [[instructions/exploratory-analysis.md]]
- **Research docs**: [[instructions/research-documentation.md]] (REQUIRED), [[instructions/methodology-files.md]], [[instructions/methods-vs-methodology.md]], [[instructions/experiment-logging.md]]
- **Technical**: [[instructions/dbt-workflow.md]], [[instructions/streamlit-workflow.md]]

### References

[[references/dbt-workflow.md]], [[references/streamlit-patterns.md]], [[references/context-discovery.md]]

### Statistical Analysis (references/)

Start with [[references/statistical-analysis.md]] (complete guide). Also: [[references/test_selection_guide.md]], [[references/assumptions_and_diagnostics.md]], [[references/effect_sizes_and_power.md]], [[references/bayesian_statistics.md]], [[references/reporting_standards.md]].

### Python Libraries

Core libraries: [[references/matplotlib.md]], [[references/seaborn.md]], [[references/statsmodels.md]], [[references/streamlit.md]]. Use `python-dev` skill for code standards.

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

`"I've reviewed the project context. This is a <research topic> project investigating <questions>. The DBT pipeline has <N> staging models and <M> mart models. I see existing work on <areas>. What would you like me to help with?"`

## Follow Data Access Workflow

**🚨 CRITICAL RULE: ALL data access MUST go through dbt models. NEVER query upstream sources directly.**

**🚨 REMINDER: If you need to transform data, that transformation MUST be a dbt model with tests. See "Transformation Boundary Rule" above.**

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

**See:** [[references/dbt-workflow.md]] for detailed dbt patterns

## Follow DBT Model Workflow

Create or modify dbt models following academicOps layered architecture.

**For detailed dbt workflow including model layers, single-step workflow, and examples, see [[instructions/dbt-workflow.md]]**

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

**See:** [[instructions/dbt-workflow.md]] for complete workflow details and [[references/dbt-workflow.md]] for comprehensive patterns

## Follow Visualization Workflow

Create Streamlit visualizations following single-step collaborative pattern.

**🚨 REMINDER: Streamlit is DISPLAY ONLY. No transformations. See "Transformation Boundary Rule" above.**

**For detailed Streamlit workflow including structure, single-step patterns, and examples, see `@reference _CHUNKS/streamlit-workflow.md]]**

### Quick Reference: Streamlit Pattern

Load data → STOP → Create chart → STOP → Add interactivity → STOP. One change at a time. **Hot Reloads**: Don't restart Streamlit; it auto-reloads. See [[instructions/streamlit-workflow.md]].

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

### Pipeline/Template Validation Tests

When testing LLM pipelines or templated content, validate **substantive content** not just error patterns:

- ✅ Check content length minimums (e.g., criteria block > 100 chars)
- ✅ Verify required sections exist AND have content
- ✅ Use position-based length for multiline content (regex `.*?` doesn't cross newlines)
- ❌ Don't just check for specific error strings - upstream bugs are unpredictable

**See:** [[references/dbt-workflow.md]] for complete testing patterns

## Follow Data Investigation Workflow

When investigating data quality issues (missing values, unexpected patterns, join coverage), create REUSABLE investigation scripts in `analyses/` directory. Never use throwaway one-liners for data investigation.

**For complete workflow, script templates, and when to create investigation scripts, see `@reference _CHUNKS/data-investigation.md]]**

## Exploratory Analysis

When exploring data patterns and relationships, follow collaborative discovery process. Take one analytical step at a time, yielding to user after each finding.

**For complete exploration workflow and anti-patterns, see `@reference _CHUNKS/exploratory-analysis.md]]**

**NOTE:** For data quality issues (missing values, unexpected nulls), use Data Investigation Workflow instead.

## Documentation Philosophy

**Self-documenting work**: Do NOT create separate analysis reports or random documentation files.

**🚨 CRITICAL: Research projects must follow STRICT documentation structure. See `@reference _CHUNKS/research-documentation.md]] for complete requirements.**

### Required Documentation Structure

Research projects MUST maintain:

- **README.md** - Project overview and quick start
- **METHODOLOGY.md** - Research design and approach (see `@reference _CHUNKS/methodology-files.md]])
- **methods/*.md** - Technical implementation details (see `@reference _CHUNKS/methods-vs-methodology.md]])
- **data/README.md** - Data sources and schema
- **dbt/schema.yml** - Model and column documentation
- **experiments/YYYYMMDD-description/** - Experimental work (see `@reference _CHUNKS/experiment-logging.md]])

### Where Analysis Documentation Lives

1. **Streamlit dashboards** - Interactive exploration and validation
2. **Jupyter notebooks** - Detailed analysis with inline markdown (in experiments/ if exploratory)
3. **GitHub issues** - Track analysis tasks and decisions
4. **Code comments** - Explain analytical decisions in dbt models
5. **Commit messages** - Document why changes were made
6. **dbt schema.yml** - Document model purposes and column meanings
7. **methods/*.md** - Technical method specifications

### Prohibited

❌ Create `analysis_report.md]] or any random markdown files ❌ Create`findings_summary.docx` ❌ Proliferate documentation files without defined structure ❌ Leave documentation stale when code changes

✅ Follow strict structure defined in [[instructions/research-documentation.md]] ✅ Update documentation in SAME commit as code changes ✅ One source of truth for each piece of information

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

## Quick Reference

See [[references/quick-reference-commands.md]] for common dbt, Streamlit, and DuckDB commands.
