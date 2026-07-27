---
name: python-viz
description: Python plotting and statistical-modelling libraries (matplotlib, seaborn,
  statsmodels) for the analyst presentation and statistical-methodology layers. Use
  when producing publication-quality figures or fitting statistical models in Python.
  Library-specific HOW for the tech-agnostic principles in the aops-tools analyst
  skill.
---

# Python Visualisation & Statistical Modelling (academicOps)

This skill collects the **Python library-specific** references that support the
tech-agnostic `analyst` skill (aops-tools). The analyst skill owns the _statistical
methodology and presentation principles_; this skill owns the _library how-to_ for
producing figures and fitting models in Python.

These libraries are **swappable** — the analyst statistical-methodology guidance (test
selection, assumptions, effect sizes, reporting standards) is library-neutral. Use this
skill when you have settled on the Python ecosystem.

## Contents

- [[matplotlib]] — foundational plotting (pyplot + object-oriented Figure/Axes), styling,
  and publication-quality static figures.
- [[seaborn]] — dataset-oriented statistical graphics, semantic mappings, and
  multi-panel figures.
- [[statsmodels]] — statistical modelling: OLS/GLM, discrete choice, time series, and
  hypothesis-testing diagnostics.

## When to use

- You need to render a figure from PRE-COMPUTED data (presentation layer).
- You need to fit or diagnose a statistical model in Python (statistical-methodology
  layer) — pair this with the analyst skill's `statistical-analysis` reference for the
  methodology that drives the choice of test/model.
