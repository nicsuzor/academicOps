---
name: dbt
description: dbt (data build tool) implementation of the analyst transformation layer.
  Use when a project has a dbt/ directory or you need to build, test, or document
  SQL transformations as version-controlled, reproducible dbt models. This is the
  dbt-specific HOW for the tech-agnostic principles in the aops-tools analyst skill.
---

# dbt — Transformation Layer (academicOps)

dbt is one **swappable** implementation of the transformation layer. The `analyst`
skill owns the principles, which hold whichever engine you use; this skill owns the
dbt how-to — the commands and file layout below.

## Contents

- [[dbt-workflow]] — single-step collaborative workflow for creating and modifying
  dbt models in the staging / intermediate / mart layered architecture.
- [[dbt-patterns]] — comprehensive reference: data-access policy, model organisation,
  testing strategies (schema / singular / package tests), documentation, incremental
  models, and performance.

## When to use

- The project contains a `dbt/` directory (`dbt/models/`, `dbt_project.yml`).
- You need to add a metric, join, aggregation, or any business logic — it belongs in a
  dbt model with tests, never in the presentation layer.
- You need to test or document a transformation so reviewers can re-run and audit it.
