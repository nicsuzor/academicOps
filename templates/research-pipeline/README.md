# Research Pipeline Mould Template

A Copier template providing a reproducible transformation and integrity mould for quantitative empirical research projects. Supports DuckDB (local-first) and BigQuery (warehouse) SQL engines.

## Admission Rule and Provenance

Per the project admission rule, every piece of this mould directly adopts an established external standard:

| Template piece | Adopted external standard | Purpose & Defect caught |
| - | - | - |
| **Directory layout & dbt models** (`dbt/models/{staging,intermediate,marts}`) | dbt Labs Best Practices | Isolates transformations from presentation; prevents business logic leaks into notebooks/dashboards. |
| **Portable committed profiles** (`dbt/profiles.yml`) | dbt Profiles standard | Enables clean-clone rebuild without uncommitted `~/.dbt/profiles.yml` dependencies or host paths. |
| **Dependency pinning & environment** (`pyproject.toml`, `.env.example`) | PEP 518/621, Astral `uv` | Locks exact adapter versions; prevents breakages from unpinned moving branches. |
| **Continuous integration gate** (`.github/workflows/ci.yml`) | GitHub Actions standard | Runs `dbt parse` and `dbt test` on every PR; catches silently dropped tests and stale refs. |
| **Quarto computational manuscript** (`manuscript/_quarto.yml`, `manuscript/index.qmd`) | Quarto standard | Reconstructs figures and tables directly from marts or Parquet files without manual copying. |
| **Parquet result export** (`scripts/export_parquet.py`) | Apache Parquet standard | Exports analytical marts to versioned columnar Parquet files for long-term durable developer proof. |
| **Model registry seed** (`dbt/seeds/safety_model_registry.csv`) | dbt Seeds standard | Eliminates hardcoded model lists and `CASE` statements across downstream transformations. |
| **Dual SQL engine support** (`duckdb` and `bigquery`) | dbt Adapters standard | Provides appropriate engine choice per project while enforcing identical integrity gates. |

## Usage

Render a new research project using Copier:

```bash
# Render with interactive prompts
uvx copier copy /path/to/templates/research-pipeline my-project

# Render with specific engine (DuckDB)
uvx copier copy --data sql_engine=duckdb /path/to/templates/research-pipeline my-project

# Render with BigQuery
uvx copier copy --data sql_engine=bigquery --data bigquery_project=my-project --data bigquery_dataset=analytics /path/to/templates/research-pipeline my-project
```
