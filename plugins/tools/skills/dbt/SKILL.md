---
name: dbt
description: dbt transformation layer for version-controlled, tested SQL models in staging, intermediate, and mart layers. Use when projects contain a dbt/ directory or require auditable metric and schema transformations.
---

# dbt -- Transformation Layer

dbt provides the version-controlled transformation layer for the `analyst` skill. Presentation tools must never implement business logic.

## Usage Boundaries

- **Location**: Use when the repository contains a `dbt/` project directory (`models/`, `dbt_project.yml`).
- **Logic isolation**: Place all joins, metrics, aggregations, and `CASE` statements in tested dbt models (staging, intermediate, mart). Never embed transformation logic in dashboards or presentation scripts.
- **Canonical source parity**: When models derive from authoritative records (YAML, benchmark configs), author tests asserting exact parity against source records.
- **Canonical database paths**: Address local database files (e.g. DuckDB) via project-root absolute paths, avoiding cwd-relative drift.

## Research Pipeline Integrity Layer

Every quantitative research pipeline built on dbt must implement deterministic integrity testing across each output category. Tests must run before and during CI on every change.

### Output Categories and Required Property Tests

| Output category | Properties requiring tests | Testing mechanism | CI execution |
| - | - | - | - |
| **Raw staging (`stg_*`)** | Primary key uniqueness, mandatory field non-nullability, source record count and key parity (zero dropped inputs). | dbt schema tests (`unique`, `not_null`), custom parity queries against raw sources. | `.github/workflows/ci.yml` via `dbt test` |
| **Registries (`seeds/*`)** | Unique model/prompt identifier, non-null metadata, accepted categorical types, exact count parity against downstream marts (distinct registered entities == distinct mart entities). | dbt seed schema tests, singular cross-join parity tests. | `.github/workflows/ci.yml` via `dbt test` |
| **Classification & scoring (`int_*`, `fct_*`)** | Complete input provenance (`record_id` foreign key to source traces, zero orphan predictions), mathematical score domain bounds (e.g. `score >= 0.0 and score <= 1.0`), valid classification categories, evaluation subset parameter fidelity. | `relationships` tests, range boundary tests, `accepted_values` tests. | `.github/workflows/ci.yml` via `dbt test` |
| **Analytical marts (`fct_*`, `dim_*`)** | Non-empty result sets, dimensional/composite key uniqueness, category partition completeness (no missing slices), aggregate sum parity against unaggregated intermediate records. | dbt schema tests, singular reconciliation tests. | `.github/workflows/ci.yml` via `dbt test` |
| **Presentation & exports (`data/export/*.parquet`, `manuscript/`)** | Logic isolation (reading exclusively from pre-computed marts with zero inline business logic or joins), Parquet export row count and schema parity. | Deterministic Python export script, Quarto compilation check. | `.github/workflows/ci.yml` via `uv run python scripts/export_parquet.py` |

### Deterministic Code Requirement

In accordance with framework axioms:

- Every check named in the integrity layer must execute as **deterministic code** (SQL constraints, singular SQL assertion queries returning 0 rows on pass, or deterministic Python assertions).
- **No heuristic or legacy NLP**: Never use regex heuristics, keyword substring matching, or fuzzy string matching to evaluate data validity.
- **No delegated qualitative judgment**: Never use language model API calls or LLM-as-a-judge scripts to evaluate outputs. Where human gold standard evaluations are needed, they must be authored by researchers in advance and checked via deterministic equality assertions.

Fetch current dbt CLI documentation dynamically at point of use.
