---
name: python-viz
description: Python plotting and statistical-modelling libraries (matplotlib, seaborn,
  statsmodels) for the analyst presentation and statistical-methodology layers. Use
  when producing publication-quality figures or fitting statistical models in Python.
  Library-specific HOW for the tech-agnostic principles in the aops-tools analyst
  skill.
---

# Python Visualisation & Statistical Modelling (academicOps)

These libraries are one **swappable** implementation. The `analyst` skill owns the
statistical-methodology and presentation principles, which are library-neutral.

## When to use

- You need to render a figure from PRE-COMPUTED data (presentation layer).
- You need to fit or diagnose a statistical model in Python (statistical-methodology
  layer) — pair this with the analyst skill's `statistical-analysis` reference for the
  methodology that drives the choice of test/model.

## Where the API detail comes from

Fetch current library documentation at the point of use. matplotlib, seaborn, and
statsmodels all move, and a copy pinned in this repo would be one more thing to keep
true. Which test, which model, and how to report it is the analyst skill's question,
not a library one.
