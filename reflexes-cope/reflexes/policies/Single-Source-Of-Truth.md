# Criteria

## Overview

This policy prevents the creation or tolerance of parallel copies of facts, rules, schemas, or documentation that can drift over time. For every system definition, there must be exactly one authoritative copy (SSoT). When duplicate copies are identified, they must be consolidated or replaced with explicit references to the canonical location.

## Definition of Terms

- **Tool call**: A pending file write or edit that introduces duplicated text or parallel schemas.
- **Agent response**: Proposed documentation or code modifications creating duplicate definitions.
- **Parallel Copy / Duplication Liability**: Creating or maintaining a second copy of a rule, axiom, schema, or configuration in a separate file rather than linking to the authoritative canonical source.
- **Single Source of Truth (SSoT)**: The single canonical file designated to own a specific fact, rule, or definition.

## Interpretation of Language

- Inspect proposed file creations, documentation edits, and code changes for duplicated rules or schemas.
- Check whether new text restates facts owned by existing canonical specs instead of linking to them.
- Creating single canonical sources and linking to them across other documents is compliant.

## Definition of Labels

### (ST): Parallel Copy or Duplication Liability

#### Includes

- **Duplicated Rule or Axiom Text Class**: A **Tool call** or **Agent response** pasting full axiom definitions or rule prose into multiple skill files instead of referencing the canonical `.agents/rules/` file.
- **Parallel Backward-Compatibility Schema Class**: A **Tool call** maintaining duplicate schema variants or competing configuration paths that can drift out of sync.
- **Redundant Documentation Fact Class**: An **Agent response** authoring a second copy of an enforcement table or system state doc instead of updating the single SSoT file.

#### Excludes

- **Canonical SSoT Consolidation Class**: A **Tool call** consolidating scattered duplicate definitions into a single authoritative spec file.
- **Explicit Cross-Reference Link Class**: An **Agent response** referencing a canonical SSoT doc by path or slug without duplicating its contents.
- **Deletion of Non-Authoritative Copy Class**: A **Tool call** removing stale or parallel duplicate files to restore single-source-of-truth integrity.
