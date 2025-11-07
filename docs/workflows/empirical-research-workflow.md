# Personal Empirical Research Workflow

This document describes my cross-project preferences for computational research. Individual projects (dbr, tox, tja, mediamarkets) adapt these principles for their specific contexts.

## Foundational Methodology

I follow the **academicOps** approach documented in `bot/docs/methodologies/computational-research.md`. Core principles:

- dbt for data transformation and validation
- Streamlit for interactive dashboards
- Jupyter for detailed analysis
- Version control for everything

## Cross-Project Preferences

### Technology Stack

**Data pipeline:**

- **dbt-core** with DuckDB adapter
- DuckDB for local analytical database
- SQL for transformations (not Python in dbt)

**Analysis:**

- **Streamlit** for dashboards (preferred over Jupyter for exploration)
- **Jupyter** for final publication-quality analysis
- **Polars** over pandas where performance matters

**Visualization:**

- **Plotly** for interactive charts
- **Altair** for publication graphics

### Project Setup Pattern

When starting a new computational research project:

1. **Create project directory** in `projects/` with standard structure
2. **Initialize dbt** with DuckDB profile
3. **Set up data ingestion** scripts
4. **Create initial staging models** with tests
5. **Build Streamlit dashboard** early for exploration
6. **Document as I go** (not at the end)

### Data Organization

```
projects/myproject/
├── data/
│   ├── raw/              # Source data (not in git)
│   ├── downloads/        # Scripts to fetch raw data
│   └── warehouse.db      # DuckDB database (not in git)
├── dbt_project/
│   ├── models/
│   │   ├── staging/      # Clean and standardize
│   │   ├── intermediate/ # Metrics and aggregations
│   │   └── marts/        # Analysis-ready tables
│   ├── tests/            # Data quality tests
│   └── schema.yml        # Documentation and tests
├── streamlit/
│   └── app.py            # Main dashboard
├── notebooks/
│   └── analysis.ipynb    # Publication analysis
└── README.md             # Setup and overview
```

### Testing Philosophy

I prefer **many small tests** over few complex ones:

- Every `id` field gets `unique` and `not_null` tests
- Every foreign key gets `relationships` test
- Status fields get `accepted_values` tests
- Date logic gets singular tests for ordering/consistency
- Start with `warn` severity, escalate to `error` once stable

See `bot/docs/methodologies/dbt-practices.md` for technical details.

### Dashboard-First Development

I build Streamlit dashboards **early** in the project:

1. **Data explorer**: Quick view of raw and staging data
2. **Validation dashboard**: Visual tests of transformations
3. **Analysis dashboard**: Interactive exploration of patterns
4. **Publication dashboard**: Final artifacts for sharing

**Why:** Dashboards catch issues faster than tests alone. Human review complements automated validation.

### Documentation Standards

**In dbt schema.yml:**

- Every model has a description
- Every column has a description (especially computed ones)
- Tests are documented with why they matter

**In README:**

- How to set up the project from scratch
- Where data comes from and how to access it
- How to run the pipeline
- How to view dashboards/analysis

**In code comments:**

- Why not what (the code shows what)
- Decisions and tradeoffs
- Links to relevant documentation or issues

### Integration with Academic Writing

The empirical component supports academic articles:

**Methods section references:**

- "Data processed using dbt v1.7 (see supplementary materials)"
- "Validation dashboard at [URL] shows data quality checks"
- "Full transformation logic in models/marts/fct_*.sql"

**Supplementary materials include:**

- Complete dbt project code
- Streamlit dashboard code
- Jupyter notebook with analysis
- Data dictionary (from dbt docs)
- Instructions to reproduce

### Strategic Alignment

Computational research projects support **Academic Profile** goal:

- Establish leadership in computational legal studies
- Demonstrate AI/data methods expertise
- Build reusable infrastructure across projects

They typically have:

- **60% time allocation** (within Academic Writing workstream)
- **Publication target** (article or book chapter)
- **Reusable components** (methodologies, tools, agents)

## Project-Specific Adaptations

Individual projects adapt this workflow:

**DBR (Digital Services Regulation):**

- Focus: Regulatory compliance tracking
- Data: Transparency reports, DSA filings
- Special: Multi-jurisdiction comparisons

**Tox (Platform Toxicity):**

- Focus: Content moderation measurement
- Data: Platform API data, labeled datasets
- Special: NLP/ML model evaluation

**TJA (Transparency and Justice):**

- Focus: Decision quality analysis
- Data: Case decisions, metadata
- Special: Qualitative + quantitative mix

**MediaMarkets:**

- Focus: Content availability tracking
- Data: Streaming service catalogs
- Special: Longitudinal comparisons

Each has its own `README.md` in `projects/*/` with specific setup and context.

## Tools and Scripts

**Reusable across projects:**

- `bot/scripts/` - Task management, data ops
- `bot/docs/methodologies/` - Generic best practices
- MCP servers for data access (zotmcp, osbchatmcp)

**Project-specific:**

- Data fetching scripts in `projects/*/data/downloads/`
- Custom dbt macros in `projects/*/dbt_project/macros/`
- Project Streamlit apps in `projects/*/streamlit/`

## Evolution

This workflow evolves as I learn:

- New methodologies get added to `bot/docs/methodologies/`
- Patterns that work get codified
- Tools that don't work get removed

**Current experiments:**

- Evidence.dev for SQL-based BI
- Great Expectations for advanced validation
- Quarto for literate programming

## References

- `bot/docs/methodologies/computational-research.md` - Generic academicOps approach
- `bot/docs/methodologies/dbt-practices.md` - DBT technical details
- Individual project READMEs for specific implementations
