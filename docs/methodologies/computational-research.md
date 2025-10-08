# Computational Research Methodology (academicOps)

## Overview

The **academicOps** approach applies DevOps practices to computational research projects in the social sciences and humanities. The core principle: treat empirical research infrastructure with the same rigor as software engineering.

### What This Means

Traditional empirical research often involves:
- Ad-hoc data transformations in spreadsheets
- Undocumented analysis scripts
- Manual validation steps
- Irreproducible workflows

**academicOps instead applies:**
- Version-controlled data pipelines
- Documented transformations
- Automated testing and validation
- Reproducible, auditable workflows

## Core Components

### 1. Data Pipeline (dbt)

Use **dbt (data build tool)** to define data transformations as code:
- SQL models define how raw data becomes analysis-ready
- Tests validate data quality at every step
- Documentation lives alongside the code
- Lineage tracking shows data dependencies

See [dbt-practices.md](./dbt-practices.md) for detailed best practices.

### 2. Analysis Artifacts (Streamlit/Jupyter)

Create interactive analysis tools:
- **Streamlit**: Dashboards for exploration and validation
- **Jupyter**: Detailed analysis notebooks for publication

**Key principle:** These consume dbt-validated data, they don't transform it. Data transformations happen in dbt where they're tested and documented.

### 3. Version Control (Git)

Everything is version controlled:
- Data transformation code (dbt models)
- Analysis scripts (Streamlit, Jupyter)
- Documentation
- Configuration

**Exception:** Raw source data and large databases are excluded (use `.gitignore`). Instead, document data sources and provide scripts to fetch/load them.

## Workflow Pattern

A typical academicOps project follows this pattern:

```
1. Raw Data → 2. dbt Pipeline → 3. Validated Data → 4. Analysis/Artifacts → 5. Publication
```

### Phase 1: Raw Data Ingestion

- Load data from sources (APIs, exports, scraping)
- Store in standardized location (`data/raw/`)
- Document provenance and access instructions

### Phase 2: dbt Pipeline

- **Staging models** (`stg_*`): Clean and standardize
- **Intermediate models** (`int_*`): Business logic and transformations
- **Mart models** (`fct_*`, `dim_*`): Analysis-ready datasets
- **Tests**: Validate at each layer

### Phase 3: Validated Data

- dbt materializes validated models
- Tests provide confidence in data quality
- Documentation describes what each field means

### Phase 4: Analysis & Artifacts

- **Exploratory analysis**: Jupyter notebooks to understand patterns
- **Validation dashboards**: Streamlit apps for human review
- **Publication artifacts**: Final visualizations, tables, statistics

### Phase 5: Publication

- Academic paper references specific dbt models and analysis scripts
- Reviewers can reproduce results by running the pipeline
- Code and (where possible) data are published alongside the paper

## Project Structure

Standard academicOps project layout:

```
project/
├── data/
│   ├── raw/              # Raw source data (gitignored)
│   └── warehouse.db      # dbt output (gitignored)
├── dbt/
│   ├── models/
│   │   ├── staging/      # stg_* models
│   │   ├── intermediate/ # int_* models
│   │   └── marts/        # fct_*, dim_* models
│   ├── tests/            # Singular tests
│   ├── schema.yml        # Documentation and schema tests
│   └── dbt_project.yml   # Configuration
├── streamlit/
│   └── dashboard.py      # Interactive dashboards
├── notebooks/
│   └── analysis.ipynb    # Detailed analysis
├── README.md             # Project overview and setup
└── requirements.txt      # Python dependencies
```

## Why This Approach?

### Reproducibility

Every transformation is code. Anyone can run the pipeline and get the same results.

### Auditability

Version control shows when changes were made and why. Tests document expectations.

### Collaboration

Clear structure and documentation let collaborators understand and extend the work.

### Quality

Automated tests catch data quality issues early. Human review happens via dashboards.

### Academic Rigor

Computational methods deserve the same rigor as statistical methods. This approach makes the empirical process transparent and verifiable.

## Integration with Academic Writing

academicOps projects generate empirical components of academic articles:

**In the paper:**
- "Data was processed using dbt pipeline version X.Y"
- "See models/marts/fct_case_decisions.sql for decision outcome logic"
- "Interactive validation dashboard available at [URL]"

**In supplementary materials:**
- Full dbt project (all models and tests)
- Streamlit dashboard code
- Jupyter notebooks with detailed analysis
- Instructions to reproduce

**Benefits:**
- Reviewers can verify empirical claims
- Other researchers can extend the work
- Methods are fully transparent

## Starting a New Project

1. **Choose your data sources**
2. **Set up project structure** (use template if available)
3. **Create dbt staging models** from raw data
4. **Add tests** to validate data quality
5. **Build intermediate and mart models** with business logic
6. **Create Streamlit dashboard** for exploration
7. **Develop Jupyter analysis** for publication
8. **Document everything** as you go

See your personal `docs/workflows/empirical-research-workflow.md` for project-specific preferences.

## Tools & Technologies

**Core:**
- **dbt** (data transformation and testing)
- **DuckDB** (analytical database, lightweight)
- **Git** (version control)

**Analysis:**
- **Streamlit** (interactive dashboards)
- **Jupyter** (detailed notebooks)
- **pandas/polars** (data manipulation)
- **plotly/altair** (visualization)

**Optional:**
- **Great Expectations** (advanced data validation)
- **Evidence** (BI dashboards from SQL)
- **Quarto** (reproducible documents)

## Example Projects

Projects using this approach (de-identified examples):

- **DBR**: Digital services regulation analysis
- **Tox**: Platform toxicity measurement
- **TJA**: Transparency and justice analysis
- **MediaMarkets**: Content availability tracking

Each follows the same core pattern but adapts for specific data sources and research questions.

## Further Reading

- [dbt-practices.md](./dbt-practices.md) - Detailed dbt guidance
- [Modern Data Stack](https://www.getdbt.com/blog/future-of-the-modern-data-stack/) - Industry context
- [The Turing Way](https://the-turing-way.netlify.app/) - Reproducible research handbook
