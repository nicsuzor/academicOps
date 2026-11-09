---
title: Research pipeline mould
status: ready
---

# Research pipeline mould

A standardized, reproducible pipeline mould for quantitative empirical research projects that provides version-controlled SQL transformations, automated continuous integration, reproducible profiles, Quarto computational manuscripts, durable Parquet result exports, and an agent-executable integrity testing standard.

## User stories

### US-1 Engine-tailored project scaffolding

As a quantitative researcher, I want to instantiate a research pipeline scaffolded for either DuckDB or BigQuery from a single template, so that I have a working repository with committed profiles, pinned dependencies, dbt project layout, Quarto manuscript, and result export machinery.

- **AC-1.1** Given a template render request specifying the DuckDB engine, when the template renders, then the generated repository contains a DuckDB-configured dbt project, a portable DuckDB profile, a Quarto manuscript scaffold, and a Parquet export script.
- **AC-1.2** Given a template render request specifying the BigQuery engine, when the template renders, then the generated repository contains a BigQuery-configured dbt project, an environment-driven BigQuery profile, a Quarto manuscript scaffold, and a Parquet export script.
- **AC-1.3** Given a rendered repository for either engine, when dependency installation is executed from a clean clone, then all required tools and dbt adapters install with zero uncommitted environment configuration.

### US-2 Continuous integration verification

As a researcher or code auditor, I want every rendered research project to include automated continuous integration workflows, so that invalid models, stale references, and broken transformations are caught immediately on push or pull request.

- **AC-2.1** Given any rendered research project, when continuous integration runs, then it parses all dbt models, seeds, and tests via `dbt parse` and halts loudly on syntax or configuration errors.
- **AC-2.2** Given a rendered DuckDB research project, when continuous integration runs, then it seeds test data, compiles models, and executes `dbt test`, failing if any schema, parity, or domain test fails.

### US-3 Output integrity and deterministic testing

As an analyst or autonomous agent building transformations, I want unambiguous integrity standards that specify which properties must be tested for each kind of output and require all assertions to be deterministic code, so that empirical findings are defensible and reproducible.

- **AC-3.1** Given any staging transformation, the pipeline tests primary key uniqueness, non-nullability, and exact key parity against raw source records.
- **AC-3.2** Given any model or prompt registry, the pipeline tests identifier uniqueness, metadata completeness, and parity between registry count and distinct model count in downstream marts.
- **AC-3.3** Given any classification, inference, or scoring output, the pipeline tests input provenance linking each prediction to a valid source record identifier, score domain bounds, and evaluation-set parameter integrity.
- **AC-3.4** Given any final analytical mart, the pipeline tests non-empty result sets, category coverage completeness, and equality against canonical source aggregates.
- **AC-3.5** Given any presentation output in the Quarto manuscript, all figures and tables read pre-computed marts or Parquet exports without inline transformation logic.
- **AC-3.6** Given any integrity test across all output categories, the test executes as deterministic code in SQL or Python with no fuzzy matching or heuristic proxies.

### US-4 Durable result preservation

As a researcher concluding an analysis cycle, I want analytical results exported into columnar Parquet files within a versioned archive, so that durable evidence of findings remains inspectable without active database warehouse connections.

- **AC-4.1** Given built mart models, when the export command is executed, then every mart table is exported into a columnar Parquet file in the designated archive directory.
- **AC-4.2** Given exported Parquet files, when queried directly, then row counts and schemas match the source mart tables exactly.

## Design

### Project layout and lifecycle

The mould organizes research repositories into distinct operational layers:

```
project-root/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated dbt parse and test validation
├── data/
│   ├── raw/                     # Immutable raw source data
│   └── export/                  # Exported Parquet analytical marts
├── dbt/
│   ├── dbt_project.yml          # Core transformation configuration
│   ├── profiles.yml             # Engine connection profile
│   ├── models/
│   │   ├── staging/             # Source cleaning and type casting (stg_*)
│   │   ├── intermediate/        # Entity joins and scoring logic (int_*)
│   │   └── marts/               # Final presentation and analysis marts (fct_*, dim_*)
│   ├── seeds/                   # Versioned registries and reference tables
│   └── tests/                   # Singular deterministic domain tests
├── manuscript/
│   ├── _quarto.yml              # Quarto manuscript configuration
│   └── index.qmd                # Computational manuscript consuming marts
├── scripts/
│   └── export_parquet.py        # Deterministic mart-to-Parquet export script
├── pyproject.toml               # Python dependencies and tool definitions
├── .env.example                 # Documented environment variable definitions
└── README.md                    # Project documentation and quickstart instructions
```

### Engine specialization

Each repository selects exactly one SQL engine at instantiation:

1. **DuckDB**: Intended for local-first, in-process execution. The database file resides at a project-relative canonical path (`data/local_cache.duckdb`). Continuous integration runs full compile, seed, run, and test steps locally without remote credentials.
2. **BigQuery**: Intended for high-scale enterprise or shared warehouse execution. Connection configuration reads Google Cloud project and dataset identifiers from environment variables, authenticating via standard Google Cloud application default credentials. Continuous integration verifies project structure, schema configurations, and SQL syntax via `dbt parse`.

### Clean-clone portability

A clean clone of any project generated from the mould builds using only version-controlled files and environment variables. The `profiles.yml` file is committed directly to the repository root or `dbt/` directory, resolving connection details from standardized environment variables (`DBT_PROFILES_DIR`, `BIGQUERY_PROJECT`, `BIGQUERY_DATASET`) or project-relative file paths.

### Integrity layer specification

The integrity layer governs every transformation and analytical output produced within the pipeline:

| Output category | Required properties to test | Verification mechanism |
| - | - | - |
| **Raw staging (`stg_*`)** | Uniqueness of primary keys, absence of nulls in required fields, zero dropped keys relative to raw inputs. | dbt schema tests (`unique`, `not_null`), parity queries. |
| **Registries (`seeds/*`)** | Unique identifier per item, valid metadata fields, exact count parity against mart aggregations. | dbt seed schema tests, singular comparison tests. |
| **Classification & scoring (`int_*`, `fct_*`)** | Complete input provenance (`record_id` foreign key), valid score ranges (e.g. `[0.0, 1.0]`), evaluation subset parameter adherence. | Foreign key relationship tests, accepted value / range tests. |
| **Analytical marts (`fct_*`, `dim_*`)** | Non-empty outputs, category partition completeness, dimensional integrity. | dbt schema tests, custom singular SQL assertions. |
| **Manuscript presentation** | Rendering from pre-computed marts only, zero inline business transformations or joins. | Quarto render check, code inspection. |

Every test is implemented in deterministic code (SQL assertions or Python tests) executed during CI.

### Parquet export contract

Durable evidence of research outputs is preserved through automated Parquet export. The export script connects to the active SQL engine, reads each mart table in `models/marts`, and serializes the exact result set to `data/export/<mart_name>.parquet`.

## Open questions

None. All architectural decisions confirmed in project foundations.
