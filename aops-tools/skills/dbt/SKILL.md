---
name: dbt
type: skill
description: dbt (data build tool) implementation of the analyst transformation layer. Use when a project has a dbt/ directory or you need to build, test, or document SQL transformations as version-controlled, reproducible dbt models. This is the dbt-specific HOW for the tech-agnostic principles in the aops-tools analyst skill.
category: instruction
triggers:
  - "dbt"
  - "dbt model"
  - "dbt project"
  - "staging model"
  - "dbt mart"
modifies_files: true
needs_task: false
mode: execution
domain:
  - academic
  - development
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Skill
version: 0.1.0
permalink: skills-aops-extras-dbt
---

# dbt — Transformation Layer (academicOps)

This skill is the **dbt-specific implementation** of the transformation layer described
in the tech-agnostic `analyst` skill (aops-tools). The analyst skill owns the
_principles_ (all transformation in a versioned/tested/reproducible layer; presentation
displays pre-computed data only); this skill owns the _dbt how-to_.

dbt is one **swappable** choice of transformation layer. The analyst principles hold
regardless of which engine you use; only the commands and file layout below are
dbt-specific.

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
