---
name: dbt
description: dbt (data build tool) implementation of the analyst transformation layer.
  Use when a project has a dbt/ directory or you need to build, test, or document
  SQL transformations as version-controlled, reproducible dbt models. This is the
  dbt-specific HOW for the tech-agnostic principles in the aops-tools analyst skill.
---

# dbt — Transformation Layer (academicOps)

dbt is one **swappable** implementation of the transformation layer. The `analyst`
skill owns the principles, which hold whichever engine you use.

## When to use

- The project contains a `dbt/` directory (`dbt/models/`, `dbt_project.yml`).
- You need to add a metric, join, aggregation, or any business logic — it belongs in a
  dbt model with tests, never in the presentation layer.
- You need to test or document a transformation so reviewers can re-run and audit it.

## The boundary that matters

Every metric, join, aggregation, and `CASE` business rule lives in a tested dbt model
in the staging / intermediate / mart layering — never inline in the presentation
layer. A transformation without a test is not one anyone can audit.

Fetch current dbt documentation at the point of use.
