---
title: Methods vs Methodology
type: note
category: instruction
permalink: analyst-chunk-methods-vs-methodology
description: Which research artifact a given statement belongs in, and how to write a methods/ file
---

# Methods vs methodology

Methodology is the research design: one `METHODOLOGY.md` at the project root,
written for a peer reviewer. Methods are the implementation: one file per
technique in `methods/`, written for someone reproducing the analysis. Keeping
them apart is what lets a reviewer evaluate the design without reading code and
an implementer find the procedure without reading justification.

Structure and maintenance of `METHODOLOGY.md`: read
`instructions/methodology-files.md`.

## Where a statement belongs

Route on who the sentence serves.

| The sentence                                                                             | Belongs in                                                             |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| justifies why — question, framework, design, conceptual variables, validity, limitations | `METHODOLOGY.md`                                                       |
| explains how — algorithm, parameters, code, tools, step-by-step procedure                | a file in `methods/`                                                   |
| describes the data itself — provenance, schema, access, refresh, known issues            | `data/README.md`                                                       |
| defines how a column is computed                                                         | transformation-layer schema documentation (`dbt/schema.yml` under dbt) |

The hard cases are concepts that appear on both sides at different altitudes.
An assumption is methodology; the test of that assumption is a method. A
variable's conceptual definition ("processing time is days from submission to
final decision") is methodology; its computation, null handling, and outlier
rule are a schema doc or a method.

| `METHODOLOGY.md`                                                                                                                                                                                                                                                                                         | `methods/diff_in_diff.md`                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "We use a difference-in-differences design to estimate the effect of policy change X on outcome Y. Treatment is cases filed after the change (n=1,247); control is cases filed in the same months a year earlier (n=1,189). We assume parallel trends and control for case type and seasonal variation." | "Estimated with `PanelOLS` from `linearmodels` with entity and time effects; standard errors clustered at case level. Pre-treatment parallel trends validated by `plot_parallel_trends()`. Run by `analyses/did_estimation.py`." |

## Writing a methods/ file

One method per file, named for the method in lowercase with underscores
(`scoring_algorithm.md`, `qualitative_coding.md`), so a reader finds a technique
by name instead of opening every file.

```markdown
# Method: [name]

## Purpose

[What this method produces and what it is for.]

## Implementation

[Algorithm, steps, and the code that runs it or a pointer to it.]

## Parameters

[Each input, its meaning, units, and admissible range.]

## Validation

[How to confirm the method works: the tests, and the edge cases they cover.]

## References

[Papers, library documentation, related methods.]

## Related files

[Code, tests, data, and transformation models this method touches.]
```

Argument for choosing the technique goes in `METHODOLOGY.md`, where a reviewer
looks for it; a methods file that argues its own case has buried the reviewer's
paragraph in an implementation note.

## Keeping both current

Update `METHODOLOGY.md` when the research question, design, conceptual
definitions, or theoretical framework change. Update the methods file when the
algorithm, parameters, implementation, or validation change. Changing what you
measure changes both: the construct in `METHODOLOGY.md`, the calculation in
`methods/`. Write each fact into exactly one of them, and cross-reference from
the other.
