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

Fetch current dbt CLI documentation dynamically at point of use.
