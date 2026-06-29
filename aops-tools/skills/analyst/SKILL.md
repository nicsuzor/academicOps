---
name: analyst
type: skill
description: Support academic research data analysis with technology-agnostic principles — research-data immutability, a versioned/tested/reproducible transformation layer, statistical methodology, and self-documenting research. Use this skill for any computational research project with an empirical data pipeline. The skill enforces academicOps best practices for reproducible, transparent research with a collaborative single-step workflow. Tech-specific how-to (dbt, Streamlit, Python plotting/stats) lives in the aops-extras package.
category: instruction
triggers:
  - "data analysis"
  - "research pipeline"
  - "empirical data"
  - "research data analysis"
  - "research project"
  - "methodology"
  - "research question"
  - "data collection"
  - "empirical analysis"
  - "dry run"
  - "research methodology"
  - "empirical research"
  - "methodological integrity"
  - "pilot study"
modifies_files: true
needs_task: true
mode: execution
domain:
  - academic
  - development
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Skill
version: 2.1.0
permalink: skills-analyst-skill
---

# Analyst

> **Taxonomy note**: This skill provides tech-agnostic domain principles (HOW) for research data analysis. Technology-specific how-to (dbt, Streamlit, Python plotting/stats) lives in the **aops-extras** package skills. See [[aops-core/skills/remember/references/TAXONOMY.md]] for the skill/workflow distinction.

## Overview

Support academic research data analysis through technology-agnostic principles: reproducible data pipelines, automated testing, self-documenting code, and fail-fast validation. The principles here hold regardless of which transformation engine or dashboard tool you use. When you have settled on specific tooling, pair this skill with the relevant aops-extras skill (`dbt`, `streamlit`, `python-viz`) for the concrete commands.

**Core principle:** Take ONE action at a time (generate a chart, update database, create a test), then yield to the user for feedback before proceeding.

**Academic research disposition (non-negotiable floor for all academic work):**

- **Data immutability** — source datasets, ground-truth labels, and research configs are sacred; never modify, reformat, or "fix" them — HALT and report rather than reshaping data to fit infrastructure. Violations are scholarly misconduct.
- **Research questions drive design** — methods serve the question; restate the question, confirm the method fits it, and refuse convenience shortcuts that compromise validity. A result that doesn't answer the question is worthless however technically sound.
- **Methodological justification** — ensure all model, variable, and sample choices are justified by the research design, not by computational convenience. Do not drop variables, models, or conditions, or simplify experimental designs unless there is a clear methodological justification. Preserve all theoretically meaningful distinctions.
- **Dry run / pilot verification** — before full-scale execution, run a qualitative pilot audit. Evaluate representative samples of actual outputs for content substance, completeness across all conditions, edge-case behavior, and face validity. Do not declare a dry run successful based on error-free execution or aggregate statistics alone.
- **Reproducibility & versioning** — every transformation is version-controlled, testable by re-running, and separated from display (never compute in the display layer).
- **Methodological transparency** — name the assumptions and limitations a result rests on; flag uncertainty rather than smoothing it over.
- **Fail-fast on data quality** — stop and report quality problems rather than patching around them; the discovery IS the result.
- **Report as argument** — structure research reports as cohesive arguments where every chapter, section, and visualization directly supports a specific claim. Ground all reported metrics in their practical and theoretical implications. Collaborate section-by-section with the user to refine narrative framing.

(The interactive research head **Ida** carries this same disposition inline in her persona — `aops-core/agents/ida.md`. This skill states it directly so it holds regardless of which agent invokes it.) The data-pipeline specifics below EXTEND this floor.

## 🚨 CRITICAL: Research Data is Immutable

**Source data immutability** (stated in the disposition above: datasets, ground-truth labels, and research configs are sacred; HALT and report rather than reshaping data; violations are scholarly misconduct). The analyst-specific application:

