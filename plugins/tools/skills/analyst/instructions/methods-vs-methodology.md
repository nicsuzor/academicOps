---
title: Methods vs Methodology
type: note
category: instruction
permalink: analyst-chunk-methods-vs-methodology
description: Route research content between METHODOLOGY.md and methods/ files, and construct technique specifications.
---

# Methods vs Methodology

Separate conceptual research design from technical implementation. `METHODOLOGY.md` at project root explains the scholarly design to peer reviewers. Files in `methods/` provide reproducible implementation instructions for researchers and coders.

## Routing guide

| Content                                                                | Target document           | Example                                                                                        |
| ---------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------- |
| **Why**: Question, design, validity, assumptions, conceptual variables | `METHODOLOGY.md`          | Difference-in-differences design to measure policy impact, assuming parallel trends.           |
| **How**: Algorithms, parameters, estimators, step-by-step procedures   | `methods/<name>.md`       | `PanelOLS` via `linearmodels`, entity/time effects, clustered SEs, parallel trend plot script. |
| **Data provenance & schema**: Sources, access, storage format          | `data/README.md`          | Ingestion cadence, table definitions, raw storage partitions.                                  |
| **Column-level computations**: Specific formula, null handling         | Schema doc (`schema.yml`) | SQL logic or definition for an individual mart column.                                         |

## Methods file template (`methods/<method_name>.md`)

Name files using lowercase and underscores (e.g., `methods/diff_in_diff.md`):

```markdown
# Method: [Name]

## Purpose

[Operational task this technique performs.]

## Implementation & Parameters

[Algorithms, execution scripts, parameters, admissible ranges, and default values.]

## Validation & Edge Cases

[Verification tests, assumption checks, and boundary behaviors.]

## References & Related Files

[Academic citations, documentation links, transformation models, and scripts.]
```

## Synchronization rule

Update `METHODOLOGY.md` when conceptual constructs or designs evolve. Update `methods/<name>.md` when implementation algorithms, code paths, or parameters change. When changing measured metrics, update both: the construct in methodology and the implementation in methods.
