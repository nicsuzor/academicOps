---
title: Experiment Logging Structure
type: note
category: instruction
permalink: analyst-chunk-experiment-logging
description: Organise, document, conclude, and retire exploratory experimental work in a research project.
---

# Experiment logging

Isolate exploratory work (testing approaches, validating measures, chasing anomalies) under `experiments/` so future readers understand what was attempted, what was found, and the final outcome.

## Directory structure

Name each directory `experiments/YYYYMMDD-short-description/`:

```
experiments/YYYYMMDD-short-description/
├── README.md        # purpose, findings, outcome (required)
├── notebook.ipynb   # exploratory analysis
├── scripts/         # prototype scripts
├── data/            # isolated test inputs
└── outputs/         # intermediate charts and tables
```

## Experiment README template

Create at the start of each experiment and keep current:

```markdown
# Experiment: [short description]

**Date**: YYYY-MM-DD | **Status**: In progress | Completed | Abandoned | **Related issue**: [#]

## Purpose & Approach

[Question tested, hypotheses, and analytical techniques.]

## Key Findings & Outcome

[Discoveries. Mark as integrated into <production path>, abandoned (<reason>), or deferred.]
```

## Lifecycle and promotion

Conclude experiments by recording final status and findings:

- **Succeeded**: Promote durable code to production homes (`methods/`, dbt models, dashboard layer). Record destination in the README, commit as historical record, and link from production docs.
- **Failed**: Document reasons for failure to prevent repeated attempts; commit findings as a negative result.
- **Stale**: Move unmaintained exploratory work to `experiments/_archive/`.

Keep production code tested and documented per `instructions/research-documentation.md`; retain only genuine prototypes and negative results in `experiments/`.
