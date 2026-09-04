---
title: Experiment Logging Structure
type: note
category: instruction
permalink: analyst-chunk-experiment-logging
description: How to organise, document, conclude, and retire exploratory experimental work in a research project
---

# Experiment logging

Experiments are exploratory work — testing an analytical approach, validating a
measurement strategy, comparing methods, chasing an unexpected finding — that
may never reach the final analysis. They live under `experiments/`, the code in
them may be messy and incomplete, and they are held to one standard: a later
reader can tell what was tried, what was found, and what happened next.

## Directory layout

One directory per experiment, named `YYYYMMDD-short-description`. Date first so
the directory listing sorts chronologically and each experiment can be matched
to the state of the code and data at that time; lowercase and hyphenated;
specific enough to identify from the name alone — `20241105-test-diff-in-diff`,
not `experiment1`.

```
experiments/
└── YYYYMMDD-short-description/
    ├── README.md        # purpose, findings, outcome — required
    ├── notebook.ipynb   # exploratory analysis
    ├── scripts/         # prototype code
    ├── data/            # experiment-specific inputs, if any
    └── outputs/         # charts, tables, intermediate results
```

## The experiment README

Write it when you start, with the purpose already filled in, and update it as
you learn. Without it the experiment costs its own re-running, because nobody —
including you — can later tell whether the approach was a dead end.

```markdown
# Experiment: [short description]

**Date**: YYYY-MM-DD
**Status**: In progress | Completed | Abandoned
**Related issue**: [link, if any]

## Purpose

[What is being tested, and what question it answers.]

## Approach

[Methods and techniques used.]

## Key findings

[What was discovered. Fill in as you go.]

## Outcome

[One of: integrated into production analysis at <location>; abandoned for
<reason>; needs further work; results recorded in issue #<n>.]

## Files

[Each file and what it holds.]
```

## Concluding an experiment

Set the status, record the findings, and record the outcome — a failed
experiment included, because the documented failure is what stops the approach
being tried again. Then:

- **Succeeded** — move the durable part to its production home: a technique to
  `methods/`, a transformation to the transformation layer, a visualisation to
  the presentation layer. Note that location in the experiment README, commit
  the experiment as the historical record, and cite it from the production
  documentation.
- **Failed** — record why, and commit. A negative result is a result.
- **Stale**, unfinished and months old — decide explicitly between reviving,
  finishing, and archiving under `experiments/_archive/`, and record the
  decision in the README.

Commit an experiment when it reaches a documented milestone, when its results
are integrated, and when it is abandoned — not on every exploratory step, and
not before the README says what it is for.

## Experiments versus production

Anything that works and will be used again leaves `experiments/`. Transformation
models, dashboards, documented methods, and reusable analysis scripts have
production homes and production standards: tested, reviewed, reproducible, and
documented per `instructions/research-documentation.md`. What stays behind is
genuinely exploratory — prototypes, throwaway charts, quick quality checks, and
the record of approaches that did not work.
