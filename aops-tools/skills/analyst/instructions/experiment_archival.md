---
title: Experiment Archival
type: reference
category: instruction
permalink: skills-analyst-experiment-archival
description: Patterns for archiving intermediate analyses and experiments when data pipelines change
tags: [experiments, archival, jupyter, research-methods, reference]
---

# Experiment Archival and Research Journaling

Distinguish two kinds of analysis output:

- **Reproducible research** — final analysis and dbt models that go in the paper; must re-run cleanly against current data.
- **Process documentation** — intermediate experiments, diagnoses, and decisions that record the journey to a conclusion, not the conclusion itself. These stop being reproducible once the underlying data changes (e.g. old data is removed after a pipeline migration) but still need to be viewable and citable indefinitely.

When a data pipeline change is about to make prior analysis non-reproducible (e.g. removing superseded data from staging tables after validating a new format), archive the process documentation before the change:

1. Archive all related analysis before the change lands.
2. Build a single comprehensive Jupyter notebook with every chart and table output saved inline.
3. Export the notebook to static HTML for long-term viewing without re-running code.
4. Timestamp the archive and link it to the change that made it necessary.
5. File it under `experiments/YYYYMMDD-archive-description/`.
6. Clean up working files once the archive is committed.
