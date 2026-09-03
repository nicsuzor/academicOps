---
title: Research Project Documentation Structure
type: note
category: instruction
permalink: analyst-chunk-research-documentation
description: The documentation files a research project must carry, the files it must not, and the data/build-output separation
---

# Research project documentation structure

The structure is fixed so that a reader knows where to look, an update happens
in one place, and git history shows meaningful change rather than churn.

## Required files

```
project_root/
├── README.md               # Overview, research questions, quick start — 1-3 pages
├── METHODOLOGY.md          # Research design (instructions/methodology-files.md)
├── methods/                # One file per technical method
│   └── method_name.md
├── experiments/            # Dated exploratory work (instructions/experiment-logging.md)
│   └── YYYYMMDD-description/
├── data/                   # Local cache — gitignored, re-extractable
│   └── README.md           # Data provenance, schema, access, known issues
├── <transformation layer>  # e.g. dbt/models/{staging,intermediate,marts} + dbt/schema.yml
├── <presentation layer>    # e.g. streamlit/dashboard.py
└── output/ or _book/       # Build artifacts only — gitignored, expendable
```

Write no other markdown files. Analysis notes, findings summaries, weekly
updates, scratch files, todo lists, and second READMEs in subdirectories all
fail the same way: they answer a question once and then rot somewhere nobody
looks. Anything worth recording has a home above, or in one of the analysis
surfaces the `analyst` skill lists.

To decide which of these files a given statement belongs in, read
`instructions/methods-vs-methodology.md`.

## Data directory separation (critical)

`data/` and build output directories (`output/`, `_book/`, `_site/`, `dist/`)
must never overlap, because build tools clean their output directory on every
render and will delete whatever of yours is sitting in it.

- Keep local cache — parquet extracts, CSV downloads, warehouse snapshots — in
  `data/`. It is expendable in principle and expensive to rebuild in practice.
- Point every build tool's output directory somewhere that is not `data/`, and
  confirm it in the tool's own config (`_quarto.yml`, `dbt_project.yml`,
  `package.json`) before placing files.

## Keeping documentation current

Stale documentation is a defect, not a nuisance: it makes the next reader
wrong. On finding documentation that no longer matches the code, stop, correct
it, commit the correction on its own, then resume the original task — working
around it, or adding a new file because the old one is wrong, multiplies the
problem.

Every documentation file describes the implementation as it actually stands and
carries no `TODO`, `TK`, or "coming soon" placeholder, because in a research
artifact a placeholder reads as a finding that was never made.