**Data directory separation**: Local data files (`data/`) and build output directories (`output/`, `_book/`, etc.) MUST NOT overlap. Build tools clean their output directories — any data stored there will be destroyed. See [[instructions/research-documentation.md#data-directory-separation-critical]] for the full convention.

## 🚨 CRITICAL: Transformation Layer vs Presentation Layer

**ALL data transformation happens in a versioned, tested, reproducible transformation layer. The presentation layer ONLY displays pre-computed data. Period.**

This is non-negotiable for academic integrity, reproducibility, and auditability. It is a property of the _architecture_, not of any particular tool. (e.g. the transformation layer might be a dbt project, a SQL pipeline, or scripted notebooks under version control; the presentation layer might be a Streamlit dashboard, a static report, or a notebook viewer. See the aops-extras `dbt` and `streamlit` skills for those concrete implementations.)

| Layer              | Allowed                                                             | Prohibited                                                         |
| ------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Transformation** | ALL transformations, joins, aggregations, filtering, business logic | -                                                                  |
| **Presentation**   | Display, formatting, interactive filtering of PRE-COMPUTED data     | Any operation that transforms, joins, aggregates, or applies logic |

### Why This Matters (Academic Integrity)

1. **Reproducibility**: Anyone can re-run the transformation layer and get identical results
2. **Auditability**: Transformation logic is version-controlled and testable
3. **Transparency**: Reviewers see exactly how data was processed
4. **Testing**: Tests in the transformation layer PROVE transformations work correctly

### The Rule in Practice

**Need a new metric?** → Add it to the transformation layer with tests
**Need to filter data?** → Pre-compute the filtered view in the transformation layer OR filter on EXISTING columns in the presentation layer (no new calculations)
**Need to join tables?** → Do the join in the transformation layer
**Need aggregations?** → Compute them in the transformation layer

### Presentation Layer: Display ONLY

The presentation layer may:

- ✅ Read pre-computed outputs (`SELECT * FROM precomputed_table`)
- ✅ Filter on EXISTING columns (`WHERE column = :user_selection`)
- ✅ Format numbers, dates for display
- ✅ Create interactive widgets that filter existing data
- ✅ Render charts from pre-computed metrics

The presentation layer must NEVER:

- ❌ Aggregate (`SUM(...) GROUP BY ...` = transformation)
- ❌ Join (`a.*, b.* FROM a JOIN b` = transformation)
- ❌ Apply business logic (`CASE WHEN ... END` = transformation)
- ❌ Calculate derived metrics inline
- ❌ Apply any formula that changes the meaning of data

### If You're Tempted to Transform in the Presentation Layer

**STOP.** Move the transformation into the transformation layer instead:

1. Add the transformation as a versioned model/script
2. Add tests proving it works
3. Build/run the transformation layer
4. THEN read the pre-computed output from the presentation layer

This takes more time. That's the point. Transformations deserve scrutiny.

## Documentation Index

### Instructions (_CHUNKS/)

- **Investigation**: [[instructions/data-investigation.md]], [[instructions/exploratory-analysis.md]]
- **Research docs**: [[instructions/research-documentation.md]] (REQUIRED), [[instructions/methodology-files.md]], [[instructions/methods-vs-methodology.md]], [[instructions/experiment-logging.md]]

### References

[[references/context-discovery.md]], [[references/quick-reference-commands.md]]

### Statistical Analysis (references/)

Start with [[references/statistical-analysis.md]] (complete guide). Also: [[references/test_selection_guide.md]], [[references/assumptions_and_diagnostics.md]], [[references/effect_sizes_and_power.md]], [[references/bayesian_statistics.md]], [[references/reporting_standards.md]].

### Technology-Specific Skills (aops-extras)

The concrete how-to for particular tools lives in the **aops-extras** package, so it can be swapped for official/community-consensus skills:

- **`dbt`** — transformation-layer implementation (models, tests, marts).
- **`streamlit`** — presentation-layer implementation (display-only dashboards).
- **`python-viz`** — Python plotting & statistical-modelling libraries (matplotlib, seaborn, statsmodels). Use the `python-dev` skill for code standards.

## When to Use This Skill

Invoke this skill when:

1. **Working in computational research projects** - An empirical data pipeline, analytical database, or transformation/presentation layer is present
2. **User requests data analysis** - "Analyze X", "Create a chart showing Y", "Explore the relationship between Z"
3. **Building or updating dashboards** - Presentation-layer visualization work (see the aops-extras `streamlit` skill for that engine)
4. **Creating or modifying transformations** - Transformation-layer pipeline work (see the aops-extras `dbt` skill for that engine)
5. **Validating data quality** - Adding tests, checking consistency

**Key indicators in project structure:**

- A version-controlled transformation layer (e.g. a `dbt/models/` directory — staging, intermediate, marts)
- A presentation layer (e.g. a `streamlit/` directory or dashboard `.py` files)
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
│  ├─ Existing transformation-layer models (list them)
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
│  ├─ Transformation model → Go to: Transformation Model Workflow
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
- **Existing transformation models** - What models already exist in the transformation layer?
- **Conventions** - Naming patterns, coding standards, project-specific rules
- **Testing strategy** - What tests exist? What quality expectations?
- **Tools and technologies** - Which transformation engine and presentation tool? (e.g. dbt + Streamlit — see the aops-extras skills.) DuckDB? PostgreSQL? Specific Python packages?

**Example context discovery:**

```bash
# List existing transformation-layer models (engine-specific; e.g. dbt)
ls -1 dbt/models/staging/*.sql dbt/models/marts/*.sql

# Check for presentation-layer apps (engine-specific; e.g. Streamlit)
ls -1 streamlit/*.py

# Understand project structure
cat README.md
cat data/README.md
```

> The example commands above assume a dbt + Streamlit stack. For the concrete
> per-engine discovery commands, see the aops-extras `dbt` and `streamlit` skills.

After context discovery, summarize findings to user:

`"I've reviewed the project context. This is a <research topic> project investigating <questions>. The transformation layer has <N> staging models and <M> mart models. I see existing work on <areas>. What would you like me to help with?"`

## Follow Data Access Workflow

**🚨 CRITICAL RULE: ALL data access MUST go through the modelled transformation layer. NEVER query raw upstream sources directly.**

**🚨 REMINDER: If you need to transform data, that transformation MUST live in the transformation layer with tests. See "Transformation Layer vs Presentation Layer" above.**

### Decision Tree

```
Need data for analysis?
│
├─ Does required data exist in the modelled (mart) layer?
│  ├─ YES → Read it (e.g. `SELECT * FROM mart_name`)
│  │         └─ Done! Use this data in analysis.
│  │
│  └─ NO → Does it exist in staging models?
│     ├─ YES → Should this become a new mart?
│     │  ├─ YES → Go to: Transformation Model Workflow (create mart)
│     │  └─ NO → Use staging model for exploratory work
│     │
│     └─ NO → Data doesn't exist in the transformation layer yet
│        └─ Ask user: "Should I create a model for [data source]?"
│           ├─ YES → Go to: Transformation Model Workflow (create staging model)
│           └─ NO → Stop. Cannot proceed without a modelled source.
```

### Prohibited Actions

❌ **NEVER** do this:

```python
# Direct BigQuery query against raw source - PROHIBITED
df = client.query("SELECT * FROM bigquery.raw.cases").to_dataframe()

# Direct database query against raw schema - PROHIBITED
df = pd.read_sql("SELECT * FROM raw_schema.table", engine)

# Direct API call for analysis data - PROHIBITED
response = requests.get("https://api.example.com/data")
```

✅ **ALWAYS** do this:

```python
# Query through the modelled layer - CORRECT
import duckdb

conn = duckdb.connect("data/warehouse.db")
df = conn.execute("SELECT * FROM fct_case_decisions").df()  # fct_* = a tested mart
```

### Why This Matters

- **Reproducibility**: Queries are version-controlled in the transformation layer
- **Data governance**: The modelled layer is the single source of truth
- **Quality**: Data passes through a validated, tested transformation pipeline
- **Consistency**: All analysts use the same transformations

**See:** the aops-extras `dbt` skill for the dbt implementation of this policy.

## Follow Transformation Model Workflow

Create or modify transformation-layer models following academicOps layered architecture. The layering below is engine-neutral; the aops-extras `dbt` skill gives the dbt-specific commands and file layout.

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

**See:** the aops-extras `dbt` skill for complete workflow details and comprehensive patterns.

## Follow Visualization Workflow

Create presentation-layer visualizations following the single-step collaborative pattern.

**🚨 REMINDER: The presentation layer is DISPLAY ONLY. No transformations. See "Transformation Layer vs Presentation Layer" above.**

**For the detailed engine-specific workflow (structure, single-step patterns, examples), see the aops-extras `streamlit` skill.**

### Quick Reference: Presentation Pattern

Load data → STOP → Create chart → STOP → Add interactivity → STOP. One change at a time. See the aops-extras `streamlit` skill for engine-specific tips (e.g. Streamlit hot-reload).

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

The examples below use dbt's `schema.yml` syntax to illustrate the _principle_ — column-level tests declared alongside the model. See the aops-extras `dbt` skill for the full engine-specific testing reference; any transformation engine should provide an equivalent declarative test layer.

```yaml
# dbt/schema.yml (dbt example)
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

**See:** the aops-extras `dbt` skill for complete engine-specific testing patterns.

## Follow Data Investigation Workflow

When investigating data quality issues (missing values, unexpected patterns, join coverage), create REUSABLE investigation scripts in `analyses/` directory. Never use throwaway one-liners for data investigation.

**For complete workflow, script templates, and when to create investigation scripts, see [[instructions/data-investigation.md]]**

## Exploratory Analysis

When exploring data patterns and relationships, follow collaborative discovery process. Take one analytical step at a time, yielding to user after each finding.

**For complete exploration workflow and anti-patterns, see [[instructions/exploratory-analysis.md]]**

**NOTE:** For data quality issues (missing values, unexpected nulls), use Data Investigation Workflow instead.

## Documentation Philosophy

**Self-documenting work**: Do NOT create separate analysis reports or random documentation files.

**🚨 CRITICAL: Research projects must follow STRICT documentation structure. See [[instructions/research-documentation.md]] for complete requirements.**

### Required Documentation Structure

Research projects MUST maintain:

- **README.md** - Project overview and quick start
- **METHODOLOGY.md** - Research design and approach (see [[instructions/methodology-files.md]])
- **methods/*.md** - Technical implementation details (see [[instructions/methods-vs-methodology.md]])
- **data/README.md** - Data sources and schema
- **Transformation-layer schema/docs** - Model and column documentation (e.g. `dbt/schema.yml`)
- **experiments/YYYYMMDD-description/** - Experimental work (see [[instructions/experiment-logging.md]])

### Where Analysis Documentation Lives

1. **Presentation-layer dashboards** - Interactive exploration and validation (e.g. Streamlit)
2. **Jupyter notebooks** - Detailed analysis with inline markdown (in experiments/ if exploratory)
3. **GitHub issues** - Track analysis tasks and decisions
4. **Code comments** - Explain analytical decisions in transformation-layer models
5. **Commit messages** - Document why changes were made
6. **Transformation-layer schema docs** - Document model purposes and column meanings (e.g. `dbt/schema.yml`)
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

See [[references/quick-reference-commands.md]] for common data-pipeline and DuckDB commands. For engine-specific commands, see the aops-extras `dbt` and `streamlit` skills.
